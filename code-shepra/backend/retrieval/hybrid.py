"""Hybrid search combining vector and full-text results."""
import logging
from retrieval.vector_search import vector_search, SearchResult
from retrieval.fulltext_search import fulltext_search
from config import settings

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    result_lists: list[list[SearchResult]],
    k: int = 60,
) -> list[SearchResult]:
    """Merge multiple ranked result lists using Reciprocal Rank Fusion (RRF).
    
    RRF score = sum(1 / (k + rank_i)) for each list containing the result.
    Higher k gives more weight to lower-ranked results.
    """
    scores: dict[int, float] = {}
    results_by_id: dict[int, SearchResult] = {}
    
    for result_list in result_lists:
        for rank, result in enumerate(result_list):
            rrf_score = 1.0 / (k + rank + 1)
            scores[result.id] = scores.get(result.id, 0.0) + rrf_score
            results_by_id[result.id] = result
    
    # Sort by fused score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    fused_results = []
    for result_id in sorted_ids:
        result = results_by_id[result_id]
        result.score = scores[result_id]
        result.source = "hybrid"
        fused_results.append(result)
    
    return fused_results


async def hybrid_search(
    query: str,
    project_id: int,
    top_k: int | None = None,
    language_filter: str | None = None,
    chunk_type_filter: str | None = None,
) -> list[SearchResult]:
    """Perform hybrid search combining vector similarity and full-text search.
    
    Returns merged results using Reciprocal Rank Fusion.
    """
    top_k = top_k or settings.TOP_K_RESULTS
    
    # Run both searches
    vector_results = await vector_search(
        query, project_id,
        top_k=top_k * 2,  # Get more candidates for fusion
        language_filter=language_filter,
        chunk_type_filter=chunk_type_filter,
    )
    
    ft_results = await fulltext_search(
        query, project_id,
        top_k=top_k * 2,
        language_filter=language_filter,
        chunk_type_filter=chunk_type_filter,
    )
    
    # Merge with RRF
    if vector_results or ft_results:
        fused = reciprocal_rank_fusion([vector_results, ft_results])
        return fused[:top_k]
    
    return []
