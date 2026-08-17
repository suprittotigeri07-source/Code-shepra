"""Agent memory management - episodic and semantic memory."""
import logging
from database import get_pool
from embedder.ollama_embed import embed_text
from config import settings

logger = logging.getLogger(__name__)


async def save_episodic_memory(
    project_id: int,
    query: str,
    files_explored: list[str],
    summary: str,
):
    """Save an episodic memory entry (what was explored)."""
    try:
        embedding = await embed_text(f"{query} {summary}")
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO episodic_memory (project_id, query, files_explored, summary, embedding)
                   VALUES ($1, $2, $3, $4, $5)""",
                project_id,
                query,
                files_explored,
                summary,
                str(embedding),
            )
    except Exception as e:
        logger.error(f"Failed to save episodic memory: {e}")


async def save_semantic_memory(
    project_id: int,
    content: str,
) -> int:
    """Save a semantic memory entry (developer-provided context).
    
    Returns the ID of the created entry.
    """
    embedding = await embed_text(content)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO semantic_memory (project_id, content, embedding)
               VALUES ($1, $2, $3) RETURNING id""",
            project_id,
            content,
            str(embedding),
        )
        return row["id"]


async def update_semantic_memory(memory_id: int, content: str):
    """Update an existing semantic memory entry."""
    embedding = await embed_text(content)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE semantic_memory 
               SET content = $1, embedding = $2, updated_at = NOW()
               WHERE id = $3""",
            content,
            str(embedding),
            memory_id,
        )


async def delete_memory(memory_id: int, memory_type: str):
    """Delete a specific memory entry."""
    pool = await get_pool()
    table = "episodic_memory" if memory_type == "episodic" else "semantic_memory"
    async with pool.acquire() as conn:
        await conn.execute(f"DELETE FROM {table} WHERE id = $1", memory_id)


async def clear_memory(project_id: int, memory_type: str):
    """Clear all memory of a type for a project."""
    pool = await get_pool()
    table = "episodic_memory" if memory_type == "episodic" else "semantic_memory"
    async with pool.acquire() as conn:
        await conn.execute(f"DELETE FROM {table} WHERE project_id = $1", project_id)


async def get_relevant_memories(
    query: str,
    project_id: int,
    top_k: int = 5,
) -> list[dict]:
    """Retrieve relevant memories for a query.
    
    Combines episodic and semantic memory results.
    """
    query_embedding = await embed_text(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    pool = await get_pool()
    results = []
    
    async with pool.acquire() as conn:
        # Search episodic memory
        episodic_rows = await conn.fetch(
            f"""SELECT id, query, files_explored, summary, created_at,
                       1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM episodic_memory
                WHERE project_id = $1 AND embedding IS NOT NULL
                ORDER BY embedding <=> '{embedding_str}'::vector
                LIMIT $2""",
            project_id, top_k,
        )
        
        for row in episodic_rows:
            if float(row["similarity"]) > 0.3:
                results.append({
                    "type": "episodic",
                    "id": row["id"],
                    "query": row["query"],
                    "files_explored": row["files_explored"],
                    "summary": row["summary"],
                    "content": row["summary"],
                    "created_at": row["created_at"].isoformat(),
                    "similarity": float(row["similarity"]),
                })
        
        # Search semantic memory
        semantic_rows = await conn.fetch(
            f"""SELECT id, content, created_at, updated_at,
                       1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM semantic_memory
                WHERE project_id = $1 AND embedding IS NOT NULL
                ORDER BY embedding <=> '{embedding_str}'::vector
                LIMIT $2""",
            project_id, top_k,
        )
        
        for row in semantic_rows:
            if float(row["similarity"]) > 0.3:
                results.append({
                    "type": "semantic",
                    "id": row["id"],
                    "content": row["content"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                    "similarity": float(row["similarity"]),
                })
    
    # Sort by similarity
    results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return results[:top_k]


async def get_all_memories(project_id: int) -> dict:
    """Get all memories for a project."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        episodic_rows = await conn.fetch(
            """SELECT id, query, files_explored, summary, created_at
               FROM episodic_memory
               WHERE project_id = $1
               ORDER BY created_at DESC""",
            project_id,
        )
        
        semantic_rows = await conn.fetch(
            """SELECT id, content, created_at, updated_at
               FROM semantic_memory
               WHERE project_id = $1
               ORDER BY created_at DESC""",
            project_id,
        )
    
    return {
        "episodic": [
            {
                "id": r["id"],
                "query": r["query"],
                "files_explored": r["files_explored"],
                "summary": r["summary"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in episodic_rows
        ],
        "semantic": [
            {
                "id": r["id"],
                "content": r["content"],
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            }
            for r in semantic_rows
        ],
    }


async def search_memories(query: str, project_id: int) -> list[dict]:
    """Search memories by text and vector similarity."""
    # Vector search
    vector_results = await get_relevant_memories(query, project_id, top_k=10)
    
    # Text search
    pool = await get_pool()
    async with pool.acquire() as conn:
        query_pattern = f"%{query}%"
        
        text_episodic = await conn.fetch(
            """SELECT id, query, files_explored, summary, created_at
               FROM episodic_memory
               WHERE project_id = $1 AND (query ILIKE $2 OR summary ILIKE $2)
               ORDER BY created_at DESC LIMIT 5""",
            project_id, query_pattern,
        )
        
        text_semantic = await conn.fetch(
            """SELECT id, content, created_at, updated_at
               FROM semantic_memory
               WHERE project_id = $1 AND content ILIKE $2
               ORDER BY created_at DESC LIMIT 5""",
            project_id, query_pattern,
        )
    
    # Merge results, deduplicate by id+type
    seen = set()
    results = []
    
    for r in vector_results:
        key = (r["type"], r["id"])
        if key not in seen:
            seen.add(key)
            results.append(r)
    
    for r in text_episodic:
        key = ("episodic", r["id"])
        if key not in seen:
            seen.add(key)
            results.append({
                "type": "episodic",
                "id": r["id"],
                "query": r["query"],
                "files_explored": r["files_explored"],
                "summary": r["summary"],
                "content": r["summary"],
                "created_at": r["created_at"].isoformat(),
            })
    
    for r in text_semantic:
        key = ("semantic", r["id"])
        if key not in seen:
            seen.add(key)
            results.append({
                "type": "semantic",
                "id": r["id"],
                "content": r["content"],
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
            })
    
    return results


async def get_exploration_summary(project_id: int) -> dict:
    """Get a summary of what has been explored vs unvisited."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get all explored files from episodic memory
        explored_rows = await conn.fetch(
            """SELECT DISTINCT unnest(files_explored) as file_path
               FROM episodic_memory
               WHERE project_id = $1""",
            project_id,
        )
        explored_files = {r["file_path"] for r in explored_rows}
        
        # Get all files in project
        all_files_rows = await conn.fetch(
            """SELECT file_path FROM file_tree
               WHERE project_id = $1 AND NOT is_directory""",
            project_id,
        )
        all_files = {r["file_path"] for r in all_files_rows}
        
        # Count queries
        query_count = await conn.fetchval(
            "SELECT COUNT(*) FROM episodic_memory WHERE project_id = $1",
            project_id,
        )
    
    unvisited = all_files - explored_files
    
    return {
        "total_files": len(all_files),
        "explored_files": len(explored_files),
        "unvisited_files": len(unvisited),
        "exploration_percentage": round(len(explored_files) / max(len(all_files), 1) * 100, 1),
        "total_queries": query_count,
        "sample_unvisited": sorted(list(unvisited))[:20],
    }
