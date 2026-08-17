"""Agent tools for code exploration."""
import fnmatch
import logging
import os
from pathlib import Path

from database import get_pool
from retrieval.hybrid import hybrid_search, SearchResult

logger = logging.getLogger(__name__)


async def search_code(
    query: str,
    project_id: int,
    language: str | None = None,
    chunk_type: str | None = None,
    top_k: int = 10,
) -> list[dict]:
    """Search for code using hybrid vector + full-text search.
    
    Tool for the LLM agent to find relevant code.
    """
    results = await hybrid_search(
        query=query,
        project_id=project_id,
        top_k=top_k,
        language_filter=language,
        chunk_type_filter=chunk_type,
    )
    
    return [
        {
            "file_path": r.file_path,
            "chunk_type": r.chunk_type,
            "chunk_name": r.chunk_name,
            "language": r.language,
            "start_line": r.start_line,
            "end_line": r.end_line,
            "content": r.content[:3000],  # Truncate very long chunks
            "score": round(r.score, 4),
        }
        for r in results
    ]


async def read_file(file_path: str, project_id: int) -> dict:
    """Read full file contents from an ingested project.
    
    Tool for the LLM agent to read complete files.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get project source path
        project = await conn.fetchrow(
            "SELECT source_path FROM projects WHERE id = $1", project_id
        )
        if not project:
            return {"error": "Project not found"}
        
        source_path = project["source_path"]
        full_path = os.path.join(source_path, file_path)
        
        if not os.path.exists(full_path):
            return {"error": f"File not found: {file_path}"}
        
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "file_path": file_path,
                "content": content[:10000],  # Limit to 10K chars
                "total_lines": content.count("\n") + 1,
                "truncated": len(content) > 10000,
            }
        except Exception as e:
            return {"error": f"Failed to read {file_path}: {str(e)}"}


async def list_files(pattern: str, project_id: int) -> list[dict]:
    """List files matching a glob pattern from stored metadata.
    
    Tool for the LLM agent to explore project structure.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT DISTINCT file_path, language 
               FROM file_tree 
               WHERE project_id = $1 AND NOT is_directory
               ORDER BY file_path""",
            project_id
        )
    
    results = []
    for row in rows:
        fp = row["file_path"]
        if pattern == "*" or fnmatch.fnmatch(fp, pattern) or pattern.lower() in fp.lower():
            results.append({
                "file_path": fp,
                "language": row["language"],
            })
    
    return results[:50]  # Limit results


async def get_project_map(project_id: int) -> dict:
    """Generate a high-level map of the project structure.
    
    Returns language breakdown, key files, entry points, and module structure.
    """
    from parser.languages import KEY_FILE_PATTERNS
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Language breakdown
        lang_rows = await conn.fetch(
            """SELECT language, COUNT(*) as count 
               FROM file_tree 
               WHERE project_id = $1 AND NOT is_directory AND language != ''
               GROUP BY language ORDER BY count DESC""",
            project_id
        )
        
        # All file paths
        file_rows = await conn.fetch(
            """SELECT file_path, is_directory, language
               FROM file_tree
               WHERE project_id = $1
               ORDER BY file_path""",
            project_id
        )
        
        # Chunk type breakdown
        chunk_rows = await conn.fetch(
            """SELECT chunk_type, COUNT(*) as count
               FROM code_chunks
               WHERE project_id = $1
               GROUP BY chunk_type ORDER BY count DESC""",
            project_id
        )
    
    # Find key files
    all_files = [r["file_path"] for r in file_rows if not r["is_directory"]]
    key_files = {}
    
    for category, patterns in KEY_FILE_PATTERNS.items():
        found = []
        for fp in all_files:
            basename = os.path.basename(fp).lower()
            for pat in patterns:
                if basename == pat.lower() or fp.lower().endswith(pat.lower()):
                    found.append(fp)
                    break
        if found:
            key_files[category] = found
    
    # Top-level directories
    top_dirs = sorted(set(
        r["file_path"].split("/")[0]
        for r in file_rows
        if r["is_directory"] and "/" not in r["file_path"].rstrip("/")
    ))
    
    return {
        "languages": {r["language"]: r["count"] for r in lang_rows},
        "chunk_types": {r["chunk_type"]: r["count"] for r in chunk_rows},
        "total_files": len(all_files),
        "top_level_modules": top_dirs[:20],
        "key_files": key_files,
    }
