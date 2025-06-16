"""Database interface for TracLine."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from tracline.models import (
    Task, TaskRelationship, FileAssociation, LogEntry,
    Member, Project, ProjectMembership
)


class DatabaseInterface(ABC):
    """Abstract base class for database operations."""
    
    @abstractmethod
    def connect(self) -> None:
        """Connect to the database."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the database."""
        pass
    
    @abstractmethod
    def initialize_schema(self) -> None:
        """Initialize database schema."""
        pass
        
    @abstractmethod
    def execute_query(self, query: str, params: List[Any] = None) -> None:
        """Execute a query with parameters, handling DB-specific placeholders.
        
        Args:
            query: SQL query with ? placeholders
            params: List of parameters to substitute for the placeholders
        """
        pass
    
    def __enter__(self):
        """Context manager entry point.
        
        Automatically connects to the database and returns self.
        """
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit handler.
        
        Automatically closes the database connection.
        """
        self.disconnect()
    
    # Task operations
    @abstractmethod
    def create_task(self, task: Task) -> Task:
        """Create a new task."""
        pass
    
    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        pass
    
    @abstractmethod
    def update_task(self, task: Task) -> Task:
        """Update an existing task."""
        pass
    
    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        pass
    
    @abstractmethod
    def list_tasks(self, filters: Dict[str, Any] = None, 
                  sort_by: str = "order_num",
                  limit: Optional[int] = None) -> List[Task]:
        """List tasks with optional filtering and sorting."""
        pass
    
    @abstractmethod
    def get_next_task(self, assignee: Optional[str] = None,
                     project_id: Optional[str] = None,
                     exclude_states: List[str] = None) -> Optional[Task]:
        """Get the next task in the queue."""
        pass
    
    @abstractmethod
    def reorder_task(self, task_id: str, new_position: int) -> bool:
        """Reorder a task to a new position."""
        pass
    
    # Relationship operations
    @abstractmethod
    def create_relationship(self, relationship: TaskRelationship) -> TaskRelationship:
        """Create a task relationship."""
        pass
    
    @abstractmethod
    def get_relationships(self, task_id: str = None,
                         relationship_type: str = None) -> List[TaskRelationship]:
        """Get task relationships."""
        pass
    
    @abstractmethod
    def delete_relationship(self, relationship_id: int) -> bool:
        """Delete a task relationship."""
        pass
    
    # File association operations
    @abstractmethod
    def add_file_association(self, association: FileAssociation) -> FileAssociation:
        """Add a file association."""
        pass
    
    @abstractmethod
    def get_file_associations(self, task_id: str) -> List[FileAssociation]:
        """Get file associations for a task."""
        pass
    
    @abstractmethod
    def get_all_file_associations(self) -> List[FileAssociation]:
        """Get all file associations in the system."""
        pass
    
    @abstractmethod
    def remove_file_association(self, association_id: int) -> bool:
        """Remove a file association."""
        pass
    
    # Log operations
    @abstractmethod
    def add_log_entry(self, entry: LogEntry) -> LogEntry:
        """Add a log entry."""
        pass
    
    @abstractmethod
    def get_log_entries(self, task_id: str = None,
                       limit: int = 100) -> List[LogEntry]:
        """Get log entries."""
        pass
    
    # Transaction support
    @abstractmethod
    def begin_transaction(self) -> None:
        """Begin a database transaction."""
        pass
    
    @abstractmethod
    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        pass
    
    @abstractmethod
    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        pass
    
    # Migration support
    @abstractmethod
    def get_schema_version(self) -> int:
        """Get current schema version."""
        pass
    
    @abstractmethod
    def set_schema_version(self, version: int) -> None:
        """Set schema version."""
        pass
    
    # Member operations
    @abstractmethod
    def create_member(self, member: Member) -> Member:
        """Create a new member."""
        pass
    
    @abstractmethod
    def get_member(self, member_id: str) -> Optional[Member]:
        """Get a member by ID."""
        pass
    
    @abstractmethod
    def update_member(self, member: Member) -> Optional[Member]:
        """Update an existing member."""
        pass
    
    @abstractmethod
    def delete_member(self, member_id: str) -> bool:
        """Delete a member."""
        pass
    
    @abstractmethod
    def list_members(self, filters: Dict[str, Any] = None) -> List[Member]:
        """List members with optional filters."""
        pass
    
    # Project operations
    @abstractmethod
    def create_project(self, project: Project) -> Project:
        """Create a new project."""
        pass
    
    @abstractmethod
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        pass
    
    @abstractmethod
    def update_project(self, project: Project) -> Optional[Project]:
        """Update an existing project."""
        pass
    
    @abstractmethod
    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        pass
    
    @abstractmethod
    def list_projects(self, filters: Dict[str, Any] = None) -> List[Project]:
        """List projects with optional filters."""
        pass
    
    # Project membership operations
    @abstractmethod
    def add_project_member(self, membership: ProjectMembership) -> ProjectMembership:
        """Add a member to a project."""
        pass
    
    @abstractmethod
    def remove_project_member(self, project_id: str, member_id: str) -> bool:
        """Remove a member from a project."""
        pass
    
    @abstractmethod
    def get_project_members(self, project_id: str) -> List[Member]:
        """Get all members of a project."""
        pass
    
    @abstractmethod
    def get_member_projects(self, member_id: str) -> List[Project]:
        """Get all projects a member belongs to."""
        pass