"""PostgreSQL database implementation"""
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json

from tracline.models.task import Task
from tracline.models.relationship import TaskRelationship, RelationshipType
from tracline.models.file_association import FileAssociation
from tracline.models.log_entry import LogEntry
from tracline.models.member import Member, MemberRole, MemberPosition
from tracline.models.project import Project, ProjectMembership
from tracline.core.config import DatabaseConfig
from tracline.db.interface import DatabaseInterface

logger = logging.getLogger(__name__)

class PostgreSQLDatabase(DatabaseInterface):
    """PostgreSQL implementation of database interface"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.conn = None
        self.cursor = None
        self.in_transaction = False
        self.db_type = 'postgresql'  # For database type detection
        self._schema_initialized = False
        
        # Get connection parameters from config
        self.host = getattr(config, 'host', 'localhost')
        self.port = getattr(config, 'port', 5432)
        self.database = getattr(config, 'name', getattr(config, 'database', 'tracline'))
        self.user = getattr(config, 'user', 'postgres')
        self.password = getattr(config, 'password', '')
        
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            # Reset transaction state
            self.in_transaction = False
            
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor
            )
            self.cursor = self.conn.cursor()
            
            # Defer schema initialization to avoid transaction conflicts
            # Schema will be initialized on first use if needed
            logger.info(f"Connected to PostgreSQL database at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
            
    def reset_connection(self):
        """Reset connection to recover from aborted transactions"""
        try:
            if self.conn:
                self.conn.rollback()
                self.in_transaction = False
        except Exception:
            # If rollback fails, reconnect completely
            self.disconnect()
            self.connect()
            
    def ensure_schema_initialized(self):
        """Ensure database schema is initialized outside of transactions"""
        # Always check columns even if schema was initialized
        # This handles cases where database exists but schema is outdated
        
        # Only initialize if we're not in a transaction
        if self.in_transaction:
            logger.warning("Cannot initialize schema during active transaction")
            return
            
        try:
            # Always run initialization to ensure schema is current
            self.initialize_schema()
            logger.debug("Schema initialization completed")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            # Don't raise - let operations try to continue
    
    def __enter__(self):
        """Context manager entry point with schema initialization for PostgreSQL."""
        self.connect()
        # Ensure schema is initialized for PostgreSQL
        self.ensure_schema_initialized()
        return self
            
    def disconnect(self):
        """Disconnect from PostgreSQL database"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Disconnected from PostgreSQL database")
    
    def execute_query(self, query: str, params: List[Any] = None) -> None:
        """Execute a query with parameters, handling DB-specific placeholders.
        
        PostgreSQL uses %s placeholders, this method converts ? to %s automatically.
        
        Args:
            query: SQL query with ? placeholders
            params: List of parameters to substitute for the placeholders
        """
        try:
            # PostgreSQL uses %s instead of ? for parameters
            # Convert the query from ? to %s notation
            postgres_query = query.replace("?", "%s")
            
            # Execute with parameters or without if None
            if params:
                self.cursor.execute(postgres_query, params)
            else:
                self.cursor.execute(postgres_query)
                
            return self.cursor
        except Exception as e:
            # If transaction is aborted, reset it
            if 'current transaction is aborted' in str(e):
                self.reset_connection()
                # Retry the query
                postgres_query = query.replace("?", "%s")
                if params:
                    self.cursor.execute(postgres_query, params)
                else:
                    self.cursor.execute(postgres_query)
                return self.cursor
            else:
                raise
    
    def initialize_schema(self):
        """Initialize database schema"""
        logger.info("PostgreSQL: Starting schema initialization...")
        
        # Tasks table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id VARCHAR(255) PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status VARCHAR(50) NOT NULL,
                assignee VARCHAR(100),
                tags TEXT,
                priority INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                due_date TIMESTAMP,
                order_num INTEGER DEFAULT 0,
                external_id VARCHAR(255),
                external_url TEXT,
                sync_status VARCHAR(50),
                project_id VARCHAR(100)
            )
        """)
        
        # Task relations table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_relations (
                id SERIAL PRIMARY KEY,
                parent_id VARCHAR(255) NOT NULL,
                child_id VARCHAR(255) NOT NULL,
                relationship_type VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                UNIQUE(parent_id, child_id),
                FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (child_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)
        
        # Task files table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_files (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(255) NOT NULL,
                file_path TEXT NOT NULL,
                file_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                UNIQUE(task_id, file_path)
            )
        """)
        
        # Log entries table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_entries (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level VARCHAR(20),
                entry_type VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                task_id VARCHAR(255),
                "user" VARCHAR(100),
                metadata JSONB,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
            )
        """)
        
        # Check if level column exists in log_entries table
        self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'log_entries' AND column_name = 'level'
        """)
        if not self.cursor.fetchone():
            logger.info("Adding missing level column to log_entries table")
            self.cursor.execute("ALTER TABLE log_entries ADD COLUMN level VARCHAR(20)")
            self.conn.commit()
        
        # Members table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                position VARCHAR(50) NOT NULL,
                age INTEGER,
                sex VARCHAR(10),
                profile TEXT,
                leader_id VARCHAR(100),
                profile_image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (leader_id) REFERENCES members(id) ON DELETE SET NULL
            )
        """)
        
        # Projects table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                owner_id VARCHAR(100),
                status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES members(id) ON DELETE SET NULL
            )
        """)
        
        # Project memberships table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_memberships (
                project_id VARCHAR(100) NOT NULL,
                member_id VARCHAR(100) NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (project_id, member_id),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """)
        
        # File associations table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_associations (
                id SERIAL PRIMARY KEY,
                task_id VARCHAR(255) NOT NULL,
                file_path TEXT NOT NULL,
                relative_path TEXT,
                file_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                last_modified TIMESTAMP,
                file_size BIGINT,
                reference_count INTEGER DEFAULT 1,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                UNIQUE(task_id, file_path)
            )
        """)
        
        # File access log table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_access_log (
                id SERIAL PRIMARY KEY,
                file_path TEXT NOT NULL,
                action VARCHAR(50) NOT NULL,
                task_id VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id VARCHAR(100),
                metadata JSONB
            )
        """)
        
        # Project settings table
        logger.info("PostgreSQL: Creating project_settings table with strict mode columns...")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_settings (
                project_id VARCHAR(100) PRIMARY KEY,
                github_enabled BOOLEAN DEFAULT false,
                github_repo TEXT,
                github_token TEXT,
                webhook_url TEXT,
                webhook_secret TEXT,
                monitor_enabled BOOLEAN DEFAULT false,
                monitor_path TEXT,
                monitor_interval INTEGER DEFAULT 60,
                monitor_extensions TEXT[],
                strict_doc_read BOOLEAN DEFAULT false,
                strict_file_ref BOOLEAN DEFAULT false,
                strict_log_entry BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)
        
        # Schema version table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY DEFAULT 1,
                version INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert initial schema version if not exists
        self.cursor.execute("""
            INSERT INTO schema_version (id, version)
            VALUES (1, 1)
            ON CONFLICT (id) DO NOTHING
        """)
        
        # Verify column existence and add if necessary
        self._ensure_columns_exist()
        
        # Create indexes - only attempt if the columns exist
        self._create_indices()
        
        self.conn.commit()
        logger.info("PostgreSQL: Schema initialization completed and committed")
        
    def _ensure_columns_exist(self):
        """Check if required columns exist in tables and add them if not"""
        # Verify and add columns if they don't exist
        try:
            # Call more comprehensive task column checker
            self._ensure_task_columns_exist()
            
            # --- Projects table columns ---
            # Check for status column in projects table
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'projects' AND column_name = 'status'
            """)
            if not self.cursor.fetchone():
                logger.info("Adding missing status column to projects table")
                self.cursor.execute("ALTER TABLE projects ADD COLUMN status VARCHAR(50) DEFAULT 'ACTIVE'")
                self.conn.commit()
            
            # --- Project settings table columns ---
            # Ensure strict mode columns exist
            self._ensure_project_settings_columns()
            
            # --- File associations table columns ---
            # Ensure file_type and other columns exist
            self._ensure_file_associations_columns()
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error checking or adding columns: {e}")
        
        # Always commit schema changes
        try:
            self.conn.commit()
            logger.info("Schema updates committed successfully")
        except Exception as e:
            logger.warning(f"Could not commit schema updates: {e}")
            
    def _ensure_task_columns_exist(self):
        """Ensure all Task model columns exist in the database"""
        try:
            # Common fields in the Task model
            task_columns = [
                ('project_id', 'VARCHAR(100)'),
                ('due_date', 'TIMESTAMP'),
                ('tags', 'TEXT'),
                ('external_id', 'VARCHAR(255)'),
                ('external_url', 'TEXT'),
                ('sync_status', 'VARCHAR(50)'),
                ('work_started_file_count', 'INTEGER')
            ]
            
            # Check for each column and add if missing
            for column_name, column_type in task_columns:
                self.cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'tasks' AND column_name = %s
                """, [column_name])
                
                if not self.cursor.fetchone():
                    logger.info(f"Adding missing {column_name} column to tasks table")
                    self.cursor.execute(f"ALTER TABLE tasks ADD COLUMN {column_name} {column_type}")
                    self.conn.commit()
                    
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error ensuring task columns: {e}")
    
    def _ensure_project_settings_columns(self):
        """Ensure project_settings table has all required columns including strict mode."""
        try:
            # Check if project_settings table exists
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'project_settings'
                )
            """)
            result = self.cursor.fetchone()
            if not result or not result.get('exists', False):
                logger.info("project_settings table does not exist, skipping column check")
                return
            
            # Define columns to ensure exist
            columns_to_ensure = [
                ('strict_doc_read', 'BOOLEAN DEFAULT false'),
                ('strict_file_ref', 'BOOLEAN DEFAULT false'),
                ('strict_log_entry', 'BOOLEAN DEFAULT false'),
                ('monitor_interval', 'INTEGER DEFAULT 60'),
                ('monitor_path', 'TEXT')
            ]
            
            # Check and add each column
            for column_name, column_definition in columns_to_ensure:
                self.cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'project_settings' AND column_name = %s
                """, [column_name])
                
                if not self.cursor.fetchone():
                    logger.info(f"Adding missing {column_name} column to project_settings table")
                    self.cursor.execute(f"ALTER TABLE project_settings ADD COLUMN {column_name} {column_definition}")
                    self.conn.commit()
                    
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error ensuring project_settings columns: {e}")
    
    def _ensure_file_associations_columns(self):
        """Ensure all required columns exist in file_associations table"""
        try:
            logger.info("Checking file_associations table columns...")
            
            # Define required columns with their definitions
            file_associations_columns = [
                ('file_type', 'VARCHAR(50)'),
                ('description', 'TEXT'),
                ('relative_path', 'TEXT'),
                ('created_by', 'VARCHAR(100)'),
                ('last_modified', 'TIMESTAMP'),
                ('file_size', 'BIGINT'),
                ('reference_count', 'INTEGER DEFAULT 1')
            ]
            
            # Check for each column and add if missing
            for column_name, column_definition in file_associations_columns:
                self.cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'file_associations' AND column_name = %s
                """, [column_name])
                
                if not self.cursor.fetchone():
                    logger.info(f"Adding missing {column_name} column to file_associations table")
                    try:
                        self.cursor.execute(f"ALTER TABLE file_associations ADD COLUMN IF NOT EXISTS {column_name} {column_definition}")
                        logger.info(f"Successfully added {column_name} column")
                    except Exception as col_error:
                        logger.error(f"Failed to add {column_name} column: {col_error}")
                        # Continue with other columns even if one fails
            
            # Update file_type for existing records if it was just added
            self.cursor.execute("""
                UPDATE file_associations 
                SET file_type = SUBSTRING(file_path FROM '\\.([^.]+)$')
                WHERE file_type IS NULL AND file_path LIKE '%.%'
            """)
            
            if self.cursor.rowcount > 0:
                self.conn.commit()
                logger.info(f"Updated {self.cursor.rowcount} records with file type based on extension")
                    
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error ensuring file_associations columns: {e}")
            # Don't re-raise - allow application to continue even if column addition fails
            
    def _create_indices(self):
        """Create indices for tables - checking column existence first"""
        # Get all columns in tasks table
        self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tasks'
        """)
        existing_task_columns = {row['column_name'] for row in self.cursor.fetchall()}
        
        # Get all columns in projects table
        self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'projects'
        """)
        existing_project_columns = {row['column_name'] for row in self.cursor.fetchall()}
        
        # Prepare index creation information with column dependencies
        indices = [
            # Only create indices for columns we've verified exist
            ("idx_tasks_status", "tasks(status)", "status" in existing_task_columns),
            ("idx_tasks_assignee", "tasks(assignee)", "assignee" in existing_task_columns),
            ("idx_tasks_due_date", "tasks(due_date)", "due_date" in existing_task_columns),
            ("idx_tasks_project_id", "tasks(project_id)", "project_id" in existing_task_columns),
            ("idx_members_leader", "members(leader_id)", True),  # Always exists from schema creation
            ("idx_project_status", "projects(status)", "status" in existing_project_columns),
            ("idx_log_entries_task", "log_entries(task_id)", True),  # Always exists from schema creation
            ("idx_log_entries_type", "log_entries(entry_type)", True)  # Always exists from schema creation
        ]
        
        # Create each index only if its dependent column exists
        for idx_name, idx_def, column_exists in indices:
            if not column_exists:
                logger.info(f"Skipping index {idx_name} because required column doesn't exist")
                continue
                
            try:
                self.cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
                self.conn.commit()
                logger.debug(f"Created or verified index: {idx_name}")
            except Exception as e:
                self.conn.rollback()
                logger.warning(f"Could not create index {idx_name}: {str(e)}")
        
    # Task operations
    def create_task(self, task: Task) -> Task:
        """Create a new task"""
        tags_str = ','.join(task.tags) if task.tags else None
        
        self.cursor.execute("""
            INSERT INTO tasks (id, title, description, status, assignee, tags, priority, created_at, due_date, external_id, external_url, sync_status, project_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING created_at, updated_at
        """, (task.id, task.title, task.description, task.status, task.assignee, tags_str, 
              task.priority, task.created_at or datetime.now(), task.due_date, task.external_id, task.external_url, task.sync_status, task.project_id))
        
        result = self.cursor.fetchone()
        if not self.in_transaction:
            self.conn.commit()
        
        task.created_at = result['created_at']
        task.updated_at = result['updated_at']
        
        return task
        
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        try:
            # Ensure schema exists before querying
            self.ensure_schema_initialized()
            
            self.cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
                
            return self._row_to_task(row)
        except Exception as e:
            logger.error(f"Error in get_task: {e}")
            # Reset connection if transaction is aborted
            if "current transaction is aborted" in str(e):
                self.reset_connection()
                # Try once more after reset
                try:
                    self.ensure_schema_initialized()
                    self.cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
                    row = self.cursor.fetchone()
                    return self._row_to_task(row) if row else None
                except Exception:
                    pass
            return None
        
    def update_task(self, task: Task) -> Task:
        """Update an existing task"""
        # Ensure tags column exists before attempting to update it
        self._ensure_task_columns_exist()
        
        # Get all column names for tasks table to avoid errors with missing columns
        self.cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tasks'
        """)
        existing_columns = {row['column_name'] for row in self.cursor.fetchall()}
        
        # Build query dynamically based on existing columns
        update_fields = []
        update_values = []
        
        # Add fields that exist in the database
        if 'title' in existing_columns:
            update_fields.append("title = %s")
            update_values.append(task.title)
            
        if 'description' in existing_columns:
            update_fields.append("description = %s")
            update_values.append(task.description)
            
        if 'status' in existing_columns:
            update_fields.append("status = %s")
            update_values.append(task.status)
            
        if 'assignee' in existing_columns:
            update_fields.append("assignee = %s")
            update_values.append(task.assignee)
            
        if 'tags' in existing_columns:
            update_fields.append("tags = %s")
            tags_str = ','.join(task.tags) if task.tags else None
            update_values.append(tags_str)
            
        if 'priority' in existing_columns:
            update_fields.append("priority = %s")
            update_values.append(task.priority)
            
        if 'due_date' in existing_columns:
            update_fields.append("due_date = %s")
            update_values.append(task.due_date)
            
        update_fields.append("updated_at = CURRENT_TIMESTAMP")  # Always include updated_at
        
        if 'completed_at' in existing_columns:
            update_fields.append("completed_at = %s")
            update_values.append(task.completed_at)
            
        if 'external_id' in existing_columns:
            update_fields.append("external_id = %s")
            update_values.append(task.external_id)
            
        if 'external_url' in existing_columns:
            update_fields.append("external_url = %s")
            update_values.append(task.external_url)
            
        if 'sync_status' in existing_columns:
            update_fields.append("sync_status = %s")
            update_values.append(task.sync_status)
            
        if 'project_id' in existing_columns:
            update_fields.append("project_id = %s")
            update_values.append(task.project_id)
        
        if 'work_started_file_count' in existing_columns:
            update_fields.append("work_started_file_count = %s")
            update_values.append(task.work_started_file_count)
        
        # Add task ID for WHERE clause
        update_values.append(task.id)
        
        # Build and execute the dynamic query
        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = %s RETURNING updated_at"
        
        try:
            self.cursor.execute(query, update_values)
            
            result = self.cursor.fetchone()
            if not self.in_transaction:
                self.conn.commit()
            
            task.updated_at = result['updated_at']
            return task
            
        except Exception as e:
            if not self.in_transaction:
                self.conn.rollback()
            logger.error(f"Error updating task {task.id}: {e}")
            raise
        
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        self.cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        if not self.in_transaction:
            self.conn.commit()
        return self.cursor.rowcount > 0
        
    def list_tasks(self, filters: Dict[str, Any] = None, 
                  sort_by: str = "created_at",  # Changed default sort to created_at
                  limit: Optional[int] = None) -> List[Task]:
        """List tasks with optional filters"""
        try:
            # Safe query construction
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []
            
            if filters:
                if 'status' in filters and filters['status']:
                    query += " AND status = %s"
                    params.append(filters['status'])
                    
                if 'exclude_status' in filters and filters['exclude_status']:
                    query += " AND status != %s"
                    params.append(filters['exclude_status'])
                    
                if 'assignee' in filters and filters['assignee']:
                    query += " AND assignee = %s"
                    params.append(filters['assignee'])
                    
                if 'project_id' in filters and filters['project_id']:
                    query += " AND project_id = %s"
                    params.append(filters['project_id'])
                elif 'project' in filters and filters['project']:
                    query += " AND project_id = %s"
                    params.append(filters['project'])
                    
                if 'priority' in filters and filters['priority']:
                    query += " AND priority = %s"
                    params.append(filters['priority'])
                    
                if 'tags' in filters and filters['tags']:
                    # Verify tags column exists first
                    self.cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'tasks' AND column_name = 'tags'
                    """)
                    if self.cursor.fetchone():
                        # Search for any of the provided tags
                        tag_conditions = []
                        for tag in filters['tags']:
                            tag_conditions.append("tags LIKE %s")
                            params.append(f"%{tag}%")
                        query += f" AND ({' OR '.join(tag_conditions)})"
            
            # Apply safe sorting
            # Verify columns exist first
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks'
            """)
            existing_columns = {row['column_name'] for row in self.cursor.fetchall()}
            
            # Default safe columns
            safe_columns = ["id", "title", "status", "assignee", "priority"]
            # Add other columns if they exist in the table
            safe_columns.extend(col for col in ["created_at", "updated_at", "order_num"] if col in existing_columns)
            
            if sort_by in safe_columns:
                query += f" ORDER BY {sort_by}"
            else:
                # Use safe default
                logger.warning(f"Using safe default sort instead of: {sort_by}")
                if "created_at" in existing_columns:
                    query += " ORDER BY created_at DESC"
                else:
                    query += " ORDER BY id"
            
            # Apply limit
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            # Convert rows
            tasks = []
            for row in rows:
                try:
                    task = self._row_to_task(row)
                    tasks.append(task)
                except Exception as e:
                    logger.warning(f"Error converting task row: {e}")
                    continue
                    
            return tasks
        
        except Exception as e:
            logger.error(f"Error in list_tasks: {str(e)}")
            # Return empty list on error
            return []
    
    def get_next_task(self, assignee: Optional[str] = None,
                     project_id: Optional[str] = None,
                     exclude_states: List[str] = None) -> Optional[Task]:
        """Get the next task in the queue"""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if assignee:
            query += " AND assignee = %s"
            params.append(assignee)
            
        if project_id:
            query += " AND project_id = %s"
            params.append(project_id)
        
        if exclude_states:
            placeholders = ', '.join(['%s'] * len(exclude_states))
            query += f" AND status NOT IN ({placeholders})"
            params.extend(exclude_states)
        
        query += " ORDER BY priority DESC, created_at ASC LIMIT 1"
        
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        return self._row_to_task(row)
    
    def reorder_task(self, task_id: str, new_position: int) -> bool:
        """Reorder a task to a new position"""
        # First, get the current task information
        self.cursor.execute("SELECT order_num FROM tasks WHERE id = %s", (task_id,))
        current_task = self.cursor.fetchone()
        
        if not current_task:
            return False
        
        # Update the position of the task
        self.cursor.execute("""
            UPDATE tasks 
            SET order_num = %s, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_position, task_id))
        
        # Update order of other tasks
        if new_position > current_task['order_num']:
            # Moving down, shift tasks in between up
            self.cursor.execute("""
                UPDATE tasks
                SET order_num = order_num - 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_num > %s AND order_num <= %s AND id != %s
            """, (current_task['order_num'], new_position, task_id))
        else:
            # Moving up, shift tasks in between down
            self.cursor.execute("""
                UPDATE tasks
                SET order_num = order_num + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_num >= %s AND order_num < %s AND id != %s
            """, (new_position, current_task['order_num'], task_id))
        
        if not self.in_transaction:
            self.conn.commit()
        
        return True
        
    # Relationship operations
    def create_relationship(self, relationship: TaskRelationship) -> TaskRelationship:
        """Create a task relationship"""
        try:
            self.cursor.execute("""
                INSERT INTO task_relations (parent_id, child_id, relationship_type, created_by)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at
            """, (relationship.parent_id, relationship.child_id, relationship.relationship_type, relationship.created_by))
            
            result = self.cursor.fetchone()
            if not self.in_transaction:
                self.conn.commit()
            
            relationship.id = result['id']
            relationship.created_at = result['created_at']
            
            return relationship
        except psycopg2.IntegrityError:
            if not self.in_transaction:
                self.conn.rollback()
            raise ValueError("Relationship already exists or invalid task IDs")
    
    def get_relationships(self, task_id: str = None, relationship_type: str = None) -> List[TaskRelationship]:
        """Get task relationships"""
        query = "SELECT * FROM task_relations WHERE 1=1"
        params = []
        
        if task_id:
            query += " AND (parent_id = %s OR child_id = %s)"
            params.extend([task_id, task_id])
        
        if relationship_type:
            query += " AND relationship_type = %s"
            params.append(relationship_type)
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        return [TaskRelationship(
            id=row['id'],
            parent_id=row['parent_id'],
            child_id=row['child_id'],
            relationship_type=row['relationship_type'],
            created_at=row['created_at'],
            created_by=row['created_by']
        ) for row in rows]
    
    def delete_relationship(self, relationship_id: int) -> bool:
        """Delete a task relationship"""
        self.cursor.execute("DELETE FROM task_relations WHERE id = %s", (relationship_id,))
        if not self.in_transaction:
            self.conn.commit()
        return self.cursor.rowcount > 0
    
    # File association operations
    def add_file_association(self, association: FileAssociation) -> FileAssociation:
        """Add a file association"""
        try:
            self.cursor.execute("""
                INSERT INTO task_files (task_id, file_path, file_type)
                VALUES (%s, %s, %s)
                RETURNING id, created_at
            """, (association.task_id, association.file_path, association.file_type))
            
            result = self.cursor.fetchone()
            if not self.in_transaction:
                self.conn.commit()
            
            association.id = result['id']
            association.created_at = result['created_at']
            
            return association
        except psycopg2.IntegrityError:
            if not self.in_transaction:
                self.conn.rollback()
            raise ValueError("File association already exists or invalid task ID")
    
    def get_file_associations(self, task_id: str) -> List[FileAssociation]:
        """Get file associations for a task"""
        self.cursor.execute("SELECT * FROM task_files WHERE task_id = %s", (task_id,))
        rows = self.cursor.fetchall()
        
        return [FileAssociation(
            id=row['id'],
            task_id=row['task_id'],
            file_path=row['file_path'],
            file_type=row['file_type'],
            created_at=row['created_at']
        ) for row in rows]
    
    def get_all_file_associations(self) -> List[FileAssociation]:
        """Get all file associations in the system"""
        self.cursor.execute("SELECT * FROM task_files")
        rows = self.cursor.fetchall()
        
        return [FileAssociation(
            id=row['id'],
            task_id=row['task_id'],
            file_path=row['file_path'],
            file_type=row['file_type'],
            created_at=row['created_at']
        ) for row in rows]
    
    def remove_file_association(self, association_id: int) -> bool:
        """Remove a file association"""
        self.cursor.execute("DELETE FROM task_files WHERE id = %s", (association_id,))
        if not self.in_transaction:
            self.conn.commit()
        return self.cursor.rowcount > 0
    
    # Log operations
    def add_log_entry(self, entry: LogEntry) -> LogEntry:
        """Add a log entry"""
        # Check and ensure log entries columns exist
        self._ensure_log_entries_columns()
        
        # Sanitize metadata to handle non-JSON-serializable types
        sanitized_metadata = self._sanitize_json(entry.metadata) if entry.metadata else None
        metadata_json = json.dumps(sanitized_metadata) if sanitized_metadata else None
        
        # Ensure level and entry_type are string values
        level_val = entry.level.value if hasattr(entry.level, 'value') else entry.level
        entry_type_val = entry.entry_type.value if hasattr(entry.entry_type, 'value') else entry.entry_type
        
        try:
            # Get column information
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'log_entries'
            """)
            columns = {row['column_name'] for row in self.cursor.fetchall()}
            
            # Check which columns exist and build a dynamic query
            insert_columns = []
            insert_values = []
            
            # Time column (different names in different schema versions)
            if 'timestamp' in columns:
                insert_columns.append('timestamp')
                insert_values.append(entry.timestamp)
            elif 'created_at' in columns:
                insert_columns.append('created_at')
                insert_values.append(entry.timestamp)
            else:
                # Neither exists - shouldn't happen but add timestamp as a fallback
                insert_columns.append('timestamp')
                insert_values.append(entry.timestamp)
            
            # Optional columns - only include if they exist
            if 'level' in columns:
                insert_columns.append('level')
                insert_values.append(level_val)
                
            # Required columns
            insert_columns.append('entry_type')
            insert_values.append(entry_type_val)
            
            insert_columns.append('message')
            insert_values.append(entry.message)
            
            # Optional columns
            if entry.task_id:
                insert_columns.append('task_id')
                insert_values.append(entry.task_id)
                
            if entry.user and ('user' in columns or '"user"' in columns):
                insert_columns.append('"user"')
                insert_values.append(entry.user)
                
            if metadata_json:
                insert_columns.append('metadata')
                insert_values.append(metadata_json)
            
            # Build and execute the dynamic query
            placeholders = ', '.join(['%s'] * len(insert_values))
            query = f"INSERT INTO log_entries ({', '.join(insert_columns)}) VALUES ({placeholders}) RETURNING id"
            
            self.cursor.execute(query, insert_values)
            result = self.cursor.fetchone()
            
            if not self.in_transaction:
                self.conn.commit()
            
            entry.id = result['id']
            return entry
            
        except Exception as e:
            if not self.in_transaction:
                self.conn.rollback()
            logger.error(f"Error adding log entry: {e}")
            # Return the original entry even though it wasn't saved
            return entry
    
    def get_log_entries(self, task_id: str = None, limit: int = 100) -> List[LogEntry]:
        """Get log entries"""
        try:
            # First, determine the correct column name for timestamp
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'log_entries' AND column_name IN ('timestamp', 'created_at')
            """)
            columns = [row['column_name'] for row in self.cursor.fetchall()]
            
            # Decide which column name to use based on what exists
            timestamp_column = 'timestamp' if 'timestamp' in columns else 'created_at'
            
            # Build the query with the correct column name
            query = "SELECT * FROM log_entries WHERE 1=1"
            params = []
            
            if task_id:
                query += " AND task_id = %s"
                params.append(task_id)
            
            query += f" ORDER BY {timestamp_column} DESC LIMIT %s"
            params.append(limit)
            
            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            
            result = []
            for row in rows:
                # Handle different column names for timestamp
                timestamp_value = row.get('timestamp', row.get('created_at'))
                
                entry = LogEntry(
                    id=row['id'],
                    timestamp=timestamp_value,
                    level=row['level'],
                    entry_type=row['entry_type'],
                    message=row['message'],
                    task_id=row['task_id'],
                    user=row.get('user', row.get('user_id')),
                    metadata=row['metadata'] if row['metadata'] else {}
                )
                result.append(entry)
            
            return result
            
        except Exception as e:
            logger.warning(f"Error getting log entries: {e}")
            return []
    
    # Transaction support
    def begin_transaction(self) -> None:
        """Begin a database transaction"""
        if not self.in_transaction:
            self.in_transaction = True
            logger.debug("Transaction started")
    
    def commit_transaction(self) -> None:
        """Commit the current transaction"""
        if self.in_transaction:
            self.conn.commit()
            self.in_transaction = False
            logger.debug("Transaction committed")
    
    def rollback_transaction(self) -> None:
        """Rollback the current transaction"""
        if self.in_transaction:
            self.conn.rollback()
            self.in_transaction = False
            logger.debug("Transaction rolled back")
    
    # Migration support
    def get_schema_version(self) -> int:
        """Get current schema version"""
        self.cursor.execute("SELECT version FROM schema_version WHERE id = 1")
        row = self.cursor.fetchone()
        
        if not row:
            return 0
        
        return row['version']
    
    def set_schema_version(self, version: int) -> None:
        """Set schema version"""
        self.cursor.execute("""
            UPDATE schema_version 
            SET version = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        """, (version,))
        
        if not self.in_transaction:
            self.conn.commit()
    
    # Member operations
    def create_member(self, member: Member) -> Member:
        """Create a new member"""
        self.cursor.execute("""
            INSERT INTO members (
                id, name, role, position, age, sex, profile, 
                leader_id, profile_image_path, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING created_at, updated_at
        """, (
            member.id,
            member.name,
            member.role.value if hasattr(member.role, 'value') else member.role,
            member.position.value if hasattr(member.position, 'value') else member.position,
            member.age,
            member.sex,
            member.profile,
            member.leader_id,
            member.profile_image_path,
            member.created_at or datetime.now(),
            member.updated_at or datetime.now()
        ))
        
        result = self.cursor.fetchone()
        if not self.in_transaction:
            self.conn.commit()
        
        member.created_at = result['created_at']
        member.updated_at = result['updated_at']
        
        return member
    
    def _sanitize_json(self, data):
        """Convert non-JSON-serializable values to serializable ones"""
        if isinstance(data, dict):
            return {k: self._sanitize_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif hasattr(data, 'value'):  # Handle enum values
            return data.value
        else:
            return data
            
    def _ensure_log_entries_columns(self):
        """Ensure log_entries table has all necessary columns"""
        try:
            # Check for level column in log_entries
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'log_entries' AND column_name = 'level'
            """)
            if not self.cursor.fetchone():
                logger.info("Adding missing level column to log_entries table")
                self.cursor.execute("ALTER TABLE log_entries ADD COLUMN level VARCHAR(20)")
                self.conn.commit()
                
            # Check for created_at column in log_entries
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'log_entries' AND column_name = 'created_at'
            """)
            if not self.cursor.fetchone():
                logger.info("Adding missing created_at column to log_entries table")
                self.cursor.execute("ALTER TABLE log_entries ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                self.conn.commit()
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error checking or adding log_entries columns: {e}")
    
    def get_member(self, member_id: str) -> Optional[Member]:
        """Get a member by ID"""
        self.cursor.execute("SELECT * FROM members WHERE id = %s", (member_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        return Member(
            id=row['id'],
            name=row['name'],
            role=row['role'],
            position=row['position'],
            age=row['age'],
            sex=row['sex'],
            profile=row['profile'],
            leader_id=row['leader_id'],
            profile_image_path=row['profile_image_path'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def update_member(self, member: Member) -> Optional[Member]:
        """Update an existing member"""
        self.cursor.execute("""
            UPDATE members
            SET name = %s,
                role = %s,
                position = %s,
                age = %s,
                sex = %s,
                profile = %s,
                leader_id = %s,
                profile_image_path = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING updated_at
        """, (
            member.name,
            member.role.value if hasattr(member.role, 'value') else member.role,
            member.position.value if hasattr(member.position, 'value') else member.position,
            member.age,
            member.sex,
            member.profile,
            member.leader_id,
            member.profile_image_path,
            member.id
        ))
        
        if self.cursor.rowcount == 0:
            return None
        
        result = self.cursor.fetchone()
        if not self.in_transaction:
            self.conn.commit()
        
        member.updated_at = result['updated_at']
        return member
    
    def delete_member(self, member_id: str) -> bool:
        """Delete a member"""
        self.cursor.execute("DELETE FROM members WHERE id = %s", (member_id,))
        if not self.in_transaction:
            self.conn.commit()
        return self.cursor.rowcount > 0
    
    def list_members(self, filters: Dict[str, Any] = None) -> List[Member]:
        """List members with optional filters"""
        query = "SELECT * FROM members WHERE 1=1"
        params = []
        
        if filters:
            if 'role' in filters:
                query += " AND role = %s"
                params.append(filters['role'])
            
            if 'position' in filters:
                query += " AND position = %s"
                params.append(filters['position'])
            
            if 'leader_id' in filters:
                query += " AND leader_id = %s"
                params.append(filters['leader_id'])
        
        query += " ORDER BY name"
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        return [Member(
            id=row['id'],
            name=row['name'],
            role=row['role'],
            position=row['position'],
            age=row['age'],
            sex=row['sex'],
            profile=row['profile'],
            leader_id=row['leader_id'],
            profile_image_path=row['profile_image_path'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        ) for row in rows]
    
    # Project operations
    def create_project(self, project: Project) -> Project:
        """Create a new project"""
        try:
            # Execute simple insert with basic columns directly
            self.cursor.execute("""
                INSERT INTO projects (id, name, description)
                VALUES (%s, %s, %s)
                RETURNING *
            """, (project.id, project.name, project.description))
            logger.info(f"Created basic project with id={project.id}, name={project.name}")
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise
        
        # Process result
        try:
            result = self.cursor.fetchone()
            # If result is a dictionary
            if hasattr(result, 'keys'):
                if 'created_at' in result:
                    project.created_at = result['created_at']
                if 'updated_at' in result:
                    project.updated_at = result['updated_at']
            # If result is a tuple
            elif result and len(result) >= 3:
                # Typical column order: id, name, description, created_at, updated_at
                # Indexes depend on the database
                pass  # Implement if value retrieval from tuple is needed
        except Exception as e:
            logger.warning(f"Failed to extract dates from result: {e}")
        
        if not self.in_transaction:
            self.conn.commit()
        
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        self.cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        # Create project with only required fields
        project = Project(
            id=row['id'],
            name=row['name'],
            description=row['description']
        )
        
        # Add optional fields only if they exist
        if 'owner_id' in row and row['owner_id']:
            project.owner_id = row['owner_id']
            
        if 'status' in row and row['status']:
            project.status = row['status']
            
        if 'created_at' in row and row['created_at']:
            project.created_at = row['created_at']
            
        if 'updated_at' in row and row['updated_at']:
            project.updated_at = row['updated_at']
            
        return project
    
    def update_project(self, project: Project) -> Optional[Project]:
        """Update an existing project"""
        self.cursor.execute("""
            UPDATE projects
            SET name = %s,
                description = %s,
                owner_id = %s,
                status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING updated_at
        """, (
            project.name,
            project.description,
            project.owner_id,
            project.status,
            project.id
        ))
        
        if self.cursor.rowcount == 0:
            return None
        
        result = self.cursor.fetchone()
        if not self.in_transaction:
            self.conn.commit()
        
        project.updated_at = result['updated_at']
        return project
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project"""
        self.cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        if not self.in_transaction:
            self.conn.commit()
        return self.cursor.rowcount > 0
    
    def list_projects(self, filters: Dict[str, Any] = None) -> List[Project]:
        """List projects with optional filters"""
        query = "SELECT * FROM projects WHERE 1=1"
        params = []
        
        if filters:
            if 'status' in filters:
                query += " AND status = %s"
                params.append(filters['status'])
            
            if 'owner_id' in filters:
                query += " AND owner_id = %s"
                params.append(filters['owner_id'])
        
        query += " ORDER BY name"
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        result = []
        for row in rows:
            # Create project with required fields
            project = Project(
                id=row['id'],
                name=row['name'],
                description=row.get('description')
            )
            
            # Add optional fields if they exist
            if 'owner_id' in row:
                project.owner_id = row['owner_id']
            if 'status' in row:
                project.status = row['status']
            if 'created_at' in row:
                project.created_at = row['created_at']
            if 'updated_at' in row:
                project.updated_at = row['updated_at']
                
            result.append(project)
            
        return result
    
    # Project membership operations
    def add_project_member(self, project_id_or_membership, member_id=None):
        """Add a member to a project
        
        This method has two forms:
        1. add_project_member(project_id, member_id) -> bool
        2. add_project_member(membership: ProjectMembership) -> ProjectMembership
        """
        # Handle overloaded call
        if isinstance(project_id_or_membership, str) and member_id is not None:
            # When string project_id and member_id are specified (form 1)
            project_id = project_id_or_membership
            # Try direct insertion
            try:
                self.cursor.execute("""
                    INSERT INTO project_memberships (project_id, member_id, joined_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (project_id, member_id) DO NOTHING
                """, (project_id, member_id))
                
                if not self.in_transaction:
                    self.conn.commit()
                
                return True
                
            except psycopg2.IntegrityError:
                if not self.in_transaction:
                    self.conn.rollback()
                return False
                
        else:
            # When ProjectMembership object is specified (form 2)
            membership = project_id_or_membership
            
            # Preserve external transaction state
            was_in_transaction = self.in_transaction
            try:
                try:
                    # Version with joined_at column
                    self.cursor.execute("""
                        INSERT INTO project_memberships (project_id, member_id, joined_at)
                        VALUES (%s, %s, %s)
                        RETURNING *
                    """, (
                        membership.project_id,
                        membership.member_id,
                        membership.joined_at or datetime.now()
                    ))
                except Exception as e:
                    # Rollback transaction and reconnect
                    if not was_in_transaction:
                        self.conn.rollback()
                    
                    logger.warning(f"Failed with joined_at, trying without: {e}")
                    
                    # Simple version without joined_at
                    self.cursor.execute("""
                        INSERT INTO project_memberships (project_id, member_id)
                        VALUES (%s, %s)
                        RETURNING *
                    """, (
                        membership.project_id,
                        membership.member_id
                    ))
                
                result = self.cursor.fetchone()
                if not self.in_transaction:
                    self.conn.commit()
                
                # If result is a dictionary, update joined_at if it exists
                if hasattr(result, 'keys') and 'joined_at' in result:
                    membership.joined_at = result['joined_at']
                return membership
                
            except psycopg2.IntegrityError:
                if not self.in_transaction:
                    self.conn.rollback()
                logger.warning("Membership already exists or invalid project/member ID")
                return membership
    
    def remove_project_member(self, project_id: str, member_id: str) -> bool:
        """Remove a member from a project"""
        self.cursor.execute("""
            DELETE FROM project_memberships
            WHERE project_id = %s AND member_id = %s
        """, (project_id, member_id))
        
        if not self.in_transaction:
            self.conn.commit()
        
        return self.cursor.rowcount > 0
    
    def get_project_members(self, project_id: str) -> List[Member]:
        """Get all members of a project"""
        self.cursor.execute("""
            SELECT m.*
            FROM members m
            JOIN project_memberships pm ON m.id = pm.member_id
            WHERE pm.project_id = %s
            ORDER BY m.name
        """, (project_id,))
        
        rows = self.cursor.fetchall()
        
        return [Member(
            id=row['id'],
            name=row['name'],
            role=row['role'],
            position=row['position'],
            age=row['age'],
            sex=row['sex'],
            profile=row['profile'],
            leader_id=row['leader_id'],
            profile_image_path=row['profile_image_path'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        ) for row in rows]
    
    def get_member_projects(self, member_id: str) -> List[Project]:
        """Get all projects a member belongs to"""
        try:
            self.cursor.execute("""
                SELECT p.*
                FROM projects p
                JOIN project_memberships pm ON p.id = pm.project_id
                WHERE pm.member_id = %s
                ORDER BY p.name
            """, (member_id,))
            
            rows = self.cursor.fetchall()
            
            result = []
            for row in rows:
                # Create project with only required properties
                project = Project(
                    id=row['id'],
                    name=row['name'],
                    description=row.get('description')
                )
                
                # Add optional properties if they exist
                if 'owner_id' in row:
                    project.owner_id = row['owner_id']
                if 'status' in row:
                    project.status = row['status']
                if 'created_at' in row:
                    project.created_at = row['created_at']
                if 'updated_at' in row:
                    project.updated_at = row['updated_at']
                    
                result.append(project)
                
            return result
        except Exception as e:
            logger.warning(f"Error getting member projects: {e}")
            return []
        
    # Relation operations - compatibility layer with other methods
    def add_relation(self, parent_id: str, child_id: str, relation_type: str = "subtask"):
        """Add a relation between tasks (compatibility method)"""
        relationship = TaskRelationship(
            parent_id=parent_id,
            child_id=child_id,
            relationship_type=relation_type
        )
        return self.create_relationship(relationship)
            
    def remove_relation(self, parent_id: str, child_id: str):
        """Remove a relation between tasks (compatibility method)"""
        self.cursor.execute("""
            DELETE FROM task_relations WHERE parent_id = %s AND child_id = %s
        """, (parent_id, child_id))
        if not self.in_transaction:
            self.conn.commit()
        
    def get_task_relations(self, task_id: str) -> Dict[str, List[str]]:
        """Get all relations for a task (compatibility method)"""
        # Get parents
        self.cursor.execute("""
            SELECT parent_id, relationship_type FROM task_relations WHERE child_id = %s
        """, (task_id,))
        parent_rows = self.cursor.fetchall()
        
        # Get children
        self.cursor.execute("""
            SELECT child_id, relationship_type FROM task_relations WHERE parent_id = %s
        """, (task_id,))
        child_rows = self.cursor.fetchall()
        
        relations = {
            'parents': [row['parent_id'] for row in parent_rows],
            'children': [row['child_id'] for row in child_rows],
            'subtasks': [row['child_id'] for row in child_rows if row['relationship_type'] == 'parent-child'],
            'blocks': [row['child_id'] for row in child_rows if row['relationship_type'] == 'blocks'],
            'blocked_by': [row['parent_id'] for row in parent_rows if row['relationship_type'] == 'blocks']
        }
        
        return relations
        
    # File operations - compatibility layer with other methods
    def add_file(self, task_id: str, file_path: str, file_type: Optional[str] = None):
        """Add a file to a task (compatibility method)"""
        association = FileAssociation(
            task_id=task_id,
            file_path=file_path,
            file_type=file_type
        )
        return self.add_file_association(association)
            
    def remove_file(self, task_id: str, file_path: str):
        """Remove a file from a task (compatibility method)"""
        self.cursor.execute("""
            DELETE FROM task_files WHERE task_id = %s AND file_path = %s
        """, (task_id, file_path))
        if not self.in_transaction:
            self.conn.commit()
        
    def get_task_files(self, task_id: str) -> List[FileAssociation]:
        """Get all files for a task (compatibility method)"""
        return self.get_file_associations(task_id)
        
    # Query operations
    def search_tasks(self, query: str) -> List[Task]:
        """Search tasks by text"""
        # Search in title, description, and context
        search_pattern = f"%{query}%"
        self.cursor.execute("""
            SELECT * FROM tasks 
            WHERE title ILIKE %s 
               OR description ILIKE %s
               OR tags ILIKE %s
            ORDER BY priority DESC, created_at DESC
        """, (search_pattern, search_pattern, search_pattern))
        
        rows = self.cursor.fetchall()
        return [self._row_to_task(row) for row in rows]
        
    def get_assignees(self) -> List[str]:
        """Get all unique assignees"""
        self.cursor.execute("SELECT DISTINCT assignee FROM tasks WHERE assignee IS NOT NULL ORDER BY assignee")
        return [row['assignee'] for row in self.cursor.fetchall()]
        
    def get_projects(self) -> List[str]:
        """Get all unique projects"""
        self.cursor.execute("SELECT DISTINCT id, name FROM projects ORDER BY name")
        return [row['id'] for row in self.cursor.fetchall()]
        
    def get_tags(self) -> List[str]:
        """Get all unique tags"""
        try:
            # Verify tags column exists first
            self.cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tasks' AND column_name = 'tags'
            """)
            if not self.cursor.fetchone():
                return []
                
            self.cursor.execute("SELECT DISTINCT tags FROM tasks WHERE tags IS NOT NULL")
            all_tags = set()
            for row in self.cursor.fetchall():
                if row['tags']:
                    all_tags.update(tag.strip() for tag in row['tags'].split(','))
            return sorted(list(all_tags))
        except Exception as e:
            logger.warning(f"Error getting tags: {e}")
            return []
        
    def _row_to_task(self, row: dict) -> Task:
        """Convert a database row to a Task object"""
        tags = []
        if 'tags' in row and row['tags']:
            tags = [tag.strip() for tag in row['tags'].split(',')]
        
        # Create basic task with required fields
        task_data = {
            'id': row['id'],
            'title': row['title'],
            'description': row.get('description'),
            'status': row['status'],
            'tags': tags
        }
        
        # Add optional fields if they exist
        optional_fields = {
            'assignee': 'assignee',
            'priority': 'priority',
            'due_date': 'due_date',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            'completed_at': 'completed_at', 
            'order_num': 'order_num',
            'external_id': 'external_id',
            'external_url': 'external_url',
            'sync_status': 'sync_status',
            'project_id': 'project_id',
            'work_started_file_count': 'work_started_file_count'
        }
        
        for field, row_key in optional_fields.items():
            if row_key in row and row[row_key] is not None:
                task_data[field] = row[row_key]
        
        return Task(**task_data)