"""
Persistent SQLite-backed checkpoint manager for ResolveAI LangGraph Multi-Agent Workflows.
Provides process-resilient, dedicated storage for workflow states, interruption points,
and human-in-the-loop approvals without conflicting with the business SQLite database.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional, Union
from langgraph.checkpoint.sqlite import SqliteSaver

from app.core.config import settings
from app.core.logging_config import logger

_checkpointer_lock = threading.Lock()
_global_checkpointer: Optional[SqliteSaver] = None
_global_connection: Optional[sqlite3.Connection] = None
_current_db_path: Optional[str] = None


def get_checkpoint_db_path(custom_path: Optional[Union[str, Path]] = None) -> str:
    """Returns the resolved string path to the checkpoint SQLite database."""
    if custom_path is not None:
        if str(custom_path) == ":memory:":
            return ":memory:"
        p = Path(custom_path)
        if not p.is_absolute():
            p = (settings.project_root / p).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    return str(settings.resolved_checkpoint_db_path)


def init_sqlite_checkpointer(
    db_path: Optional[Union[str, Path]] = None
) -> SqliteSaver:
    """
    Initializes and sets up a dedicated SqliteSaver checkpointer.
    Configures SQLite WAL journal mode and busy_timeout for concurrency safety.
    """
    target_path = get_checkpoint_db_path(db_path)
    logger.info("Initializing LangGraph SQLite checkpointer at: %s", target_path)

    conn = sqlite3.connect(target_path, check_same_thread=False, timeout=30.0)
    if target_path != ":memory:":
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
        except Exception as e:
            logger.warning("Failed to configure WAL mode on checkpoint db: %s", e)

    checkpointer = SqliteSaver(conn)
    checkpointer.setup()
    return checkpointer


def get_checkpointer(db_path: Optional[Union[str, Path]] = None) -> SqliteSaver:
    """
    Returns the thread-safe singleton SqliteSaver checkpointer instance.
    Re-initializes if the target db_path changes (e.g., during tests).
    """
    global _global_checkpointer, _global_connection, _current_db_path

    target_path = get_checkpoint_db_path(db_path)

    with _checkpointer_lock:
        if _global_checkpointer is None or _current_db_path != target_path:
            # Close existing connection if switching paths
            if _global_connection is not None:
                try:
                    _global_connection.close()
                except Exception:
                    pass
                _global_connection = None
                _global_checkpointer = None

            conn = sqlite3.connect(target_path, check_same_thread=False, timeout=30.0)
            if target_path != ":memory:":
                try:
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA busy_timeout=5000;")
                except Exception as e:
                    logger.warning("Failed to configure WAL mode on checkpoint db: %s", e)

            saver = SqliteSaver(conn)
            saver.setup()

            _global_connection = conn
            _global_checkpointer = saver
            _current_db_path = target_path

        return _global_checkpointer


def close_checkpointer() -> None:
    """Safely closes the active checkpointer SQLite connection."""
    global _global_checkpointer, _global_connection, _current_db_path

    with _checkpointer_lock:
        if _global_connection is not None:
            try:
                _global_connection.close()
            except Exception as e:
                logger.warning("Error closing checkpointer connection: %s", e)
            _global_connection = None
        _global_checkpointer = None
        _current_db_path = None
