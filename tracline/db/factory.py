"""Database factory for TracLine."""

from typing import Dict, Type, List
from tracline.core.config import DatabaseConfig
from tracline.db.interface import DatabaseInterface


class DatabaseFactory:
    """Factory for creating database instances."""
    
    _database_types: Dict[str, Type[DatabaseInterface]] = {}
    
    @classmethod
    def register(cls, db_type: str, db_class: Type[DatabaseInterface]) -> None:
        """Register a database implementation."""
        cls._database_types[db_type.lower()] = db_class
    
    @classmethod
    def create(cls, config: DatabaseConfig) -> DatabaseInterface:
        """Create a database instance based on configuration."""
        db_type = config.type.lower()
        
        if db_type not in cls._database_types:
            raise ValueError(f"Unknown database type: {db_type}")
        
        db_class = cls._database_types[db_type]
        return db_class(config)
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of available database types."""
        return list(cls._database_types.keys())


# Auto-register database types
def _auto_register():
    """Auto-register available database implementations."""
    try:
        from tracline.db.postgresql import PostgreSQLDatabase
        DatabaseFactory.register("postgresql", PostgreSQLDatabase)
        DatabaseFactory.register("postgres", PostgreSQLDatabase)
    except ImportError:
        pass
    
    try:
        from tracline.db.sqlite import SQLiteDatabase
        DatabaseFactory.register("sqlite", SQLiteDatabase)
        DatabaseFactory.register("sqlite3", SQLiteDatabase)
    except ImportError:
        pass
    
    try:
        from tracline.db.mysql import MySQLDatabase
        DatabaseFactory.register("mysql", MySQLDatabase)
        DatabaseFactory.register("mariadb", MySQLDatabase)
    except ImportError:
        pass
    
    try:
        from tracline.db.mongodb import MongoDBDatabase
        DatabaseFactory.register("mongodb", MongoDBDatabase)
        DatabaseFactory.register("mongo", MongoDBDatabase)
    except ImportError:
        pass


_auto_register()