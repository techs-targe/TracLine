#!/usr/bin/env python3
"""
TracLine Cleanup Script
Removes test data, test files, and temporary files.
"""

import os
import sys
import argparse
import shutil
import logging
from pathlib import Path
import sqlite3
import psycopg2
from datetime import datetime

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Test files to delete
TEST_FILES = [
    "test_all_commands.sh",
    "test_all_working.py",
    "test_context_manager.py",
    "test_create.py",
    "test.db",
    "test_debug_path.py",
    "test_direct.py",
    "test_enum.py",
    "test_factory.py",
    "test_file.txt",
    "test_full_commands.py",
    "test_new_instance.py",
    "test_next_debug.py",
    "test_simple_command.py",
    "test_simple.py",
    "test_single.py",
    "test_tracline.py",
    "test_v1_compatibility.py",
    "test_with_statement.py",
    "test_workflow_command.py",
    "test_basic_postgres.py",
    "test_simple_postgres.py",
    "test_tracline_features.py",
    "test_web_app.py",
    "web_app.log",
    "test_results.md",
]

# Directories to delete
TEST_DIRECTORIES = [
    "test-files",
    "test_team",
]

# SQL queries for deleting PostgreSQL test data
POSTGRES_CLEANUP_QUERIES = [
    # Queries to delete sample data
    "DELETE FROM task_files WHERE task_id LIKE 'test-%' OR task_id LIKE 'task-%' OR task_id LIKE 'direct-test-%'",
    "DELETE FROM task_relations WHERE parent_id LIKE 'test-%' OR child_id LIKE 'test-%' OR parent_id LIKE 'task-%' OR child_id LIKE 'task-%'",
    "DELETE FROM tasks WHERE id LIKE 'test-%' OR id LIKE 'task-%' OR id LIKE 'direct-test-%'",
    "DELETE FROM project_memberships WHERE project_id LIKE 'test-%' OR member_id LIKE 'test-%' OR project_id LIKE 'direct-test-%'",
    "DELETE FROM members WHERE id LIKE 'test-%' OR id LIKE 'member-%' OR id LIKE 'tech-leader'",
    "DELETE FROM projects WHERE id LIKE 'test-%' OR id LIKE 'direct-test-%' OR id LIKE 'comm-app-dev'",
    # Refresh indexes
    "REINDEX TABLE tasks",
    "REINDEX TABLE members",
    "REINDEX TABLE projects",
]

def cleanup_test_files(force=False):
    """Delete test files"""
    base_dir = Path(__file__).resolve().parent
    
    # Verify parent directory (safety measure)
    if not (base_dir / "tracline").exists():
        logger.error("tracline directory not found. Please run from the correct directory.")
        return False
    
    # Process files to delete
    removed_files = 0
    for file_name in TEST_FILES:
        file_path = base_dir / file_name
        if file_path.exists():
            if force:
                try:
                    file_path.unlink()
                    logger.info(f"File deleted: {file_path}")
                    removed_files += 1
                except Exception as e:
                    logger.error(f"File deletion error {file_path}: {e}")
            else:
                logger.info(f"File to delete: {file_path} (use --force option to delete)")
                removed_files += 1
    
    # Process directories to delete
    removed_dirs = 0
    for dir_name in TEST_DIRECTORIES:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            if force:
                try:
                    shutil.rmtree(dir_path)
                    logger.info(f"Directory deleted: {dir_path}")
                    removed_dirs += 1
                except Exception as e:
                    logger.error(f"Directory deletion error {dir_path}: {e}")
            else:
                logger.info(f"Directory to delete: {dir_path} (use --force option to delete)")
                removed_dirs += 1
    
    # Delete *.pyc files and __pycache__ directories
    if force:
        # Delete .pyc files
        for pyc_file in base_dir.glob("**/*.pyc"):
            try:
                pyc_file.unlink()
                logger.debug(f"File deleted: {pyc_file}")
                removed_files += 1
            except Exception as e:
                logger.error(f"File deletion error {pyc_file}: {e}")
        
        # Delete __pycache__ directories
        for pycache_dir in base_dir.glob("**/__pycache__"):
            try:
                shutil.rmtree(pycache_dir)
                logger.debug(f"Directory deleted: {pycache_dir}")
                removed_dirs += 1
            except Exception as e:
                logger.error(f"Directory deletion error {pycache_dir}: {e}")
    
    logger.info(f"Files to delete: {removed_files}")
    logger.info(f"Directories to delete: {removed_dirs}")
    
    return True

def cleanup_sqlite_data(force=False):
    """Delete test data from SQLite database"""
    home = Path.home()
    db_path = home / ".tracline" / "tracline.db"
    
    if not db_path.exists():
        logger.warning(f"SQLite database not found: {db_path}")
        return False
    
    try:
        logger.info(f"Connecting to SQLite database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Delete test data
        if force:
            cursor.execute("DELETE FROM task_files WHERE task_id LIKE 'test-%' OR task_id LIKE 'task-%'")
            cursor.execute("DELETE FROM task_relations WHERE parent_id LIKE 'test-%' OR child_id LIKE 'test-%' OR parent_id LIKE 'task-%' OR child_id LIKE 'task-%'")
            cursor.execute("DELETE FROM tasks WHERE id LIKE 'test-%' OR id LIKE 'task-%'")
            cursor.execute("DELETE FROM members WHERE id LIKE 'test-%' OR id LIKE 'member-%'")
            cursor.execute("DELETE FROM projects WHERE id LIKE 'test-%' OR id LIKE 'direct-test-%'")
            conn.commit()
            logger.info(f"Test data deleted from SQLite database")
        else:
            # Check the number of data items to delete
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE id LIKE 'test-%' OR id LIKE 'task-%'")
            task_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM members WHERE id LIKE 'test-%' OR id LIKE 'member-%'")
            member_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM projects WHERE id LIKE 'test-%' OR id LIKE 'direct-test-%'")
            project_count = cursor.fetchone()[0]
            
            logger.info(f"Test data to delete: {task_count} tasks, {member_count} members, {project_count} projects (use --force option to delete)")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"SQLite database operation error: {e}")
        return False

def cleanup_postgresql_data(force=False, host="localhost", port=5432, dbname="tracline", user="postgres", password="postgres"):
    """Delete test data from PostgreSQL database"""
    try:
        logger.info(f"Connecting to PostgreSQL database: {host}:{port}/{dbname}")
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        if force:
            # Delete test data
            for query in POSTGRES_CLEANUP_QUERIES:
                try:
                    cursor.execute(query)
                    affected = cursor.rowcount
                    logger.debug(f"Executed: {query} - {affected} rows affected")
                except Exception as e:
                    logger.error(f"Query execution error: {query} - {e}")
                    conn.rollback()
            
            conn.commit()
            logger.info("Test data deleted from PostgreSQL database")
        else:
            # Check the number of data items to delete
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE id LIKE 'test-%' OR id LIKE 'task-%' OR id LIKE 'direct-test-%'")
            task_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM members WHERE id LIKE 'test-%' OR id LIKE 'member-%' OR id LIKE 'tech-leader'")
            member_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM projects WHERE id LIKE 'test-%' OR id LIKE 'direct-test-%' OR id LIKE 'comm-app-dev'")
            project_count = cursor.fetchone()[0]
            
            logger.info(f"Test data to delete: {task_count} tasks, {member_count} members, {project_count} projects (use --force option to delete)")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"PostgreSQL database operation error: {e}")
        return False

def create_backup(backup_dir=None):
    """Create a backup of the current state"""
    if not backup_dir:
        backup_dir = Path.home() / f"tracline_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    else:
        backup_dir = Path(backup_dir)
    
    backup_dir.mkdir(exist_ok=True, parents=True)
    
    # Backup project files
    base_dir = Path(__file__).resolve().parent
    backup_project_dir = backup_dir / "project"
    backup_project_dir.mkdir(exist_ok=True)
    
    logger.info(f"Creating project backup: {backup_project_dir}")
    
    # Copy core files (excluding test files)
    for item in base_dir.glob("**/*"):
        if item.is_file():
            # Exclude test files
            if item.name not in TEST_FILES and not any(test_dir in str(item) for test_dir in TEST_DIRECTORIES):
                # Exclude .pyc files and __pycache__ directories
                if not item.name.endswith(".pyc") and "__pycache__" not in str(item):
                    # Maintain relative path from backup directory
                    rel_path = item.relative_to(base_dir)
                    backup_path = backup_project_dir / rel_path
                    backup_path.parent.mkdir(exist_ok=True, parents=True)
                    shutil.copy2(item, backup_path)
    
    # Backup SQLite database
    home = Path.home()
    sqlite_db = home / ".tracline" / "tracline.db"
    if sqlite_db.exists():
        backup_db_dir = backup_dir / "data"
        backup_db_dir.mkdir(exist_ok=True)
        backup_sqlite = backup_db_dir / "tracline.db"
        shutil.copy2(sqlite_db, backup_sqlite)
        logger.info(f"Created SQLite database backup: {backup_sqlite}")
    
    logger.info(f"Backup completed: {backup_dir}")
    return backup_dir

def main():
    parser = argparse.ArgumentParser(description="TracLine test data and test file cleanup")
    parser.add_argument("--force", action="store_true", help="Actually perform deletion (without this flag, only displays what would be deleted)")
    parser.add_argument("--backup", action="store_true", help="Create backup before cleanup")
    parser.add_argument("--backup-dir", type=str, help="Specify backup directory")
    parser.add_argument("--skip-files", action="store_true", help="Skip test file cleanup")
    parser.add_argument("--skip-sqlite", action="store_true", help="Skip SQLite database cleanup")
    parser.add_argument("--skip-postgresql", action="store_true", help="Skip PostgreSQL database cleanup")
    parser.add_argument("--pg-host", type=str, default="localhost", help="PostgreSQL host")
    parser.add_argument("--pg-port", type=int, default=5432, help="PostgreSQL port")
    parser.add_argument("--pg-dbname", type=str, default="tracline", help="PostgreSQL database name")
    parser.add_argument("--pg-user", type=str, default="postgres", help="PostgreSQL user")
    parser.add_argument("--pg-password", type=str, default="postgres", help="PostgreSQL password")
    
    args = parser.parse_args()
    
    logger.info("TracLine Cleanup Tool")
    logger.info(f"Execution mode: {'Actual deletion' if args.force else 'Display only (use --force option to actually delete)'}")
    
    if args.backup:
        backup_dir = create_backup(args.backup_dir)
        logger.info(f"Created backup: {backup_dir}")
    
    if not args.skip_files:
        cleanup_test_files(args.force)
    
    if not args.skip_sqlite:
        cleanup_sqlite_data(args.force)
    
    if not args.skip_postgresql:
        cleanup_postgresql_data(
            args.force,
            args.pg_host,
            args.pg_port,
            args.pg_dbname,
            args.pg_user,
            args.pg_password
        )
    
    if args.force:
        logger.info("Cleanup completed")
    else:
        logger.info("Use the --force option to actually perform the cleanup")

if __name__ == "__main__":
    main()