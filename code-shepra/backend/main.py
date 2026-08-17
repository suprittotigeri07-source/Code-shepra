"""FastAPI application entry point for Code Sherpa backend."""
import asyncio
import logging
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config import settings
from database import init_database, close_pool, get_pool
import projects.manager as pm
from agent.explorer import explore
import agent.memory as am
from agent.tools import read_file

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Active ingestion queues: project_id -> Queue
ingestion_queues: dict[int, asyncio.Queue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    try:
        await init_database()
    except Exception as e:
        logger.error(f"Lifespan startup database initialization failed: {e}")
    yield
    # Shutdown
    logger.info("Closing database connections...")
    await close_pool()
    from embedder.ollama_embed import close_client
    await close_client()


app = FastAPI(
    title="Code Sherpa API",
    description="Semantic code exploration tool API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic schemas
class ProjectCreate(BaseModel):
    name: str
    source_path: str
    description: Optional[str] = ""


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str
    history: Optional[list[ChatMessage]] = []


class MemoryCreate(BaseModel):
    content: str


# Projects API
@app.get("/api/projects")
async def list_projects():
    try:
        return await pm.list_projects()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects")
async def create_project(project: ProjectCreate):
    try:
        return await pm.create_project(
            name=project.name,
            source_path=project.source_path,
            description=project.description,
        )
    except Exception as e:
        if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
            raise HTTPException(status_code=400, detail="A project with this name already exists")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}")
async def get_project(project_id: int):
    p = await pm.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int):
    try:
        await pm.delete_project(project_id)
        return {"status": "success", "message": f"Project {project_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Ingestion API
@app.post("/api/projects/{project_id}/ingest")
async def start_ingestion(project_id: int, background_tasks: BackgroundTasks):
    p = await pm.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    lock = pm.get_ingestion_lock(project_id)
    if lock.locked():
        raise HTTPException(status_code=400, detail="Ingestion already in progress for this project")
        
    # Create or reuse progress queue
    q = asyncio.Queue()
    ingestion_queues[project_id] = q
    
    # Run in background
    background_tasks.add_task(pm.ingest_project, project_id, q)
    return {"status": "started", "message": "Project ingestion initiated in background"}


@app.get("/api/projects/{project_id}/ingest/progress")
async def get_ingestion_progress(project_id: int):
    if project_id not in ingestion_queues:
        # If not active, check if the project is ingesting
        p = await pm.get_project(project_id)
        if p and p["is_ingesting"]:
            # Recreate queue
            ingestion_queues[project_id] = asyncio.Queue()
        else:
            return EventSourceResponse(iter([{"event": "message", "data": json.dumps({"phase": "idle", "message": "No active ingestion"})}]))
            
    q = ingestion_queues[project_id]
    
    async def event_generator():
        try:
            while True:
                event = await q.get()
                yield {"event": "message", "data": json.dumps(event)}
                if event.get("phase") in ("completed", "error"):
                    break
        except asyncio.CancelledError:
            logger.info(f"Progress streaming client disconnected for project {project_id}")
        finally:
            if project_id in ingestion_queues:
                del ingestion_queues[project_id]
                
    return EventSourceResponse(event_generator())


# Exploration API
@app.post("/api/projects/{project_id}/chat")
async def chat_explore(project_id: int, req: ChatRequest):
    p = await pm.get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    history = [{"role": msg.role, "content": msg.content} for msg in req.history]
    
    async def chat_event_generator():
        try:
            async for event in explore(req.query, project_id, history):
                yield {"event": "message", "data": json.dumps(event)}
        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield {"event": "message", "data": json.dumps({"type": "error", "data": {"message": str(e)}})}
            
    return EventSourceResponse(chat_event_generator())


# Memory API
@app.get("/api/projects/{project_id}/memory")
async def get_memory(project_id: int):
    try:
        return await am.get_all_memories(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/memory")
async def add_semantic_memory(project_id: int, req: MemoryCreate):
    try:
        mem_id = await am.save_semantic_memory(project_id, req.content)
        return {"status": "success", "id": mem_id, "message": "Semantic memory saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}/memory/{memory_id}")
async def delete_memory(project_id: int, memory_id: int, type: str = Query("semantic")):
    try:
        await am.delete_memory(memory_id, type)
        return {"status": "success", "message": f"{type.capitalize()} memory deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/memory/clear")
async def clear_memory(project_id: int, type: str = Query("semantic")):
    try:
        await am.clear_memory(project_id, type)
        return {"status": "success", "message": f"All {type} memories cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}/memory/search")
async def search_memory(project_id: int, q: str = Query(...)):
    try:
        return await am.search_memories(q, project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}/memory/summary")
async def get_exploration_summary(project_id: int):
    try:
        return await am.get_exploration_summary(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Files & Browser API
@app.get("/api/projects/{project_id}/files")
async def get_file_tree(project_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT file_path, is_directory, language FROM file_tree WHERE project_id = $1 ORDER BY is_directory DESC, file_path ASC",
            project_id
        )
    return [dict(r) for r in rows]


@app.get("/api/projects/{project_id}/files/content")
async def get_file_content(project_id: int, file_path: str = Query(...)):
    res = await read_file(file_path, project_id)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


if __name__ == "__main__":
    import uvicorn
    # Make sure env config port is respected
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
