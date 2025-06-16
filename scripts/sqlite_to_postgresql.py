#!/usr/bin/env python3
"""
SQLite to PostgreSQL migration script for TracLine.
This script migrates data from a SQLite database to PostgreSQL.
"""

import os
import sys
import argparse
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 package not found. Please install it with 'pip install psycopg2-binary'")
    sys.exit(1)

from tracline.core.config import Config, DatabaseConfig

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_sqlite_connection(db_path: str) -> sqlite3.Connection:
    """Get a connection to SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error connecting to SQLite database: {e}")
        sys.exit(1)

def get_postgresql_connection(params: Dict[str, Any]) -> Tuple[Any, Any]:
    """Get a connection to PostgreSQL database."""
    try:
        conn = psycopg2.connect(**params)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        return conn, cursor
    except psycopg2.Error as e:
        logger.error(f"Error connecting to PostgreSQL database: {e}")
        sys.exit(1)

def get_sqlite_tables(conn: sqlite3.Connection) -> List[str]:
    """Get list of tables in SQLite database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor.fetchall()]

def create_postgresql_schema(pg_conn: Any, pg_cursor: Any, sqlite_conn: sqlite3.Connection) -> None:
    """Create PostgreSQL schema based on SQLite schema."""
    logger.info("Creating PostgreSQL schema")
    
    # Get SQLite tables
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    
    for table in tables:
        # Get SQLite table schema
        sqlite_cursor.execute(f"PRAGMA table_info({table})")
        columns = sqlite_cursor.fetchall()
        
        # Skip empty tables or system tables
        if not columns:
            continue
            
        # Map SQLite types to PostgreSQL types
        type_map = {
            "INTEGER": "INTEGER",
            "REAL": "DOUBLE PRECISION",
            "TEXT": "TEXT",
            "BLOB": "BYTEA",
            "TIMESTAMP": "TIMESTAMP",
            "DATETIME": "TIMESTAMP",
            "BOOLEAN": "BOOLEAN",
            "VARCHAR": "VARCHAR",
        }
        
        # Prepare schema for PostgreSQL
        column_defs = []
        primary_key = None
        
        for col in columns:
            name = col['name']
            col_type = col['type'].upper()
            not_null = "NOT NULL" if col['notnull'] else ""
            
            # Handle column type conversion
            for sqlite_type, pg_type in type_map.items():
                if sqlite_type in col_type:
                    col_type = pg_type
                    break
            
            # Handle VARCHAR with length
            if "VARCHAR" in col['type'].upper() and "(" in col['type']:
                col_type = col['type'].upper()
                
            if col['pk']:
                primary_key = name
                column_defs.append(f"{name} {col_type} {not_null}")
            else:
                column_defs.append(f"{name} {col_type} {not_null}")
        
        # Add primary key constraint
        if primary_key:
            column_defs.append(f"PRIMARY KEY ({primary_key})")
            
        # Create table in PostgreSQL
        try:
            create_table_sql = f"CREATE TABLE IF NOT EXISTS {table} (\n  " + ",\n  ".join(column_defs) + "\n)"
            logger.info(f"Creating table {table}")
            pg_cursor.execute(create_table_sql)
            pg_conn.commit()
        except Exception as e:
            logger.error(f"Error creating table {table}: {e}")
            pg_conn.rollback()

def migrate_data(
    sqlite_conn: sqlite3.Connection, 
    pg_conn: Any, 
    pg_cursor: Any,
    tables_to_migrate: Optional[List[str]] = None
) -> None:
    """Migrate data from SQLite to PostgreSQL."""
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get all tables or use provided list
    if not tables_to_migrate:
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables_to_migrate = [row[0] for row in sqlite_cursor.fetchall()]
    
    total_rows_migrated = 0
    
    for table in tables_to_migrate:
        try:
            # Get column names
            sqlite_cursor.execute(f"PRAGMA table_info({table})")
            columns = [col['name'] for col in sqlite_cursor.fetchall()]
            
            if not columns:
                logger.warning(f"Table {table} has no columns, skipping")
                continue
                
            # Select all rows from SQLite
            sqlite_cursor.execute(f"SELECT * FROM {table}")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                logger.info(f"Table {table} is empty, skipping")
                continue
                
            # Prepare batch insert
            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            # Insert in batches to improve performance
            batch_size = 100
            total_rows = len(rows)
            migrated = 0
            
            for i in range(0, total_rows, batch_size):
                batch = rows[i:i+batch_size]
                batch_values = []
                
                for row in batch:
                    # Convert row to list of values
                    row_values = []
                    for col in columns:
                        # Handle NULL values
                        if col in row and row[col] is not None:
                            row_values.append(row[col])
                        else:
                            row_values.append(None)
                    batch_values.append(row_values)
                
                # Execute batch insert
                pg_cursor.executemany(insert_sql, batch_values)
                pg_conn.commit()
                
                migrated += len(batch)
                logger.info(f"Migrated {migrated}/{total_rows} rows from table {table}")
            
            total_rows_migrated += total_rows
            logger.info(f"Completed migration of {total_rows} rows from table {table}")
            
        except Exception as e:
            logger.error(f"Error migrating table {table}: {e}")
            pg_conn.rollback()
    
    logger.info(f"Total rows migrated: {total_rows_migrated}")

def main():
    parser = argparse.ArgumentParser(description="Migrate TracLine data from SQLite to PostgreSQL")
    parser.add_argument("--sqlite-path", type=str, help="Path to SQLite database file")
    parser.add_argument("--host", type=str, default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--dbname", type=str, default="tracline", help="PostgreSQL database name")
    parser.add_argument("--user", type=str, default="postgres", help="PostgreSQL user")
    parser.add_argument("--password", type=str, default="postgres", help="PostgreSQL password")
    parser.add_argument("--skip-schema", action="store_true", help="Skip schema creation")
    parser.add_argument("--tables", type=str, help="Comma-separated list of tables to migrate")
    parser.add_argument("--use-config", action="store_true", help="Use TracLine config for database connections")
    
    args = parser.parse_args()
    
    # Use TracLine config if specified
    if args.use_config:
        config = Config()
        if config.config.database.type == "postgresql":
            pg_params = {
                "host": config.config.database.host or "localhost",
                "port": config.config.database.port or 5432,
                "dbname": config.config.database.database,
                "user": config.config.database.user,
                "password": config.config.database.password
            }
            
            # Default SQLite path from config or use home directory
            home = Path.home()
            default_sqlite_path = home / ".tracline" / "tracline.db"
            sqlite_path = args.sqlite_path or default_sqlite_path
            
            logger.info(f"Using configuration from TracLine:")
            logger.info(f"  PostgreSQL: {pg_params['host']}:{pg_params['port']}/{pg_params['dbname']}")
            logger.info(f"  SQLite: {sqlite_path}")
        else:
            logger.error("TracLine configuration does not use PostgreSQL")
            sys.exit(1)
    else:
        # Use command line arguments
        sqlite_path = args.sqlite_path
        if not sqlite_path:
            home = Path.home()
            sqlite_path = home / ".tracline" / "tracline.db"
            
        pg_params = {
            "host": args.host,
            "port": args.port,
            "dbname": args.dbname,
            "user": args.user,
            "password": args.password
        }
    
    # Check that SQLite database exists
    if not os.path.exists(sqlite_path):
        logger.error(f"SQLite database not found at {sqlite_path}")
        sys.exit(1)
    
    # Tables to migrate
    tables_to_migrate = None
    if args.tables:
        tables_to_migrate = [t.strip() for t in args.tables.split(",")]
    
    # Connect to databases
    logger.info(f"Connecting to SQLite database at {sqlite_path}")
    sqlite_conn = get_sqlite_connection(sqlite_path)
    
    logger.info(f"Connecting to PostgreSQL database at {pg_params['host']}:{pg_params['port']}/{pg_params['dbname']}")
    pg_conn, pg_cursor = get_postgresql_connection(pg_params)
    
    try:
        # Create schema if needed
        if not args.skip_schema:
            create_postgresql_schema(pg_conn, pg_cursor, sqlite_conn)
        
        # Migrate data
        migrate_data(sqlite_conn, pg_conn, pg_cursor, tables_to_migrate)
        
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Error during migration: {e}")
    finally:
        # Close connections
        sqlite_conn.close()
        pg_cursor.close()
        pg_conn.close()

if __name__ == "__main__":
    main()