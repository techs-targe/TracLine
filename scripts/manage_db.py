#!/usr/bin/env python3
"""Database management utility for TracLine."""

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def drop_database():
    """Drop the TracLine database."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port='5432', 
            user='postgres',
            password='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Dropping database 'tracline'...")
        cursor.execute("DROP DATABASE IF EXISTS tracline")
        print("Database dropped successfully.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def create_database():
    """Create the TracLine database."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port='5432',
            user='postgres', 
            password='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Creating database 'tracline'...")
        cursor.execute("CREATE DATABASE tracline")
        print("Database created successfully.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def reset_database():
    """Drop and recreate the TracLine database."""
    drop_database()
    create_database()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage_db.py [drop|create|reset]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "drop":
        drop_database()
    elif command == "create":
        create_database()
    elif command == "reset":
        reset_database()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python manage_db.py [drop|create|reset]")
        sys.exit(1)