"""Database abstraction layer for TracLine."""

from .interface import DatabaseInterface
from .factory import DatabaseFactory
from .sqlite import SQLiteDatabase
from .utils import get_database

# Import PostgreSQL only if available
try:
    from .postgresql import PostgreSQLDatabase
    __all__ = [
        "DatabaseInterface",
        "DatabaseFactory",
        "PostgreSQLDatabase",
        "SQLiteDatabase",
        "get_database"
    ]
except ImportError:
    __all__ = [
        "DatabaseInterface",
        "DatabaseFactory",
        "SQLiteDatabase",
        "get_database"
    ]