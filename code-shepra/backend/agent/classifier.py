"""Query intent classifier using LLM."""
import json
import logging

import httpx
from config import settings

logger = logging.getLogger(__name__)


CLASSIFY_PROMPT = """You are a query classifier for a code exploration tool. Classify the user's query into one of these categories:

1. "map" - User wants a high-level overview of the codebase (e.g., "show me the project structure", "what is this project about?", "give me a map")
2. "follow_up" - User is asking about something from the previous conversation (e.g., "what calls this?", "where is the return value used?", "tell me more about that")
3. "exploration" - User wants to understand a broad topic or flow (e.g., "how does authentication work?", "explain the payment flow", "trace the request lifecycle")
4. "specific" - User is asking about a specific function, class, file, or concept (e.g., "what does the parse_args function do?", "where is the database connection configured?")

Recent conversation (may be empty):
{history}

User query: {query}

Respond with ONLY a JSON object: {{"intent": "<category>", "reasoning": "<brief explanation>"}}"""


async def classify_query(query: str, history: list[dict] | None = None) -> dict:
    """Classify a user query into an intent category.
    
    Uses a single LLM call with conversation history for context.
    
    Returns:
        dict with "intent" and "reasoning" keys
    """
    # Format recent history
    history_text = ""
    if history:
        recent = history[-6:]  # Last 3 exchanges
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]
            history_text += f"{role}: {content}\n"
    
    if not history_text:
        history_text = "(no prior conversation)"
    
    prompt = CLASSIFY_PROMPT.format(history=history_text, query=query)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_CHAT_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                }
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "").strip()
            
            # Parse JSON from response
            # Find the JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                result = json.loads(text[start:end])
                if "intent" in result:
                    return result
            
            # Fallback: try to detect intent from keywords
            return {"intent": "specific", "reasoning": "Could not parse LLM response"}
            
    except Exception as e:
        logger.error(f"Query classification failed: {e}")
        # Fallback classification based on keywords
        query_lower = query.lower()
        if any(w in query_lower for w in ["map", "overview", "structure", "layout"]):
            return {"intent": "map", "reasoning": "Keyword-based fallback"}
        elif any(w in query_lower for w in ["this", "that", "it", "those", "calls this", "more about"]):
            return {"intent": "follow_up", "reasoning": "Keyword-based fallback"}
        elif any(w in query_lower for w in ["how does", "explain", "trace", "flow", "lifecycle", "walk through"]):
            return {"intent": "exploration", "reasoning": "Keyword-based fallback"}
        return {"intent": "specific", "reasoning": "Default fallback"}
