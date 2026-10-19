"""
Thread-safe storage utility supporting Neon PostgreSQL with local JSON backup sync.
All data files live in the project-root/data/ directory and mirror tables in Neon.
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional

from database import (
    is_db_configured,
    get_table_for_file,
    db_fetch_all,
    db_find_by_id,
    db_upsert_record,
    db_insert_batch,
    db_delete_by_id,
    db_delete_where,
    db_clear_table,
)

logger = logging.getLogger("backend.storage")

# Resolve data directory relative to this file's location
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# One lock per file path to allow concurrent access to different files
_locks: dict[str, threading.Lock] = {}
_meta_lock = threading.Lock()


def _get_lock(filepath: str) -> threading.Lock:
    with _meta_lock:
        if filepath not in _locks:
            _locks[filepath] = threading.Lock()
        return _locks[filepath]


def _resolve_path(filename: str) -> str:
    """Resolve a filename to an absolute path inside DATA_DIR."""
    path = DATA_DIR / filename
    return str(path)


_STATIC_CACHE: dict[str, list[dict[str, Any]]] = {}


def read_json(filename: str) -> list[dict[str, Any]]:
    """
    Read data. If Neon PostgreSQL is configured, read directly from database.
    Falls back to local JSON file if database is offline or unconfigured.
    """
    if filename in ("scenarios.json", "scaffolds.json") and filename in _STATIC_CACHE:
        return _STATIC_CACHE[filename]

    if is_db_configured():
        table_name = get_table_for_file(filename)
        if table_name:
            try:
                res = db_fetch_all(table_name)
                if filename in ("scenarios.json", "scaffolds.json"):
                    _STATIC_CACHE[filename] = res
                return res
            except Exception as e:
                logger.warning(f"Database read failed for {table_name}, falling back to file: {e}")

    # File-based read
    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)
    with lock:
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            try:
                res = json.loads(content)
                if filename in ("scenarios.json", "scaffolds.json"):
                    _STATIC_CACHE[filename] = res
                return res
            except Exception:
                return []


def write_json(filename: str, data: list[dict[str, Any]]) -> None:
    """
    Write data. Updates local JSON file and persists to Neon PostgreSQL.
    """
    _STATIC_CACHE.pop(filename, None)

    # 1. Update local JSON file (thread-safe)
    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)
    with lock:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # 2. Persist to Neon PostgreSQL if configured
    if is_db_configured():
        table_name = get_table_for_file(filename)
        if table_name:
            try:
                if not data:
                    db_clear_table(table_name)
                else:
                    db_insert_batch(table_name, data)
            except Exception as e:
                logger.warning(f"Database write failed for {table_name}: {e}")


def upsert_record(filename: str, item: dict[str, Any]) -> dict[str, Any]:
    """
    Upsert a single record into both local JSON file and Neon PostgreSQL.
    High-performance single-record write without re-serializing entire table to DB.
    """
    if not isinstance(item, dict) or not item.get("id"):
        raise ValueError("Item must be a dictionary with an 'id' field")

    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)
    with lock:
        existing: list[dict[str, Any]] = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    try:
                        existing = json.loads(content)
                    except Exception:
                        existing = []

        found = False
        for i, rec in enumerate(existing):
            if filename == "coding.json":
                if rec.get("response_id") == item.get("response_id") and rec.get("coder_id") == item.get("coder_id"):
                    existing[i] = item
                    found = True
                    break
            else:
                if rec.get("id") == item.get("id"):
                    existing[i] = item
                    found = True
                    break

        if not found:
            existing.append(item)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

    if is_db_configured():
        table_name = get_table_for_file(filename)
        if table_name:
            try:
                db_upsert_record(table_name, item)
            except Exception as e:
                logger.warning(f"Database single upsert failed for {table_name}: {e}")

    return item


def append_json(filename: str, items: list[dict[str, Any]]) -> None:
    """
    Append items to local JSON file and insert into Neon PostgreSQL.
    """
    if not items:
        return

    # 1. Append to local JSON file (thread-safe)
    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)
    with lock:
        existing: list[dict[str, Any]] = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    try:
                        existing = json.loads(content)
                    except Exception:
                        existing = []

        existing.extend(items)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

    # 2. Insert into Neon PostgreSQL if configured
    if is_db_configured():
        table_name = get_table_for_file(filename)
        if table_name:
            try:
                db_insert_batch(table_name, items)
            except Exception as e:
                logger.warning(f"Database append failed for {table_name}: {e}")


def find_by_id(filename: str, item_id: str) -> dict[str, Any] | None:
    """Find a single item by its 'id' field in DB or local file."""
    if is_db_configured():
        table_name = get_table_for_file(filename)
        if table_name:
            try:
                row = db_find_by_id(table_name, item_id)
                if row is not None:
                    return row
            except Exception as e:
                logger.warning(f"Database find_by_id failed for {table_name}: {e}")

    # File-based lookup
    data = read_json(filename)
    for item in data:
        if item.get("id") == item_id:
            return item
    return None


def update_by_id(filename: str, item_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update an item by ID, merging updates in DB and local file."""
    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)
    updated_item = None

    with lock:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                data = json.loads(content) if content else []
        else:
            data = []

        for i, item in enumerate(data):
            if item.get("id") == item_id:
                data[i] = {**item, **updates}
                updated_item = data[i]
                break

        if updated_item is not None:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    # Update in Neon PostgreSQL
    if is_db_configured() and updated_item:
        table_name = get_table_for_file(filename)
        if table_name:
            try:
                db_upsert_record(table_name, updated_item)
            except Exception as e:
                logger.warning(f"Database update_by_id failed for {table_name}: {e}")

    return updated_item


def delete_by_id(filename: str, item_id: str) -> bool:
    """Delete an item by ID in DB and local file."""
    deleted_local = False
    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)

    with lock:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                data = json.loads(content) if content else []
            original_len = len(data)
            data = [item for item in data if item.get("id") != item_id]
            if len(data) < original_len:
                deleted_local = True
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

    # Delete in Neon PostgreSQL
    if is_db_configured():
        table_name = get_table_for_file(filename)
        if table_name:
            try:
                db_delete_by_id(table_name, item_id)
            except Exception as e:
                logger.warning(f"Database delete_by_id failed for {table_name}: {e}")

    return deleted_local
