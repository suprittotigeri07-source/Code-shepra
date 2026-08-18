"""Database connection and schema management for Code Sherpa."""
import asyncio
import logging
import sqlite3
import json
import re
import math
from datetime import datetime, timezone
from pathlib import Path

# Try importing asyncpg, but fallback if not installed or connection fails
try:
    import asyncpg
except ImportError:
    asyncpg = None

from config import settings

logger = logging.getLogger(__name__)

# Global state
_pool = None
IS_SQLITE = False
_sqlite_conn = None


def sqlite_cosine_distance(v1_str, v2_str):
    if not v1_str or not v2_str:
        return 1.0
    try:
        if isinstance(v1_str, str):
            v1_str = v1_str.strip()
            if v1_str.startswith('[') and v1_str.endswith(']'):
                v1 = json.loads(v1_str)
            else:
                v1 = [float(x) for x in v1_str.split(',') if x.strip()]
        else:
            v1 = list(v1_str)
            
        if isinstance(v2_str, str):
            v2_str = v2_str.strip()
            if v2_str.startswith('[') and v2_str.endswith(']'):
                v2 = json.loads(v2_str)
            else:
                v2 = [float(x) for x in v2_str.split(',') if x.strip()]
        else:
            v2 = list(v2_str)
            
        dot_product = sum(x * y for x, y in zip(v1, v2))
        norm_v1 = math.sqrt(sum(x * x for x in v1))
        norm_v2 = math.sqrt(sum(x * x for x in v2))
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 1.0
            
        similarity = dot_product / (norm_v1 * norm_v2)
        return 1.0 - similarity
    except Exception:
        return 1.0


def sqlite_ts_match(content, query_str):
    if not content or not query_str:
        return False
    words = [w.strip().lower() for w in query_str.split('|') if w.strip()]
    content_lower = content.lower()
    return any(w in content_lower for w in words)


def sqlite_ts_rank(content, query_str):
    if not content or not query_str:
        return 0.0
    words = [w.strip().lower() for w in query_str.split('|') if w.strip()]
    content_lower = content.lower()
    score = 0.0
    for w in words:
        count = content_lower.count(w)
        score += count * 1.0
    return score


def translate_sql(sql: str) -> str:
    if IS_SQLITE:
        # Translate vector operators
        # Match e.g. embedding <=> $1 or embedding <=> '...'::vector
        sql = re.sub(r'(\w+)\s*<=>\s*(\'[^\']+\'|\$\d+|\?)(?:::vector)?', r'cosine_distance(\1, \2)', sql)
        sql = sql.replace("1 - (embedding <=> ", "1 - (cosine_distance(embedding, ")
        # Translate fulltext matching
        sql = sql.replace("content_tsv @@ to_tsquery('english', $2)", "ts_match(content, $2)")
        sql = sql.replace("content_tsv @@ to_tsquery('english', ?)", "ts_match(content, ?)")
        # Translate fulltext ranking
        sql = sql.replace("ts_rank_cd(content_tsv, to_tsquery('english', $2))", "ts_rank(content, $2)")
        sql = sql.replace("ts_rank_cd(content_tsv, to_tsquery('english', ?))", "ts_rank(content, ?)")
        
        # Schema definition translations
        sql = sql.replace("CREATE EXTENSION IF NOT EXISTS vector;", "-- CREATE EXTENSION")
        sql = re.sub(r'vector\(\d+\)', 'TEXT', sql)
        sql = sql.replace("vector", "TEXT")
        sql = sql.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
        sql = sql.replace("TIMESTAMPTZ", "TIMESTAMP")
        sql = sql.replace("NOW()", "CURRENT_TIMESTAMP")
        sql = sql.replace("TEXT[] DEFAULT ARRAY[]::TEXT[]", "TEXT DEFAULT '[]'")
        # Remove pg specific column and index formats
        sql = sql.replace("content_tsv tsvector,", "content_tsv TEXT,")
        sql = sql.replace("content_tsv tsvector", "content_tsv TEXT")
        sql = sql.replace("USING GIN(content_tsv)", "(content_tsv)")
        sql = sql.replace("USING ivfflat (embedding vector_cosine_ops)", "(embedding)")
        sql = sql.replace("USING ivfflat", "")
        sql = sql.replace("WITH (lists = ?)", "")
        # Replace $ placeholders with ?
        sql = re.sub(r'\$(\d+)', r'?', sql)
    return sql


def process_args_for_sqlite(args):
    if not IS_SQLITE:
        return args
    processed = []
    for arg in args:
        if isinstance(arg, list):
            # Check if list of strings/ints or floats (vector)
            if arg and isinstance(arg[0], float):
                processed.append(json.dumps(arg))
            else:
                processed.append(json.dumps(arg))
        elif isinstance(arg, dict):
            processed.append(json.dumps(arg))
        else:
            processed.append(arg)
    return tuple(processed)


def postprocess_record(record: dict):
    if not IS_SQLITE:
        return record
    # If the record contains vector as string, parse it
    if "embedding" in record and isinstance(record["embedding"], str):
        try:
            record["embedding"] = json.loads(record["embedding"])
        except Exception:
            try:
                record["embedding"] = [float(x) for x in record["embedding"].split(",") if x.strip()]
            except Exception:
                pass
    # If the record contains files_explored as string, parse it
    if "files_explored" in record and isinstance(record["files_explored"], str):
        try:
            record["files_explored"] = json.loads(record["files_explored"])
        except Exception:
            record["files_explored"] = []
    return record


class SQLiteRecord(dict):
    """Mimics asyncpg.Record."""
    def __init__(self, colnames, values):
        super().__init__(zip(colnames, values))
        self._values = values
        
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)
        
    def get(self, key, default=None):
        return super().get(key, default)


class SQLiteConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn
        
    async def execute(self, sql: str, *args):
        translated_sql = translate_sql(sql)
        processed_args = process_args_for_sqlite(args)
        
        def _exec():
            cursor = self._conn.cursor()
            try:
                cursor.execute(translated_sql, processed_args)
                self._conn.commit()
            except Exception as e:
                logger.error(f"SQLite execute error: {e} | SQL: {translated_sql}")
                raise e
            finally:
                cursor.close()
        await asyncio.to_thread(_exec)
        return "SUCCESS"
        
    async def fetch(self, sql: str, *args):
        translated_sql = translate_sql(sql)
        processed_args = process_args_for_sqlite(args)
        
        def _fetch():
            cursor = self._conn.cursor()
            try:
                cursor.execute(translated_sql, processed_args)
                rows = cursor.fetchall()
                colnames = [d[0] for d in cursor.description] if cursor.description else []
                return [SQLiteRecord(colnames, r) for r in rows]
            except Exception as e:
                logger.error(f"SQLite fetch error: {e} | SQL: {translated_sql}")
                raise e
            finally:
                cursor.close()
                
        records = await asyncio.to_thread(_fetch)
        for r in records:
            postprocess_record(r)
        return records
        
    async def fetchrow(self, sql: str, *args):
        records = await self.fetch(sql, *args)
        return records[0] if records else None
        
    async def fetchval(self, sql: str, *args):
        row = await self.fetchrow(sql, *args)
        if row is not None:
            return list(row.values())[0]
        return None


class SQLitePoolWrapper:
    def __init__(self, conn_path):
        self.conn_path = conn_path
        
    def acquire(self):
        class ConnectionContext:
            def __init__(self, conn):
                self.conn = conn
            async def __aenter__(self):
                return SQLiteConnectionWrapper(self.conn)
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return ConnectionContext(_sqlite_conn)
        
    async def close(self):
        global _sqlite_conn
        if _sqlite_conn:
            _sqlite_conn.close()
            _sqlite_conn = None


async def get_pool():
    """Get or create the connection pool (asyncpg or SQLite fallback)."""
    global _pool, IS_SQLITE, _sqlite_conn
    if _pool is None:
        if asyncpg:
            try:
                url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
                _pool = await asyncio.wait_for(
                    asyncpg.create_pool(url, min_size=2, max_size=10),
                    timeout=5.0
                )
                IS_SQLITE = False
                logger.info("Connected to PostgreSQL successfully.")
                return _pool
            except Exception as e:
                logger.warning(f"Failed to connect to PostgreSQL: {e}. Falling back to SQLite.")
        
        # Falling back to SQLite
        IS_SQLITE = True
        db_path = Path("d:/Projects/code-shepra/backend/code_sherpa.db").resolve()
        db_path.parent.mkdir(exist_ok=True)
        
        _sqlite_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        _sqlite_conn.row_factory = sqlite3.Row
        
        _sqlite_conn.create_function("cosine_distance", 2, sqlite_cosine_distance)
        _sqlite_conn.create_function("ts_match", 2, sqlite_ts_match)
        _sqlite_conn.create_function("ts_rank", 2, sqlite_ts_rank)
        
        _pool = SQLitePoolWrapper(str(db_path))
        logger.info(f"Initialized SQLite database fallback at {db_path}.")
        
    return _pool


async def close_pool():
    global _pool, _sqlite_conn
    if _pool:
        await _pool.close()
        _pool = None


async def init_database():
    """Initialize database schema with pgvector extension and all tables."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Enable pgvector extension (ignored in SQLite)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Projects table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                source_path TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_ingestion TIMESTAMPTZ,
                file_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0,
                is_ingesting BOOLEAN DEFAULT FALSE
            );
        """)
        
        # Code chunks table with vector embeddings
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS code_chunks (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                file_hash VARCHAR(64),
                chunk_type VARCHAR(50) NOT NULL,
                chunk_name VARCHAR(255) DEFAULT '',
                language VARCHAR(50) NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector({settings.EMBEDDING_DIMENSIONS}),
                content_tsv tsvector,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(project_id, file_path, start_line, end_line)
            );
        """)
        
        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_project 
            ON code_chunks(project_id);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_file_path 
            ON code_chunks(project_id, file_path);
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_file_hash 
            ON code_chunks(project_id, file_hash);
        """)
        
        # Full-text search index
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_tsv 
            ON code_chunks USING GIN(content_tsv);
        """)
        
        # Episodic memory table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                query TEXT NOT NULL,
                files_explored TEXT[] DEFAULT ARRAY[]::TEXT[],
                summary TEXT NOT NULL,
                embedding vector({settings.EMBEDDING_DIMENSIONS}),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        # Semantic memory table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                embedding vector({settings.EMBEDDING_DIMENSIONS}),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        
        # File tree metadata (for browsing)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS file_tree (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                file_path TEXT NOT NULL,
                is_directory BOOLEAN DEFAULT FALSE,
                language VARCHAR(50) DEFAULT '',
                file_size INTEGER DEFAULT 0,
                UNIQUE(project_id, file_path)
            );
        """)
        
        logger.info("Database schema initialized successfully.")


async def create_vector_index(project_id: int):
    """Create IVFFlat vector index for a project after ingestion."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check how many chunks exist
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM code_chunks WHERE project_id = $1",
            project_id
        )
        if count >= 100:
            nlist = max(1, min(int(count ** 0.5), 100))
            try:
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_chunks_vector_{project_id}
                    ON code_chunks USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = {nlist})
                    WHERE project_id = {project_id};
                """)
                logger.info(f"Created IVFFlat index for project {project_id} with {nlist} lists")
            except Exception as e:
                logger.warning(f"Could not create IVFFlat index: {e}")
        else:
            logger.info(f"Skipping IVFFlat index for project {project_id} ({count} chunks, need >= 100)")
