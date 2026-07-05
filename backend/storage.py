"""
Thread-safe JSON file storage utility.
All data files live in the project-root/data/ directory.
"""

import json
import os
import threading
from pathlib import Path
from typing import Any

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


def read_json(filename: str) -> list[dict[str, Any]]:
    """Read a JSON file and return its contents as a list of dicts."""
    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)
    with lock:
        if not os.path.exists(filepath):
            return []
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)


def write_json(filename: str, data: list[dict[str, Any]]) -> None:
    """Overwrite a JSON file with the given list of dicts."""
    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)
    with lock:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def append_json(filename: str, items: list[dict[str, Any]]) -> None:
    """Append items to an existing JSON array file without overwriting."""
    filepath = _resolve_path(filename)
    lock = _get_lock(filepath)
    with lock:
        existing: list[dict[str, Any]] = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    existing = json.loads(content)

        existing.extend(items)

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)


def find_by_id(filename: str, item_id: str) -> dict[str, Any] | None:
    """Find a single item by its 'id' field."""
    data = read_json(filename)
    for item in data:
        if item.get("id") == item_id:
            return item
    return None


def update_by_id(filename: str, item_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update an item by ID, merging the updates dict into the existing item."""
    data = read_json(filename)
    for i, item in enumerate(data):
        if item.get("id") == item_id:
            data[i] = {**item, **updates}
            write_json(filename, data)
            return data[i]
    return None


def delete_by_id(filename: str, item_id: str) -> bool:
    """Delete an item by ID. Returns True if found and deleted."""
    data = read_json(filename)
    original_len = len(data)
    data = [item for item in data if item.get("id") != item_id]
    if len(data) < original_len:
        write_json(filename, data)
        return True
    return False
