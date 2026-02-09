"""
In-memory progress store for long-running tasks.

Thread-safe storage for tracking progress of data collection tasks.
Used with polling-based progress reporting from the frontend.
"""
import threading
from typing import Dict, Any, Optional

_progress: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def update_progress(task_id: str, data: Dict[str, Any]):
    """Update progress for a task."""
    with _lock:
        _progress[task_id] = {**data}


def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
    """Get current progress for a task. Returns None if not found."""
    with _lock:
        return _progress.get(task_id, {}).copy() if task_id in _progress else None


def clear_progress(task_id: str):
    """Clear progress for a completed task."""
    with _lock:
        _progress.pop(task_id, None)
