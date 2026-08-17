"""Project management and ingestion pipeline for Code Sherpa."""
import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
import git

from database import get_pool, init_database, create_vector_index
from parser.chunker import parse_codebase, CodeChunk
from embedder.ollama_embed import embed_batch

logger = logging.getLogger(__name__)

# Active ingestion locks to prevent concurrent runs on the same project
_ingestion_locks = {}


def get_ingestion_lock(project_id: int) -> asyncio.Lock:
    """Get a lock for a project to prevent concurrent ingestion."""
    if project_id not in _ingestion_locks:
        _ingestion_locks[project_id] = asyncio.Lock()
    return _ingestion_locks[project_id]


async def create_project(name: str, source_path: str, description: str = "") -> dict:
    """Create a new project entry in the database."""
    pool = await get_pool()
    
    # Handle git clone if it is a Git URL
    actual_path = source_path
    if source_path.startswith("http://") or source_path.startswith("https://") or source_path.endswith(".git"):
        # Let's create a local clone directory
        projects_dir = Path("d:/Projects/code-shepra/projects_cloned")
        projects_dir.mkdir(exist_ok=True)
        repo_name = name.lower().replace(" ", "_")
        clone_path = projects_dir / repo_name
        
        if not clone_path.exists():
            logger.info(f"Cloning {source_path} to {clone_path}...")
            git.Repo.clone_from(source_path, str(clone_path))
        else:
            logger.info(f"Repo already cloned at {clone_path}")
        actual_path = str(clone_path).replace("\\", "/")

    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """INSERT INTO projects (name, source_path, description)
                   VALUES ($1, $2, $3)
                   RETURNING id, name, source_path, description, created_at, last_ingestion, file_count, chunk_count""",
                name, actual_path, description
            )
            return dict(row)
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise e


async def list_projects() -> list[dict]:
    """List all projects with metadata."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, name, source_path, description, created_at, last_ingestion, file_count, chunk_count, is_ingesting FROM projects ORDER BY name"
        )
        return [dict(r) for r in rows]


async def get_project(project_id: int) -> dict | None:
    """Get project details."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, source_path, description, created_at, last_ingestion, file_count, chunk_count, is_ingesting FROM projects WHERE id = $1",
            project_id
        )
        return dict(row) if row else None


async def delete_project(project_id: int):
    """Delete a project and all its associated data."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM projects WHERE id = $1", project_id)


async def ingest_project(project_id: int, progress_queue: asyncio.Queue = None):
    """Run the ingestion pipeline for a project (parse -> embed -> store).
    
    Includes incremental updates by hashing files and only embedding modified files.
    """
    lock = get_ingestion_lock(project_id)
    if lock.locked():
        if progress_queue:
            await progress_queue.put({"phase": "error", "message": "Ingestion already running for this project"})
        return
        
    async with lock:
        pool = await get_pool()
        
        # Set ingesting flag
        async with pool.acquire() as conn:
            await conn.execute("UPDATE projects SET is_ingesting = TRUE WHERE id = $1", project_id)
            project = await conn.fetchrow("SELECT name, source_path FROM projects WHERE id = $1", project_id)
            
        if not project:
            if progress_queue:
                await progress_queue.put({"phase": "error", "message": "Project not found"})
            return
            
        name = project["name"]
        source_path = project["source_path"]
        
        try:
            if progress_queue:
                await progress_queue.put({"phase": "parsing", "message": f"Scanning and parsing files in {source_path}..."})
                
            # Define parser callback
            def parser_callback(status_msg, processed, chunks_count, failed):
                if progress_queue:
                    asyncio.run_coroutine_threadsafe(
                        progress_queue.put({
                            "phase": "parsing",
                            "message": status_msg,
                            "files_processed": processed,
                            "chunks_created": chunks_count,
                            "files_failed": failed
                        }),
                        asyncio.get_event_loop()
                    )
            
            # Run parser in a separate thread to avoid blocking event loop
            loop = asyncio.get_running_loop()
            parse_res = await loop.run_in_executor(
                None, parse_codebase, source_path, parser_callback
            )
            
            if not parse_res.chunks:
                if progress_queue:
                    await progress_queue.put({
                        "phase": "completed", 
                        "message": "Ingestion complete. No source files found.",
                        "summary": {"files_processed": 0, "chunks_stored": 0, "files_skipped": parse_res.files_skipped}
                    })
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE projects SET is_ingesting = FALSE, last_ingestion = NOW() WHERE id = $1",
                        project_id
                    )
                return

            if progress_queue:
                await progress_queue.put({
                    "phase": "analyzing",
                    "message": "Analyzing changes for incremental update..."
                })

            # Check existing file hashes to do incremental update
            async with pool.acquire() as conn:
                existing_hashes = await conn.fetch(
                    "SELECT DISTINCT file_path, file_hash FROM code_chunks WHERE project_id = $1",
                    project_id
                )
            
            hash_map = {r["file_path"]: r["file_hash"] for r in existing_hashes}
            
            # Categorize files
            chunks_to_embed = []
            files_to_delete = set(hash_map.keys())
            unchanged_files = 0
            
            for chunk in parse_res.chunks:
                path = chunk.file_path
                current_hash = chunk.file_hash
                
                # If file in parsed files, we don't delete it
                if path in files_to_delete:
                    files_to_delete.remove(path)
                    
                if path in hash_map and hash_map[path] == current_hash:
                    # File is unchanged, keep existing chunk
                    unchanged_files += 1
                else:
                    # File is new or changed
                    chunks_to_embed.append(chunk)

            # Delete chunks for removed files
            if files_to_delete:
                if progress_queue:
                    await progress_queue.put({
                        "phase": "cleaning",
                        "message": f"Removing {len(files_to_delete)} deleted files from index..."
                    })
                async with pool.acquire() as conn:
                    await conn.execute(
                        "DELETE FROM code_chunks WHERE project_id = $1 AND file_path = ANY($2)",
                        project_id, list(files_to_delete)
                    )
                    await conn.execute(
                        "DELETE FROM file_tree WHERE project_id = $1 AND file_path = ANY($2)",
                        project_id, list(files_to_delete)
                    )

            # Update file_tree metadata
            if progress_queue:
                await progress_queue.put({
                    "phase": "metadata",
                    "message": "Updating project file tree..."
                })
            
            all_paths = set()
            for chunk in parse_res.chunks:
                all_paths.add(chunk.file_path)
                
            # Create directories structure from paths
            dirs_to_insert = set()
            for fp in all_paths:
                parts = fp.split("/")
                for i in range(1, len(parts)):
                    dirs_to_insert.add("/".join(parts[:i]))
                    
            async with pool.acquire() as conn:
                # Insert dirs
                for d in dirs_to_insert:
                    await conn.execute(
                        """INSERT INTO file_tree (project_id, file_path, is_directory)
                           VALUES ($1, $2, TRUE) ON CONFLICT (project_id, file_path) DO NOTHING""",
                        project_id, d
                    )
                # Insert files
                for chunk in parse_res.chunks:
                    await conn.execute(
                        """INSERT INTO file_tree (project_id, file_path, is_directory, language)
                           VALUES ($1, $2, FALSE, $3) ON CONFLICT (project_id, file_path) DO UPDATE SET language = $3""",
                        project_id, chunk.file_path, chunk.language
                    )

            # If there are changed or new chunks, embed and store them
            chunks_stored_count = 0
            if chunks_to_embed:
                total_chunks = len(chunks_to_embed)
                batch_size = 50
                total_batches = (total_chunks + batch_size - 1) // batch_size
                
                if progress_queue:
                    await progress_queue.put({
                        "phase": "embedding",
                        "message": f"Embedding {total_chunks} chunks in {total_batches} batches...",
                        "total_batches": total_batches,
                        "current_batch": 0
                    })
                
                # Delete old chunks for files that are being updated
                updated_files = list(set(c.file_path for c in chunks_to_embed))
                async with pool.acquire() as conn:
                    await conn.execute(
                        "DELETE FROM code_chunks WHERE project_id = $1 AND file_path = ANY($2)",
                        project_id, updated_files
                    )
                
                for b in range(total_batches):
                    start_idx = b * batch_size
                    end_idx = min(start_idx + batch_size, total_chunks)
                    batch = chunks_to_embed[start_idx:end_idx]
                    
                    if progress_queue:
                        await progress_queue.put({
                            "phase": "embedding",
                            "message": f"Embedding batch {b+1} of {total_batches}...",
                            "total_batches": total_batches,
                            "current_batch": b + 1
                        })
                    
                    # Generate embeddings
                    contents = [c.content for c in batch]
                    embeddings = await embed_batch(contents)
                    
                    # Store chunks
                    async with pool.acquire() as conn:
                        for chunk, emb in zip(batch, embeddings):
                            # Insert code chunk and generate full text search vector
                            await conn.execute(
                                """INSERT INTO code_chunks 
                                   (project_id, file_path, file_hash, chunk_type, chunk_name, language, start_line, end_line, content, embedding, content_tsv)
                                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, to_tsvector('english', $9))""",
                                project_id, chunk.file_path, chunk.file_hash, chunk.chunk_type, chunk.chunk_name,
                                chunk.language, chunk.start_line, chunk.end_line, chunk.content, str(emb)
                            )
                            chunks_stored_count += 1
            
            # Post-processing: create vector index if needed
            await create_vector_index(project_id)
            
            # Update project metadata
            async with pool.acquire() as conn:
                file_count = await conn.fetchval(
                    "SELECT COUNT(DISTINCT file_path) FROM file_tree WHERE project_id = $1 AND NOT is_directory",
                    project_id
                )
                chunk_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM code_chunks WHERE project_id = $1",
                    project_id
                )
                await conn.execute(
                    """UPDATE projects 
                       SET file_count = $1, chunk_count = $2, last_ingestion = NOW(), is_ingesting = FALSE
                       WHERE id = $3""",
                    file_count, chunk_count, project_id
                )
                
            if progress_queue:
                await progress_queue.put({
                    "phase": "completed",
                    "message": "Ingestion complete!",
                    "summary": {
                        "files_processed": parse_res.files_processed,
                        "chunks_stored": chunks_stored_count,
                        "unchanged_files": unchanged_files,
                        "removed_files": len(files_to_delete),
                        "total_chunks": chunk_count,
                        "total_files": file_count
                    }
                })
                
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            async with pool.acquire() as conn:
                await conn.execute("UPDATE projects SET is_ingesting = FALSE WHERE id = $1", project_id)
            if progress_queue:
                await progress_queue.put({"phase": "error", "message": f"Ingestion failed: {str(e)}"})
