"""Vector similarity search using pgvector."""
import logging
from dataclasses import dataclass

from database import get_pool
from embedder.ollama_embed import embed_text
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result with relevance score."""
    id: int
    file_path: str
    chunk_type: str
    chunk_name: str
    language: str
    start_line: int
    end_line: int
    content: str
    score: float
    source: str = "vector"  # "vector" or "fulltext"


async def vector_search(
    query: str,
    project_id: int,
    top_k: int | None = None,
    min_similarity: float | None = None,
    language_filter: str | None = None,
    chunk_type_filter: str | None = None,
) -> list[SearchResult]:
    """Search for code chunks by vector similarity.
    
    Args:
        query: Natural language query
        project_id: Project to search within
        top_k: Maximum results (default from settings)
        min_similarity: Minimum cosine similarity (default from settings)
        language_filter: Optional language filter
        chunk_type_filter: Optional chunk type filter
    
    Returns:
        List of SearchResult sorted by relevance
    """
    top_k = top_k or settings.TOP_K_RESULTS
    min_similarity = min_similarity or settings.SIMILARITY_THRESHOLD
    
    # Embed the query
    query_embedding = await embed_text(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # Build query with filters
    conditions = ["project_id = $1", "embedding IS NOT NULL"]
    params: list = [project_id]
    param_idx = 2
    
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
               1 - (embedding <=> '{embedding_str}'::vector) as similarity
        FROM code_chunks
        WHERE {where_clause}
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT {top_k}
    """
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    
    results = []
    for row in rows:
        sim = float(row["similarity"])
        if sim >= min_similarity:
            results.append(SearchResult(
                id=row["id"],
                file_path=row["file_path"],
                chunk_type=row["chunk_type"],
                chunk_name=row["chunk_name"],
                language=row["language"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                content=row["content"],
                score=sim,
                source="vector",
            ))
    
    return results
