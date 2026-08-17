"""Ollama embedding client for Code Sherpa."""
import logging
from typing import Optional

import httpx
from config import settings

logger = logging.getLogger(__name__)

# Reusable HTTP client
_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    """Get or create the HTTP client."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.OLLAMA_BASE_URL,
            timeout=120.0,
        )
    return _client


async def close_client():
    """Close the HTTP client."""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def embed_text(text: str) -> list[float]:
    """Generate embedding for a single text using Ollama."""
    client = await get_client()
    response = await client.post("/api/embed", json={
        "model": settings.OLLAMA_EMBED_MODEL,
        "input": text,
    })
    response.raise_for_status()
    data = response.json()
    # Ollama returns {"embeddings": [[...]] } for /api/embed
    embeddings = data.get("embeddings", [])
    if embeddings and len(embeddings) > 0:
        return embeddings[0]
    raise ValueError(f"No embeddings returned from Ollama: {data}")


async def embed_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    """Generate embeddings for a batch of texts.
    
    Processes in sub-batches to avoid overwhelming Ollama.
    """
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = []
        
        for text in batch:
            try:
                emb = await embed_text(text)
                batch_embeddings.append(emb)
            except Exception as e:
                logger.error(f"Embedding failed for text (len={len(text)}): {e}")
                # Use zero vector as fallback
                batch_embeddings.append([0.0] * settings.EMBEDDING_DIMENSIONS)
        
        all_embeddings.extend(batch_embeddings)
    
    return all_embeddings


async def verify_model() -> bool:
    """Verify the embedding model is available in Ollama."""
    try:
        client = await get_client()
        response = await client.post("/api/embed", json={
            "model": settings.OLLAMA_EMBED_MODEL,
            "input": "test",
        })
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings", [])
        if embeddings and len(embeddings[0]) == settings.EMBEDDING_DIMENSIONS:
            logger.info(f"Ollama embedding model verified: {settings.OLLAMA_EMBED_MODEL} ({len(embeddings[0])}d)")
            return True
        logger.warning(f"Unexpected embedding dimensions: {len(embeddings[0]) if embeddings else 'none'}")
        return True  # Still usable
    except Exception as e:
        logger.error(f"Failed to verify Ollama embedding model: {e}")
        return False
