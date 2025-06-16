"""Database utility functions for TracLine."""

from tracline.core.config import Config
from tracline.db.factory import DatabaseFactory


def get_database(config: Config):
    """Get a database instance from configuration.
    
    This is a context manager that handles database connections.
    
    Usage:
        with get_database(config) as db:
            cursor = db.execute_query("SELECT * FROM tasks", [])
            results = cursor.fetchall()
    """
    db_config = config.get_database_config()
    return DatabaseFactory.create(db_config)