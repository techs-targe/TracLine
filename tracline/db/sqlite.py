"""SQLite database implementation."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from tracline.core.config import DatabaseConfig
from tracline.db.interface import DatabaseInterface
from tracline.models import (
    Task, TaskRelationship, FileAssociation, LogEntry,
    TaskStatus, TaskPriority,
    Member, Project, ProjectMembership
)


class SQLiteDatabase(DatabaseInterface):
    """SQLite database implementation."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.conn = None
        self.cursor = None
        self.db_type = 'sqlite'  # For database type detection
        
        # Use url, path, or default path
        if hasattr(config, 'url') and config.url:
            self.db_path = Path(config.url).expanduser()
        elif hasattr(config, 'path') and config.path:
            self.db_path = Path(config.path).expanduser()
        else:
            self.db_path = Path.home() / ".tracline" / "tracline.db"
    
    def connect(self) -> None:
        """Connect to the database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def disconnect(self) -> None:
        """Disconnect from the database."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            
    def execute_query(self, query: str, params: List[Any] = None) -> None:
        """Execute a query with parameters, handling DB-specific placeholders.
        
        SQLite uses ? placeholders which is our standard format, so no conversion needed.
        
        Args:
            query: SQL query with ? placeholders
            params: List of parameters to substitute for the placeholders
        """
        # Execute with parameters or without if None
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
            
        return self.cursor
    
    def initialize_schema(self) -> None:
        """Initialize database schema."""
        # Only connect if not already connected
        if self.conn is None:
            self.connect()
        
        # Tasks table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                assignee TEXT,
                project_id TEXT,
                priority INTEGER DEFAULT 3,
                due_date TEXT,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                order_num INTEGER,
                external_id TEXT,
                external_url TEXT,
                sync_status TEXT,
                work_started_file_count INTEGER DEFAULT NULL
            )
        """)
        
        # Add project_id column if it doesn't exist (for backward compatibility)
        try:
            self.cursor.execute("SELECT project_id FROM tasks LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding project_id column to tasks table")
            self.cursor.execute("ALTER TABLE tasks ADD COLUMN project_id TEXT")
            
        # Add due_date column if it doesn't exist
        try:
            self.cursor.execute("SELECT due_date FROM tasks LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding due_date column to tasks table")
            self.cursor.execute("ALTER TABLE tasks ADD COLUMN due_date TEXT")
            
        # Ensure status column exists and has proper type
        try:
            self.cursor.execute("SELECT status FROM tasks LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding status column to tasks table")
            self.cursor.execute("ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'TODO'")
        
        # Add work_started_file_count column if it doesn't exist
        try:
            self.cursor.execute("SELECT work_started_file_count FROM tasks LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding work_started_file_count column to tasks table")
            self.cursor.execute("ALTER TABLE tasks ADD COLUMN work_started_file_count INTEGER DEFAULT NULL")
        
        # Task relationships table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id TEXT NOT NULL,
                child_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT,
                FOREIGN KEY (parent_id) REFERENCES tasks(task_id),
                FOREIGN KEY (child_id) REFERENCES tasks(task_id),
                UNIQUE(parent_id, child_id)
            )
        """)
        
        # File associations table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                relative_path TEXT,
                file_type TEXT,
                description TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT,
                last_modified TEXT,
                file_size INTEGER,
                reference_count INTEGER DEFAULT 1,
                FOREIGN KEY (task_id) REFERENCES tasks(id),
                UNIQUE(task_id, file_path)
            )
        """)
        
        # Add description column if it doesn't exist in file_associations
        try:
            self.cursor.execute("SELECT description FROM file_associations LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding description column to file_associations table")
            self.cursor.execute("ALTER TABLE file_associations ADD COLUMN description TEXT")
        
        # Log entries table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT DEFAULT 'INFO',
                entry_type TEXT NOT NULL,
                message TEXT NOT NULL,
                task_id TEXT,
                user TEXT,
                metadata TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """)
        
        # Schema version table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)
        
        # Members table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                position TEXT NOT NULL,
                age INTEGER,
                sex TEXT,
                profile TEXT,
                leader_id TEXT,
                profile_image_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(leader_id) REFERENCES members(id)
            )
        """)
        
        # Projects table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner_id TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY(owner_id) REFERENCES members(id)
            )
        """)
        
        # Project memberships table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_memberships (
                project_id TEXT NOT NULL,
                member_id TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                PRIMARY KEY(project_id, member_id),
                FOREIGN KEY(project_id) REFERENCES projects(id),
                FOREIGN KEY(member_id) REFERENCES members(id)
            )
        """)
        
        # File access log table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                action TEXT NOT NULL,
                task_id TEXT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                metadata TEXT
            )
        """)
        
        # Project settings table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_settings (
                project_id TEXT PRIMARY KEY,
                github_enabled BOOLEAN DEFAULT 0,
                github_repo TEXT,
                github_token TEXT,
                webhook_url TEXT,
                webhook_secret TEXT,
                monitor_enabled BOOLEAN DEFAULT 0,
                monitor_path TEXT,
                monitor_interval INTEGER DEFAULT 60,
                monitor_extensions TEXT,
                strict_doc_read BOOLEAN DEFAULT 0,
                strict_file_ref BOOLEAN DEFAULT 0,
                strict_log_entry BOOLEAN DEFAULT 0,
                project_root TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        
        # Add project_root column if it doesn't exist
        try:
            self.cursor.execute("SELECT project_root FROM project_settings LIMIT 1")
        except sqlite3.OperationalError:
            print("Adding project_root column to project_settings table")
            self.cursor.execute("ALTER TABLE project_settings ADD COLUMN project_root TEXT")
        
        # Create indexes
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_members_leader_id ON members(leader_id)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id)
        """)
        
        # Add status index if column exists
        try:
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """)
        except sqlite3.OperationalError:
            print("Could not create index: column 'status' does not exist")
        
        # Add project_id index if column exists
        try:
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id)
            """)
        except sqlite3.OperationalError:
            print("Could not create index: column 'project_id' does not exist")
        
        # Add due_date index if column exists
        try:
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)
            """)
        except sqlite3.OperationalError:
            print("Could not create index: column 'due_date' does not exist")
        
        # Set initial version if not exists
        self.cursor.execute("SELECT version FROM schema_version")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO schema_version (version) VALUES (1)")
        
        self.conn.commit()
    
    # Helper methods
    def _task_from_row(self, row: sqlite3.Row) -> Task:
        """Convert database row to Task object."""
        data = dict(row)
        
        # Rename task_id to id
        data['id'] = data.pop('task_id')
        
        # Convert string timestamps to datetime
        for field in ['created_at', 'updated_at', 'completed_at', 'due_date']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert tags from JSON string to list
        if data.get('tags'):
            import json
            data['tags'] = json.loads(data['tags'])
        else:
            data['tags'] = []
        
        return Task(**data)
    
    def _task_to_row(self, task: Task) -> Dict[str, Any]:
        """Convert Task object to database row."""
        # Use model_dump with mode='json' to convert enums to their values
        if hasattr(task, 'model_dump'):
            data = task.model_dump(mode='json')
        else:
            data = task.dict()
            # Manually convert enums for older pydantic versions
            if data.get('status'):
                data['status'] = data['status'].value
            if data.get('priority'):
                data['priority'] = data['priority'].value
        
        # Rename id to task_id for SQLite
        data['task_id'] = data.pop('id')
        
        # Convert datetime to string (they're already converted with mode='json')
        for field in ['created_at', 'updated_at', 'completed_at', 'due_date']:
            if data.get(field) and not isinstance(data[field], str):
                data[field] = data[field].isoformat()
        
        # Convert tags list to JSON string (including empty lists)
        if 'tags' in data and isinstance(data['tags'], list):
            import json
            data['tags'] = json.dumps(data['tags'])
        
        return data
    
    # Task operations
    def create_task(self, task: Task) -> Task:
        """Create a new task."""
        self.cursor.execute("""
            SELECT MAX(order_num) FROM tasks
        """)
        result = self.cursor.fetchone()
        max_order = result[0] if result and result[0] else 0
        task.order_num = max_order + 1
        
        data = self._task_to_row(task)
        
        placeholders = ', '.join(['?'] * len(data))
        columns = ', '.join(data.keys())
        
        self.cursor.execute(
            f"INSERT INTO tasks ({columns}) VALUES ({placeholders})",
            list(data.values())
        )
        self.conn.commit()
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        self.cursor.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,)
        )
        row = self.cursor.fetchone()
        
        if row:
            return self._task_from_row(row)
        return None
    
    def update_task(self, task: Task) -> Task:
        """Update an existing task."""
        data = self._task_to_row(task)
        
        set_clause = ', '.join([f"{k} = ?" for k in data.keys() if k != 'task_id'])
        values = [v for k, v in data.items() if k != 'task_id']
        values.append(task.id)
        
        self.cursor.execute(
            f"UPDATE tasks SET {set_clause} WHERE task_id = ?",
            values
        )
        self.conn.commit()
        
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        self.cursor.execute(
            "DELETE FROM tasks WHERE task_id = ?",
            (task_id,)
        )
        self.conn.commit()
        
        return self.cursor.rowcount > 0
    
    def list_tasks(self, filters: Dict[str, Any] = None, 
                  sort_by: str = "order_num",
                  limit: Optional[int] = None) -> List[Task]:
        """List tasks with optional filtering and sorting."""
        query = "SELECT * FROM tasks"
        where_clauses = []
        params = []
        
        if filters:
            for field, value in filters.items():
                if field == 'tags':
                    where_clauses.append("tags LIKE ?")
                    params.append(f'%"{value}"%')
                elif field == 'exclude_status':
                    where_clauses.append("status != ?")
                    params.append(value)
                else:
                    where_clauses.append(f"{field} = ?")
                    params.append(value)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Apply sorting with fallback to created_at if the column doesn't exist
        # SQLite table has different column naming: task_id instead of id
        valid_sort_columns = ["task_id", "title", "status", "assignee", "priority", "created_at", 
                             "updated_at", "due_date", "order_num", "project_id"]
        if sort_by in valid_sort_columns or sort_by == "id":
            # Handle special case for id vs task_id
            actual_sort_by = "task_id" if sort_by == "id" else sort_by
            query += f" ORDER BY {actual_sort_by}"
        else:
            # Fallback to a safe default
            print(f"WARNING: Invalid sort column '{sort_by}', falling back to created_at")
            query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        self.cursor.execute(query, params)
        
        return [self._task_from_row(row) for row in self.cursor.fetchall()]
    
    def get_next_task(self, assignee: Optional[str] = None,
                     project_id: Optional[str] = None,
                     exclude_states: List[str] = None) -> Optional[Task]:
        """Get the next task in the queue."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if assignee:
            query += " AND assignee = ?"
            params.append(assignee)
            
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        
        if exclude_states:
            placeholders = ','.join(['?'] * len(exclude_states))
            query += f" AND status NOT IN ({placeholders})"
            params.extend(exclude_states)
        
        query += " ORDER BY priority DESC, order_num LIMIT 1"
        
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        
        if row:
            return self._task_from_row(row)
        return None
    
    def reorder_task(self, task_id: str, new_position: int) -> bool:
        """Reorder a task to a new position."""
        # Get current position
        self.cursor.execute(
            "SELECT order_num FROM tasks WHERE task_id = ?",
            (task_id,)
        )
        row = self.cursor.fetchone()
        
        if not row:
            return False
        
        current_position = row[0]
        
        if current_position == new_position:
            return True
        
        # Update positions
        if new_position < current_position:
            self.cursor.execute("""
                UPDATE tasks SET order_num = order_num + 1
                WHERE order_num >= ? AND order_num < ?
            """, (new_position, current_position))
        else:
            self.cursor.execute("""
                UPDATE tasks SET order_num = order_num - 1
                WHERE order_num > ? AND order_num <= ?
            """, (current_position, new_position))
        
        # Set new position
        self.cursor.execute(
            "UPDATE tasks SET order_num = ? WHERE task_id = ?",
            (new_position, task_id)
        )
        
        self.conn.commit()
        return True
    
    # Relationship operations  
    def create_relationship(self, relationship: TaskRelationship) -> TaskRelationship:
        """Create a task relationship."""
        self.cursor.execute("""
            INSERT INTO task_relationships 
            (parent_id, child_id, relationship_type, created_at, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (
            relationship.parent_id,
            relationship.child_id,
            relationship.relationship_type,
            relationship.created_at.isoformat(),
            relationship.created_by
        ))
        
        relationship.id = self.cursor.lastrowid
        self.conn.commit()
        return relationship
    
    def get_relationships(self, task_id: str = None,
                         relationship_type: str = None) -> List[TaskRelationship]:
        """Get task relationships."""
        query = "SELECT * FROM task_relationships WHERE 1=1"
        params = []
        
        if task_id:
            query += " AND (parent_id = ? OR child_id = ?)"
            params.extend([task_id, task_id])
        
        if relationship_type:
            query += " AND relationship_type = ?"
            params.append(relationship_type)
        
        self.cursor.execute(query, params)
        
        relationships = []
        for row in self.cursor.fetchall():
            data = dict(row)
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            relationships.append(TaskRelationship(**data))
        
        return relationships
    
    def delete_relationship(self, relationship_id: int) -> bool:
        """Delete a task relationship."""
        self.cursor.execute(
            "DELETE FROM task_relationships WHERE id = ?",
            (relationship_id,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    # File association operations
    def add_file_association(self, association: FileAssociation) -> FileAssociation:
        """Add a file association."""
        self.cursor.execute("""
            INSERT INTO file_associations
            (task_id, file_path, relative_path, file_type, created_at, 
             created_by, last_modified, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            association.task_id,
            association.file_path,
            association.relative_path,
            association.file_type,
            association.created_at.isoformat(),
            association.created_by,
            association.last_modified.isoformat() if association.last_modified else None,
            association.file_size
        ))
        
        association.id = self.cursor.lastrowid
        self.conn.commit()
        return association
    
    def get_file_associations(self, task_id: str) -> List[FileAssociation]:
        """Get file associations for a task."""
        self.cursor.execute(
            "SELECT * FROM file_associations WHERE task_id = ?",
            (task_id,)
        )
        
        associations = []
        for row in self.cursor.fetchall():
            data = dict(row)
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('last_modified'):
                data['last_modified'] = datetime.fromisoformat(data['last_modified'])
            associations.append(FileAssociation(**data))
        
        return associations
    
    def get_all_file_associations(self) -> List[FileAssociation]:
        """Get all file associations in the system."""
        self.cursor.execute("SELECT * FROM file_associations ORDER BY created_at DESC")
        
        associations = []
        for row in self.cursor.fetchall():
            data = dict(row)
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('last_modified'):
                data['last_modified'] = datetime.fromisoformat(data['last_modified'])
            associations.append(FileAssociation(**data))
        
        return associations
    
    def remove_file_association(self, association_id: int) -> bool:
        """Remove a file association."""
        self.cursor.execute(
            "DELETE FROM file_associations WHERE id = ?",
            (association_id,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    # Log operations
    def add_log_entry(self, entry: LogEntry) -> LogEntry:
        """Add a log entry."""
        import json
        
        self.cursor.execute("""
            INSERT INTO log_entries
            (timestamp, level, entry_type, message, task_id, user, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.timestamp.isoformat(),
            entry.level,
            entry.entry_type,
            entry.message,
            entry.task_id,
            entry.user,
            json.dumps(entry.metadata)
        ))
        
        entry.id = self.cursor.lastrowid
        self.conn.commit()
        return entry
    
    def get_log_entries(self, task_id: str = None,
                       limit: int = 100) -> List[LogEntry]:
        """Get log entries."""
        import json
        
        query = "SELECT * FROM log_entries"
        params = []
        
        if task_id:
            query += " WHERE task_id = ?"
            params.append(task_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        self.cursor.execute(query, params)
        
        entries = []
        for row in self.cursor.fetchall():
            data = dict(row)
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            data['metadata'] = json.loads(data['metadata'])
            entries.append(LogEntry(**data))
        
        return entries
    
    # Transaction support
    def begin_transaction(self) -> None:
        """Begin a database transaction."""
        self.conn.execute("BEGIN")
    
    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        self.conn.commit()
    
    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        self.conn.rollback()
    
    # Migration support
    def get_schema_version(self) -> int:
        """Get current schema version."""
        self.cursor.execute("SELECT version FROM schema_version")
        row = self.cursor.fetchone()
        return row[0] if row else 0
    
    def set_schema_version(self, version: int) -> None:
        """Set schema version."""
        self.cursor.execute(
            "UPDATE schema_version SET version = ?",
            (version,)
        )
        self.conn.commit()
    
    # Member operations
    def create_member(self, member: Member) -> Member:
        """Create a new member."""
        self.cursor.execute("""
            INSERT INTO members (
                id, name, role, position, age, sex, profile,
                leader_id, profile_image_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            member.id, member.name, member.role, member.position,
            member.age, member.sex, member.profile, member.leader_id,
            member.profile_image_path, member.created_at.isoformat(),
            member.updated_at.isoformat()
        ))
        self.conn.commit()
        return member
    
    def get_member(self, member_id: str) -> Optional[Member]:
        """Get a member by ID."""
        self.cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
        row = self.cursor.fetchone()
        return self._member_from_row(row) if row else None
    
    def update_member(self, member: Member) -> Optional[Member]:
        """Update an existing member."""
        self.cursor.execute("""
            UPDATE members SET
                name = ?, role = ?, position = ?, age = ?, sex = ?,
                profile = ?, leader_id = ?, profile_image_path = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            member.name, member.role, member.position, member.age,
            member.sex, member.profile, member.leader_id,
            member.profile_image_path, member.updated_at.isoformat(),
            member.id
        ))
        self.conn.commit()
        return member if self.cursor.rowcount > 0 else None
    
    def delete_member(self, member_id: str) -> bool:
        """Delete a member."""
        self.cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def list_members(self, filters: Dict[str, Any] = None) -> List[Member]:
        """List members with optional filters."""
        query = "SELECT * FROM members"
        where_clauses = []
        params = []
        
        if filters:
            for field, value in filters.items():
                where_clauses.append(f"{field} = ?")
                params.append(value)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY created_at DESC"
        
        self.cursor.execute(query, params)
        return [self._member_from_row(row) for row in self.cursor.fetchall()]
    
    # Project operations
    def create_project(self, project: Project) -> Project:
        """Create a new project."""
        self.cursor.execute("""
            INSERT INTO projects (
                id, name, description, owner_id, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project.id, project.name, project.description,
            project.owner_id, project.status,
            project.created_at.isoformat(),
            project.updated_at.isoformat()
        ))
        self.conn.commit()
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        self.cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = self.cursor.fetchone()
        return self._project_from_row(row) if row else None
    
    def update_project(self, project: Project) -> Optional[Project]:
        """Update an existing project."""
        self.cursor.execute("""
            UPDATE projects SET
                name = ?, description = ?, owner_id = ?,
                status = ?, updated_at = ?
            WHERE id = ?
        """, (
            project.name, project.description, project.owner_id,
            project.status, project.updated_at.isoformat(),
            project.id
        ))
        self.conn.commit()
        return project if self.cursor.rowcount > 0 else None
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        self.cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def list_projects(self, filters: Dict[str, Any] = None) -> List[Project]:
        """List projects with optional filters."""
        query = "SELECT * FROM projects"
        where_clauses = []
        params = []
        
        if filters:
            for field, value in filters.items():
                where_clauses.append(f"{field} = ?")
                params.append(value)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY created_at DESC"
        
        self.cursor.execute(query, params)
        return [self._project_from_row(row) for row in self.cursor.fetchall()]
    
    # Project membership operations
    def add_project_member(self, membership: ProjectMembership) -> ProjectMembership:
        """Add a member to a project."""
        self.cursor.execute("""
            INSERT INTO project_memberships (
                project_id, member_id, joined_at
            ) VALUES (?, ?, ?)
        """, (
            membership.project_id, membership.member_id,
            membership.joined_at.isoformat()
        ))
        self.conn.commit()
        return membership
    
    def remove_project_member(self, project_id: str, member_id: str) -> bool:
        """Remove a member from a project."""
        self.cursor.execute("""
            DELETE FROM project_memberships 
            WHERE project_id = ? AND member_id = ?
        """, (project_id, member_id))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_project_members(self, project_id: str) -> List[Member]:
        """Get all members of a project."""
        self.cursor.execute("""
            SELECT m.* FROM members m
            JOIN project_memberships pm ON m.id = pm.member_id
            WHERE pm.project_id = ?
            ORDER BY pm.joined_at
        """, (project_id,))
        return [self._member_from_row(row) for row in self.cursor.fetchall()]
    
    def get_member_projects(self, member_id: str) -> List[Project]:
        """Get all projects a member belongs to."""
        self.cursor.execute("""
            SELECT p.* FROM projects p
            JOIN project_memberships pm ON p.id = pm.project_id
            WHERE pm.member_id = ?
            ORDER BY pm.joined_at
        """, (member_id,))
        return [self._project_from_row(row) for row in self.cursor.fetchall()]
    
    # Helper methods for new models
    def _member_from_row(self, row: sqlite3.Row) -> Member:
        """Convert database row to Member object."""
        data = dict(row)
        
        # Convert string timestamps to datetime
        for field in ['created_at', 'updated_at']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        return Member(**data)
    
    def _project_from_row(self, row: sqlite3.Row) -> Project:
        """Convert database row to Project object."""
        data = dict(row)
        
        # Convert string timestamps to datetime
        for field in ['created_at', 'updated_at']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        return Project(**data)