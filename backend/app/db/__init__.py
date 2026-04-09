"""Public API for the ``app.db`` package.

Re-exports the most commonly used symbols so callers can write::

    from app.db import get_session, get_engine, create_all, metadata
"""

from app.db.base import create_all, metadata
from app.db.session import SessionDep, get_engine, get_session

__all__ = [
    "create_all",
    "get_engine",
    "get_session",
    "metadata",
    "SessionDep",
]
