"""File change event handler for TracLine."""

import os
from pathlib import Path
from datetime import datetime
from watchdog.events import FileSystemEventHandler
from watchdog.events import EVENT_TYPE_CREATED, EVENT_TYPE_MODIFIED, EVENT_TYPE_DELETED, EVENT_TYPE_MOVED
from ..core.config import Config
from ..db.factory import DatabaseFactory
from ..models.file_association import FileAssociation
import logging

logger = logging.getLogger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """Handle file system events and update TracLine database."""
    
    def __init__(self, project_id, db_config, extensions=None):
        super().__init__()
        self.project_id = project_id
        self.db_config = db_config
        self.extensions = extensions or ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs']
        self.db = None
        self._connect_db()
        
    def _connect_db(self):
        """Connect to database."""
        try:
            self.db = DatabaseFactory.create(self.db_config)
            self.db.connect()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            
    def _should_track_file(self, path):
        """Check if file should be tracked based on extension."""
        if not self.extensions:
            return True
        
        file_ext = Path(path).suffix.lower()
        return file_ext in self.extensions
        
    def _log_file_access(self, file_path, access_type, task_id=None):
        """Log file access to database."""
        try:
            if self.db is None:
                self._connect_db()
                
            if self.db_config.type == "postgresql":
                query = """
                INSERT INTO file_access_log (file_path, access_type, task_id, project_id, timestamp)
                VALUES (%s, %s, %s, %s, %s)
                """
                params = [file_path, access_type, task_id, self.project_id, datetime.now()]
            else:
                query = """
                INSERT INTO file_access_log (file_path, access_type, task_id, project_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """
                params = [file_path, access_type, task_id, self.project_id, datetime.now()]
                
            self.db.execute_query(query, params)
            self.db.conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to log file access: {e}")
            
    def _update_reference_count(self, file_path):
        """Update reference count for a file."""
        try:
            if self.db is None:
                self._connect_db()
                
            # Get current reference count
            if self.db_config.type == "postgresql":
                query = """
                SELECT COUNT(DISTINCT task_id) as count
                FROM file_associations
                WHERE file_path = %s
                """
                params = [file_path]
            else:
                query = """
                SELECT COUNT(DISTINCT task_id) as count
                FROM file_associations
                WHERE file_path = ?
                """
                params = [file_path]
                
            cursor = self.db.execute_query(query, params)
            result = cursor.fetchone()
            count = result[0] if result else 0
            
            # Update all associations with new count
            if self.db_config.type == "postgresql":
                update_query = """
                UPDATE file_associations
                SET reference_count = %s
                WHERE file_path = %s
                """
                update_params = [count, file_path]
            else:
                update_query = """
                UPDATE file_associations
                SET reference_count = ?
                WHERE file_path = ?
                """
                update_params = [count, file_path]
                
            self.db.execute_query(update_query, update_params)
            self.db.conn.commit()
            
            logger.info(f"Updated reference count for {file_path}: {count}")
            
        except Exception as e:
            logger.error(f"Failed to update reference count: {e}")
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
            
        if not self._should_track_file(event.src_path):
            return
            
        logger.info(f"File created: {event.src_path}")
        self._log_file_access(event.src_path, 'create')
        
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        if not self._should_track_file(event.src_path):
            return
            
        logger.info(f"File modified: {event.src_path}")
        self._log_file_access(event.src_path, 'edit')
        self._update_reference_count(event.src_path)
        
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
            
        if not self._should_track_file(event.src_path):
            return
            
        logger.info(f"File deleted: {event.src_path}")
        self._log_file_access(event.src_path, 'delete')
        
        # Remove file associations for deleted files
        try:
            if self.db_config.type == "postgresql":
                query = "UPDATE file_associations SET reference_count = 0 WHERE file_path = %s"
                params = [event.src_path]
            else:
                query = "UPDATE file_associations SET reference_count = 0 WHERE file_path = ?"
                params = [event.src_path]
                
            self.db.execute_query(query, params)
            self.db.conn.commit()
        except Exception as e:
            logger.error(f"Failed to update associations for deleted file: {e}")
        
    def on_moved(self, event):
        """Handle file move/rename events."""
        if event.is_directory:
            return
            
        if not self._should_track_file(event.dest_path):
            return
            
        logger.info(f"File moved: {event.src_path} -> {event.dest_path}")
        self._log_file_access(event.src_path, 'rename')
        
        # Update file associations with new path
        try:
            if self.db_config.type == "postgresql":
                query = "UPDATE file_associations SET file_path = %s WHERE file_path = %s"
                params = [event.dest_path, event.src_path]
            else:
                query = "UPDATE file_associations SET file_path = ? WHERE file_path = ?"
                params = [event.dest_path, event.src_path]
                
            self.db.execute_query(query, params)
            self.db.conn.commit()
            
            # Update reference count for new path
            self._update_reference_count(event.dest_path)
            
        except Exception as e:
            logger.error(f"Failed to update associations for moved file: {e}")
            
    def __del__(self):
        """Clean up database connection."""
        if self.db:
            try:
                self.db.disconnect()
            except:
                pass