"""
Neon PostgreSQL database integration.
Handles connection management, schema initialization, and CRUD operations.
"""

import os
import json
import logging
from typing import Any, Optional
from contextlib import contextmanager
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

# Load .env from project root or backend directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger("backend.database")

DATABASE_URL = os.getenv("DATABASE_URL")


import queue

def is_db_configured() -> bool:
    """Check if DATABASE_URL is set and non-empty."""
    return bool(DATABASE_URL and DATABASE_URL.strip())


_POOL_SIZE = 5
_conn_pool: queue.Queue = queue.Queue(maxsize=_POOL_SIZE)


def _is_conn_alive(conn) -> bool:
    """Check if connection is open and responsive."""
    try:
        if conn.closed:
            return False
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
        return True
    except Exception:
        return False


@contextmanager
def get_db_connection():
    """Context manager yielding a pooled psycopg connection with dict_row factory."""
    if not is_db_configured():
        raise RuntimeError("DATABASE_URL is not configured in .env")

    conn = None
    while not _conn_pool.empty():
        try:
            candidate = _conn_pool.get_nowait()
            if _is_conn_alive(candidate):
                conn = candidate
                break
            else:
                try:
                    candidate.close()
                except Exception:
                    pass
        except queue.Empty:
            break

    if conn is None:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    try:
        yield conn
        conn.commit()
        try:
            _conn_pool.put_nowait(conn)
        except queue.Full:
            conn.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        raise


# ── DDL Schema Definition ─────────────────────────────────────────────────────

SCHEMA_SQL = """
-- 1. Scenarios table
CREATE TABLE IF NOT EXISTS scenarios (
    id VARCHAR(64) PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    scenario_text TEXT NOT NULL,
    category VARCHAR(64) NOT NULL,
    category_other VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Scaffolds table
CREATE TABLE IF NOT EXISTS scaffolds (
    id VARCHAR(64) PRIMARY KEY,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    version VARCHAR(32) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. Experiments table
CREATE TABLE IF NOT EXISTS experiments (
    id VARCHAR(64) PRIMARY KEY,
    scenario_id VARCHAR(64) REFERENCES scenarios(id) ON DELETE CASCADE,
    scaffold_id VARCHAR(64) REFERENCES scaffolds(id) ON DELETE CASCADE,
    model VARCHAR(128) NOT NULL,
    temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,
    top_p DOUBLE PRECISION NOT NULL DEFAULT 0.9,
    max_tokens INTEGER NOT NULL DEFAULT 512,
    top_k INTEGER NOT NULL DEFAULT 40,
    repeat_penalty DOUBLE PRECISION NOT NULL DEFAULT 1.1,
    seed INTEGER,
    num_replicates INTEGER NOT NULL DEFAULT 20,
    swap_type VARCHAR(64) DEFAULT 'npc',
    status VARCHAR(32) NOT NULL DEFAULT 'configured',
    tag VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Responses table
CREATE TABLE IF NOT EXISTS responses (
    id VARCHAR(64) PRIMARY KEY,
    pair_id VARCHAR(64) NOT NULL,
    experiment_id VARCHAR(64) REFERENCES experiments(id) ON DELETE CASCADE,
    scenario_id VARCHAR(64) REFERENCES scenarios(id) ON DELETE CASCADE,
    scaffold_id VARCHAR(64) REFERENCES scaffolds(id) ON DELETE CASCADE,
    scaffold_version VARCHAR(32) NOT NULL,
    model VARCHAR(128) NOT NULL,
    temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,
    top_p DOUBLE PRECISION DEFAULT 0.9,
    top_k INTEGER DEFAULT 40,
    repeat_penalty DOUBLE PRECISION DEFAULT 1.1,
    max_tokens INTEGER DEFAULT 512,
    seed INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    condition VARCHAR(32) NOT NULL,
    replicate_number INTEGER NOT NULL DEFAULT 1,
    scaffold_prompt TEXT,
    scenario_prompt TEXT,
    system_prompt TEXT,
    user_prompt TEXT,
    generated_response TEXT NOT NULL,
    tag VARCHAR(64)
);

-- Indexes for responses
CREATE INDEX IF NOT EXISTS idx_responses_pair_id ON responses(pair_id);
CREATE INDEX IF NOT EXISTS idx_responses_experiment_id ON responses(experiment_id);
CREATE INDEX IF NOT EXISTS idx_responses_model ON responses(model);
CREATE INDEX IF NOT EXISTS idx_responses_scenario_id ON responses(scenario_id);
CREATE INDEX IF NOT EXISTS idx_responses_condition ON responses(condition);

-- 5. Codings table
CREATE TABLE IF NOT EXISTS codings (
    id VARCHAR(64) PRIMARY KEY,
    response_id VARCHAR(64) REFERENCES responses(id) ON DELETE CASCADE,
    coder_id VARCHAR(64) NOT NULL,
    truth DOUBLE PRECISION NOT NULL CHECK (truth >= 0.0 AND truth <= 1.0),
    indeterminacy DOUBLE PRECISION NOT NULL CHECK (indeterminacy >= 0.0 AND indeterminacy <= 1.0),
    falsity DOUBLE PRECISION NOT NULL CHECK (falsity >= 0.0 AND falsity <= 1.0),
    reasoning_notes TEXT,
    coded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_response_coder UNIQUE (response_id, coder_id)
);

-- Indexes for codings
CREATE INDEX IF NOT EXISTS idx_codings_response_id ON codings(response_id);
CREATE INDEX IF NOT EXISTS idx_codings_coder_id ON codings(coder_id);
"""


def init_db() -> bool:
    """Initialize database schema in Neon PostgreSQL."""
    if not is_db_configured():
        logger.warning("DATABASE_URL not set; skipping database initialization.")
        return False

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
        logger.info("Neon PostgreSQL schema initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        return False


# ── File-to-Table Mapping ─────────────────────────────────────────────────────

FILE_TABLE_MAP = {
    "scenarios.json": "scenarios",
    "scaffolds.json": "scaffolds",
    "experiments.json": "experiments",
    "responses.json": "responses",
    "coding.json": "codings",
}


def get_table_for_file(filename: str) -> Optional[str]:
    """Get the SQL table name corresponding to a JSON filename."""
    base = Path(filename).name
    return FILE_TABLE_MAP.get(base)


# ── Generic Query Helpers ─────────────────────────────────────────────────────

def db_fetch_all(table_name: str) -> list[dict[str, Any]]:
    """Fetch all records from a table as a list of dicts."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table_name};")
            rows = cur.fetchall()
            # Convert ISO datetime objects to string format matching JSON storage
            result = []
            for r in rows:
                d = dict(r)
                for k, v in d.items():
                    if hasattr(v, "isoformat"):
                        d[k] = v.isoformat()
                result.append(d)
            return result


def db_find_by_id(table_name: str, item_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single record by its ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table_name} WHERE id = %s;", (item_id,))
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            return d


_TABLE_COLUMNS_CACHE: dict[str, set[str]] = {}


def get_table_columns(table_name: str) -> set[str]:
    """Retrieve and cache column names for a table."""
    if table_name in _TABLE_COLUMNS_CACHE:
        return _TABLE_COLUMNS_CACHE[table_name]

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s;
                """,
                (table_name,),
            )
            cols = {row["column_name"] for row in cur.fetchall()}
            _TABLE_COLUMNS_CACHE[table_name] = cols
            return cols


def db_upsert_record(table_name: str, record: dict[str, Any]) -> dict[str, Any]:
    """Insert or update a single record by ID."""
    if not record.get("id"):
        raise ValueError("Record must contain an 'id' field")

    valid_cols = get_table_columns(table_name)
    cleaned = {k: v for k, v in record.items() if k in valid_cols}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            keys = list(cleaned.keys())
            cols = ", ".join(keys)
            placeholders = ", ".join(["%s"] * len(keys))
            
            if table_name == "codings":
                # Codings has unique constraint on (response_id, coder_id)
                update_cols = [k for k in keys if k not in ("id", "response_id", "coder_id")]
                if update_cols:
                    update_clause = ", ".join([f"{k} = EXCLUDED.{k}" for k in update_cols])
                    sql = f"""
                        INSERT INTO {table_name} ({cols}) 
                        VALUES ({placeholders})
                        ON CONFLICT (response_id, coder_id) 
                        DO UPDATE SET {update_clause};
                    """
                else:
                    sql = f"""
                        INSERT INTO {table_name} ({cols}) 
                        VALUES ({placeholders})
                        ON CONFLICT (response_id, coder_id) DO NOTHING;
                    """
            else:
                update_cols = [k for k in keys if k != "id"]
                if update_cols:
                    update_clause = ", ".join([f"{k} = EXCLUDED.{k}" for k in update_cols])
                    sql = f"""
                        INSERT INTO {table_name} ({cols}) 
                        VALUES ({placeholders})
                        ON CONFLICT (id) 
                        DO UPDATE SET {update_clause};
                    """
                else:
                    sql = f"""
                        INSERT INTO {table_name} ({cols}) 
                        VALUES ({placeholders})
                        ON CONFLICT (id) DO NOTHING;
                    """
            
            values = [cleaned[k] for k in keys]
            cur.execute(sql, values)
    return cleaned


def db_insert_batch(table_name: str, records: list[dict[str, Any]]) -> None:
    """Insert or update a batch of records into a table."""
    if not records:
        return

    valid_cols = get_table_columns(table_name)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for rec in records:
                cleaned = {k: v for k, v in rec.items() if k in valid_cols}
                keys = list(cleaned.keys())
                cols = ", ".join(keys)
                placeholders = ", ".join(["%s"] * len(keys))
                if table_name == "codings":
                    update_cols = [k for k in keys if k not in ("id", "response_id", "coder_id")]
                    if update_cols:
                        update_clause = ", ".join([f"{k} = EXCLUDED.{k}" for k in update_cols])
                        sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT (response_id, coder_id) DO UPDATE SET {update_clause};"
                    else:
                        sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT (response_id, coder_id) DO NOTHING;"
                elif table_name == "responses":
                    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING;"
                else:
                    update_cols = [k for k in keys if k != "id"]
                    if update_cols:
                        update_clause = ", ".join([f"{k} = EXCLUDED.{k}" for k in update_cols])
                        sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO UPDATE SET {update_clause};"
                    else:
                        sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING;"
                values = [cleaned[k] for k in keys]
                cur.execute(sql, values)


def db_delete_by_id(table_name: str, item_id: str) -> bool:
    """Delete a record by ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {table_name} WHERE id = %s;", (item_id,))
            return cur.rowcount > 0


def db_delete_where(table_name: str, where_clause: str, params: tuple) -> int:
    """Delete records matching a WHERE clause."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {table_name} WHERE {where_clause};", params)
            return cur.rowcount


def db_clear_table(table_name: str) -> None:
    """Clear all records from a table."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {table_name};")


# ── Data Migration ────────────────────────────────────────────────────────────

def migrate_local_json_to_db() -> dict[str, int]:
    """
    Migrate existing local JSON records into Neon PostgreSQL if tables are empty.
    Returns counts of inserted records per table.
    """
    if not is_db_configured():
        return {}

    data_dir = PROJECT_ROOT / "data"
    counts = {}

    # Migration order respecting foreign key constraints:
    # 1. scenarios
    # 2. scaffolds
    # 3. experiments
    # 4. responses
    # 5. codings
    migration_order = [
        ("scenarios.json", "scenarios"),
        ("scaffolds.json", "scaffolds"),
        ("experiments.json", "experiments"),
        ("responses.json", "responses"),
        ("coding.json", "codings"),
    ]

    for json_file, table_name in migration_order:
        path = data_dir / json_file
        if not path.exists():
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    continue
                records = json.loads(content)
        except Exception as e:
            logger.error(f"Failed to read {json_file} for migration: {e}")
            continue

        if not records:
            continue

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {table_name};")
                existing_count = cur.fetchone()["count"]

                if existing_count == 0:
                    inserted = 0

                    # For codings, filter out orphaned records whose response_id is not in responses
                    if table_name == "codings":
                        cur.execute("SELECT id FROM responses;")
                        valid_resp_ids = {row["id"] for row in cur.fetchall()}
                        records = [r for r in records if r.get("response_id") in valid_resp_ids]
                    for rec in records:
                        # Clean up fields for table schema
                        cleaned = dict(rec)
                        
                        # Filter out keys not present in DB table
                        cur.execute(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = %s;
                        """, (table_name,))
                        db_cols = {row["column_name"] for row in cur.fetchall()}
                        cleaned = {k: v for k, v in cleaned.items() if k in db_cols}

                        keys = list(cleaned.keys())
                        cols = ", ".join(keys)
                        placeholders = ", ".join(["%s"] * len(keys))
                        cur.execute(
                            f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;",
                            [cleaned[k] for k in keys]
                        )
                        inserted += 1
                    counts[table_name] = inserted
                    logger.info(f"Migrated {inserted} records from {json_file} to {table_name}.")
                else:
                    counts[table_name] = existing_count

    return counts
