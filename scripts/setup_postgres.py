#!/usr/bin/env python3
"""
Setup PostgreSQL database for TracLine.
This script initializes the PostgreSQL database for TracLine.
"""

import sys
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import time
from pathlib import Path

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, continue with environment variables only
    pass

# Configuration from environment variables with defaults
DB_NAME = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "tracline"))
DB_USER = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "postgres"))
DB_PASS = os.getenv("DB_PASS", os.getenv("POSTGRES_PASSWORD", "postgres"))
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# SQL for database initialization
# Note: For clean installs, tables are dropped and recreated to ensure correct schema
INIT_SQL = """
-- Create TracLine schema
CREATE SCHEMA IF NOT EXISTS tracline;

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL,
    assignee VARCHAR(255),
    priority INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    order_num INTEGER DEFAULT 0,
    project_id VARCHAR(255),
    tags TEXT,
    external_id VARCHAR(255),
    external_url TEXT,
    sync_status VARCHAR(50)
);

-- Add columns if they don't exist (for existing databases)
DO $$
BEGIN
    BEGIN
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE;
    EXCEPTION WHEN OTHERS THEN
        -- Column might already exist
    END;
    
    BEGIN
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS due_date TIMESTAMP WITH TIME ZONE;
    EXCEPTION WHEN OTHERS THEN
        -- Column might already exist
    END;
    
    BEGIN
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS order_num INTEGER DEFAULT 0;
    EXCEPTION WHEN OTHERS THEN
        -- Column might already exist
    END;
    
    BEGIN
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS project_id VARCHAR(255);
    EXCEPTION WHEN OTHERS THEN
        -- Column might already exist
    END;
    
    BEGIN
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS tags TEXT;
    EXCEPTION WHEN OTHERS THEN
        -- Column might already exist
    END;
    
    BEGIN
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);
    EXCEPTION WHEN OTHERS THEN
        -- Column might already exist
    END;
    
    BEGIN
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS external_url TEXT;
    EXCEPTION WHEN OTHERS THEN
        -- Column might already exist
    END;
    
    BEGIN
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50);
    EXCEPTION WHEN OTHERS THEN
        -- Column might already exist
    END;
END $$;

-- Team members table
CREATE TABLE IF NOT EXISTS members (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    position VARCHAR(50) NOT NULL,
    age INTEGER,
    sex VARCHAR(10),
    profile TEXT,
    leader_id VARCHAR(255),
    profile_image_path VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Project membership table
CREATE TABLE IF NOT EXISTS project_memberships (
    project_id VARCHAR(255) NOT NULL,
    member_id VARCHAR(255) NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (project_id, member_id)
);

-- Task file associations
CREATE TABLE IF NOT EXISTS file_associations (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(task_id, file_path)
);

-- Task relationships
CREATE TABLE IF NOT EXISTS task_relationships (
    id SERIAL PRIMARY KEY,
    parent_id VARCHAR(255) NOT NULL,
    child_id VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task log entries
CREATE TABLE IF NOT EXISTS log_entries (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255),
    message TEXT NOT NULL,
    entry_type VARCHAR(50) NOT NULL,
    level VARCHAR(20) DEFAULT 'INFO',
    "user" VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Project settings table
CREATE TABLE IF NOT EXISTS project_settings (
    project_id VARCHAR(255) PRIMARY KEY,
    strict_file_ref BOOLEAN DEFAULT FALSE,
    strict_log_entry BOOLEAN DEFAULT FALSE,
    strict_doc_read BOOLEAN DEFAULT FALSE,
    monitor_enabled BOOLEAN DEFAULT TRUE,
    monitor_path TEXT,
    monitor_extensions TEXT,
    monitor_interval INTEGER DEFAULT 60,
    project_root TEXT,
    github_enabled BOOLEAN DEFAULT FALSE,
    github_repo VARCHAR(255),
    work_started_file_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assignee);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_file_associations_task_id ON file_associations(task_id);
CREATE INDEX IF NOT EXISTS idx_task_relationships_parent ON task_relationships(parent_id);
CREATE INDEX IF NOT EXISTS idx_task_relationships_child ON task_relationships(child_id);
CREATE INDEX IF NOT EXISTS idx_log_entries_task_id ON log_entries(task_id);
CREATE INDEX IF NOT EXISTS idx_members_leader_id ON members(leader_id);
"""

def test_connection():
    """Test the database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS
        )
        conn.close()
        return True
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

def create_database():
    """Create the TracLine database if it doesn't exist."""
    try:
        # Display connection info
        print(f"Connecting to PostgreSQL server...")
        print(f"  Host: {DB_HOST}")
        print(f"  Port: {DB_PORT}")
        print(f"  User: {DB_USER}")
        print(f"  Database: {DB_NAME}")
        print()
        
        # Test connection first
        if not test_connection():
            print("Failed to connect to PostgreSQL server.")
            print("Please ensure PostgreSQL is running and the connection settings are correct.")
            return False
        
        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        exists = cursor.fetchone()
        
        # Always drop and recreate for clean installations
        if exists and os.getenv('TRACLINE_CLEAN_INSTALL', '').lower() == 'true':
            print(f"Database '{DB_NAME}' exists. Clean install requested.")
            print(f"Dropping and recreating database...")
            
            # Terminate ALL existing connections to ensure clean drop
            cursor.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{DB_NAME}'
                AND pid <> pg_backend_pid()
            """)
            
            # Wait a moment for connections to close
            import time
            time.sleep(1)
            
            # Drop the database
            try:
                cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
                print(f"Database '{DB_NAME}' dropped.")
            except Exception as e:
                print(f"Warning: Could not drop database: {e}")
            
            # Create fresh database
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database '{DB_NAME}' created fresh.")
            
        elif not exists:
            print(f"Creating database '{DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database '{DB_NAME}' created.")
        else:
            print(f"Database '{DB_NAME}' already exists.")
        
        cursor.close()
        conn.close()
        
        # Connect to the TracLine database and initialize schema
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Execute initialization SQL
        print("Initializing database schema...")
        cursor.execute(INIT_SQL)
        
        cursor.close()
        conn.close()
        print("Database schema initialized.")
        
        return True
    
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False

def main():
    """Main function to set up the PostgreSQL database."""
    print("TracLine PostgreSQL Setup")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("Using configuration from .env file")
    else:
        print("No .env file found, using default values")
        print("Tip: Copy .env.example to .env for custom configuration")
    print()
    
    success = create_database()
    
    if success:
        print("\n✅ PostgreSQL setup completed successfully!")
        print("\nNext steps:")
        print("1. Ensure docker-compose is running: docker-compose up -d")
        print("2. Verify tracline.yaml has correct PostgreSQL settings")
        print("3. Start the web interface: cd web && python run_app.py")
        print("4. Access TracLine at http://localhost:8000")
    else:
        print("\n❌ PostgreSQL setup failed. See error messages above.")
        print("\nTroubleshooting tips:")
        print("1. Check if PostgreSQL is running: docker ps")
        print("2. Verify environment variables in .env file")
        print("3. Check PostgreSQL logs: docker-compose logs postgres")
        sys.exit(1)

if __name__ == "__main__":
    main()