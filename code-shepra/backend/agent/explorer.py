"""LLM-powered code exploration agent with tool calling."""
import json
import logging
from typing import AsyncGenerator

import httpx
from config import settings
from agent.tools import search_code, read_file, list_files, get_project_map
from agent.classifier import classify_query
from agent.memory import get_relevant_memories, save_episodic_memory

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Code Sherpa, an expert code exploration assistant. You help developers understand codebases by finding and explaining code.

RULES:
1. Always cite specific file paths and function/class names in your explanations.
2. Never speculate beyond what the retrieved code shows. If you can't fully answer, say what you can determine and flag what's unclear.
3. When explaining code, use clear, plain language suitable for a developer new to the project.
4. When multiple implementations exist, surface all of them and explain differences.
5. Use markdown formatting: code blocks with language tags, headers, bullet points.
6. If prior context from memory is relevant, build on it rather than re-explaining.

You have access to these tools:
- search_code(query): Search the codebase using semantic + keyword search. Returns relevant code chunks.
- read_file(file_path): Read the full contents of a specific file.
- list_files(pattern): List files matching a pattern (glob or substring).

To use a tool, respond with a JSON tool call in this format:
{"tool": "tool_name", "args": {"arg1": "value1"}}

After gathering enough information, provide your final explanation. Do NOT use tool calls in your final response.

{memory_context}"""


async def _call_ollama(messages: list[dict], temperature: float = 0.3) -> str:
    """Call Ollama chat API."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_CHAT_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")


def _parse_tool_call(text: str) -> dict | None:
    """Try to parse a tool call from LLM response."""
    # Look for JSON tool call pattern
    try:
        # Find JSON object in text
        start = text.find('{"tool"')
        if start < 0:
            start = text.find('{ "tool"')
        if start < 0:
            return None
        
        # Find matching closing brace
        depth = 0
        end = start
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        
        json_str = text[start:end]
        obj = json.loads(json_str)
        
        if "tool" in obj and "args" in obj:
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    
    return None


async def explore(
    query: str,
    project_id: int,
    conversation_history: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """Run the exploration agent.
    
    Yields progress events and the final response.
    
    Events:
        {"type": "classifying", "data": {}}
        {"type": "tool_call", "data": {"tool": "...", "args": {...}}}
        {"type": "tool_result", "data": {"tool": "...", "summary": "..."}}
        {"type": "thinking", "data": {"step": N}}
        {"type": "response", "data": {"content": "...", "files_explored": [...]}}
        {"type": "error", "data": {"message": "..."}}
    """
    history = conversation_history or []
    
    # Step 1: Classify query
    yield {"type": "classifying", "data": {"query": query}}
    classification = await classify_query(query, history)
    intent = classification.get("intent", "specific")
    
    yield {"type": "classified", "data": classification}
    
    # Step 2: Check memory for relevant context
    memory_context = ""
    try:
        memories = await get_relevant_memories(query, project_id)
        if memories:
            memory_lines = []
            for mem in memories:
                if mem["type"] == "episodic":
                    memory_lines.append(f"- Previously explored: {mem['summary']}")
                elif mem["type"] == "semantic":
                    memory_lines.append(f"- Developer note: {mem['content']}")
            memory_context = "CONTEXT FROM MEMORY:\n" + "\n".join(memory_lines)
    except Exception as e:
        logger.warning(f"Memory retrieval failed: {e}")
    
    # Step 3: Handle map queries specially
    if intent == "map":
        yield {"type": "tool_call", "data": {"tool": "get_project_map", "args": {}}}
        project_map = await get_project_map(project_id)
        yield {"type": "tool_result", "data": {"tool": "get_project_map", "summary": f"Found {project_map['total_files']} files"}}
        
        # Generate explanation from map data
        map_prompt = f"""Based on this project map, provide a clear, well-formatted overview:

{json.dumps(project_map, indent=2)}

Include: languages used, project structure, key files (entry points, configs, docs), and suggested areas to explore first."""
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.replace("{memory_context}", memory_context)},
            {"role": "user", "content": map_prompt},
        ]
        
        response_text = await _call_ollama(messages)
        
        yield {"type": "response", "data": {
            "content": response_text,
            "files_explored": [],
            "intent": intent,
        }}
        
        # Save to episodic memory
        try:
            await save_episodic_memory(
                project_id=project_id,
                query=query,
                files_explored=[],
                summary=f"Explored project map: {project_map['total_files']} files across {len(project_map['languages'])} languages",
            )
        except Exception as e:
            logger.warning(f"Failed to save episodic memory: {e}")
        
        return
    
    # Step 4: Agent loop with tool calling
    system_msg = SYSTEM_PROMPT.replace("{memory_context}", memory_context)
    messages = [{"role": "system", "content": system_msg}]
    
    # Add conversation history
    for msg in history[-10:]:  # Last 5 exchanges
        messages.append(msg)
    
    messages.append({"role": "user", "content": query})
    
    files_explored = set()
    max_iterations = settings.MAX_AGENT_ITERATIONS
    
    for step in range(max_iterations):
        yield {"type": "thinking", "data": {"step": step + 1}}
        
        response_text = await _call_ollama(messages)
        
        # Check if it's a tool call
        tool_call = _parse_tool_call(response_text)
        
        if tool_call:
            tool_name = tool_call["tool"]
            tool_args = tool_call.get("args", {})
            
            yield {"type": "tool_call", "data": {"tool": tool_name, "args": tool_args}}
            
            # Execute tool
            try:
                if tool_name == "search_code":
                    result = await search_code(
                        query=tool_args.get("query", query),
                        project_id=project_id,
                        language=tool_args.get("language"),
                        chunk_type=tool_args.get("chunk_type"),
                    )
                    for r in result:
                        files_explored.add(r["file_path"])
                    result_text = json.dumps(result[:5], indent=2)  # Limit context size
                    summary = f"Found {len(result)} matching chunks"
                    
                elif tool_name == "read_file":
                    result = await read_file(
                        file_path=tool_args.get("file_path", ""),
                        project_id=project_id,
                    )
                    files_explored.add(tool_args.get("file_path", ""))
                    result_text = json.dumps(result, indent=2)
                    summary = f"Read file: {tool_args.get('file_path', '')}"
                    
                elif tool_name == "list_files":
                    result = await list_files(
                        pattern=tool_args.get("pattern", "*"),
                        project_id=project_id,
                    )
                    result_text = json.dumps(result, indent=2)
                    summary = f"Listed {len(result)} files"
                    
                else:
                    result_text = f"Unknown tool: {tool_name}"
                    summary = "Unknown tool"
                
                yield {"type": "tool_result", "data": {"tool": tool_name, "summary": summary}}
                
                # Add tool result to conversation
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Tool result for {tool_name}:\n{result_text}\n\nContinue your analysis. Use more tools if needed, or provide your final explanation."})
                
            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                logger.error(error_msg)
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"Tool error: {error_msg}. Try a different approach or provide your answer with what you have."})
        else:
            # No tool call = final response
            yield {"type": "response", "data": {
                "content": response_text,
                "files_explored": list(files_explored),
                "intent": intent,
            }}
            
            # Save to episodic memory
            try:
                await save_episodic_memory(
                    project_id=project_id,
                    query=query,
                    files_explored=list(files_explored),
                    summary=response_text[:200],
                )
            except Exception as e:
                logger.warning(f"Failed to save episodic memory: {e}")
            
            return
    
    # Hit max iterations
    yield {"type": "response", "data": {
        "content": response_text + "\n\n*Note: Reached maximum exploration depth. The answer above is based on the information gathered so far.*",
        "files_explored": list(files_explored),
        "intent": intent,
    }}
