"""
JARVIS-MKIII — memory/prune.py
TTL-based pruning for the ChromaDB jarvis_memory collection.

Entries older than RETENTION_DAYS are deleted. Runs automatically
once a week via APScheduler in api/main.py. Can also be triggered
manually via POST /memory/prune.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90


def prune_old_memories(collection, days: int = RETENTION_DAYS) -> int:
    """
    Delete all ChromaDB entries whose 'timestamp' metadata field is
    older than `days` days. Returns the number of deleted entries.

    Args:
        collection: a chromadb Collection object (jarvis_memory)
        days:       retention window in days (default 90)
    """
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    try:
        results = collection.get(
            where={"timestamp": {"$lt": cutoff}},
            include=["metadatas"],
        )
    except Exception as e:
        logger.error("[PRUNE] Failed to query collection: %s", e)
        return 0

    ids = results.get("ids", [])
    if not ids:
        logger.info("[PRUNE] No entries older than %dd — nothing to delete.", days)
        return 0

    try:
        collection.delete(ids=ids)
        logger.info("[PRUNE] Deleted %d entries older than %dd from ChromaDB.", len(ids), days)
    except Exception as e:
        logger.error("[PRUNE] Delete failed: %s", e)
        return 0

    return len(ids)
