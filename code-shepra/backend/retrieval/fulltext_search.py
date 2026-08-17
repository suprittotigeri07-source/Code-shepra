"""Full-text search using PostgreSQL tsvector."""
import logging
import re

from database import get_pool
from retrieval.vector_search import SearchResult
from config import settings

logger = logging.getLogger(__name__)


def sanitize_query(query: str) -> str:
    """Convert natural language query to tsquery-compatible format."""
    # Remove special characters, keep words
    words = re.findall(r'\w+', query.lower())
    if not words:
        return ""
    # Join with OR for broader matching
    return " | ".join(words)


async def fulltext_search(
    query: str,
    project_id: int,
    top_k: int | None = None,
    language_filter: str | None = None,
    chunk_type_filter: str | None = None,
) -> list[SearchResult]:
    """Search for code chunks using PostgreSQL full-text search.
    
    Catches exact identifier names, error messages, string literals
    that vector search might rank lower.
    """
    top_k = top_k or settings.TOP_K_RESULTS
    
    ts_query = sanitize_query(query)
    if not ts_query:
        return []
    
    conditions = ["project_id = $1", "content_tsv @@ to_tsquery('english', $2)"]
    params: list = [project_id, ts_query]
    param_idx = 3
    
    if language_filter:
        conditions.append(f"language = ${param_idx}")
        params.append(language_filter)
        param_idx += 1
    
    if chunk_type_filter:
        conditions.append(f"chunk_type = ${param_idx}")
        params.append(chunk_type_filter)
        param_idx += 1
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT id, file_path, chunk_type, chunk_name, language,
               start_line, end_line, content,
               ts_rank_cd(content_tsv, to_tsquery('english', $2)) as rank
        FROM code_chunks
        WHERE {where_clause}
        ORDER BY rank DESC
        LIMIT {top_k}
    """
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    
    results = []
    for row in rows:
        results.append(SearchResult(
            id=row["id"],
            file_path=row["file_path"],
            chunk_type=row["chunk_type"],
            chunk_name=row["chunk_name"],
            language=row["language"],
            start_line=row["start_line"],
            end_line=row["end_line"],
            content=row["content"],
            score=float(row["rank"]),
            source="fulltext",
        ))
    
    return results
