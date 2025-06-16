"""Task service for business logic."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from tracline.core.config import Config
from tracline.db import DatabaseInterface, DatabaseFactory
from tracline.models import (
    Task, TaskStatus, TaskPriority,
    TaskRelationship, RelationshipType,
    FileAssociation, LogEntry, LogEntryType
)


class TaskService:
    """Service layer for task operations."""
    
    def __init__(self, config: Config, db: Optional[DatabaseInterface] = None):
        self.config = config
        self.db = db or DatabaseFactory.create(config.get_database_config())
    
    def create_task(self, task_id: str, title: str, 
                   description: Optional[str] = None,
                   assignee: Optional[str] = None,
                   project_id: Optional[str] = None,
                   priority: int = TaskPriority.MEDIUM,
                   tags: List[str] = None) -> Task:
        """Create a new task."""
        # Use default assignee if none provided
        if assignee is None:
            assignee = self.config.get_default_assignee()
            
        # Use current project if none provided
        if project_id is None:
            project_id = self.config.get_current_project()
        
        # Create task model
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=self.config.fixed_states["initial"],
            assignee=assignee,
            project_id=project_id,
            priority=priority,
            tags=tags or []
        )
        
        # Save to database
        created_task = self.db.create_task(task)
        
        # Log the creation
        log_entry = LogEntry.create_task_log(
            task_id=task_id,
            entry_type=LogEntryType.TASK_CREATED,
            message=f"Task '{title}' created",
            user=assignee,
            metadata={"assignee": assignee, "priority": priority}
        )
        self.db.add_log_entry(log_entry)
        
        return created_task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.db.get_task(task_id)
    
    def update_task(self, task_id_or_task, **kwargs) -> Optional[Task]:
        """Update a task.
        
        Args:
            task_id_or_task: Either a task ID string or a Task object
            **kwargs: Task attributes to update (if task_id_or_task is a string)
            
        Returns:
            Updated Task object or None if task not found
        """
        # Determine if we got a task_id or a Task object
        if isinstance(task_id_or_task, str):
            # We got a task_id
            task_id = task_id_or_task
            task = self.db.get_task(task_id)
            if not task:
                return None
            
            # Update fields - handle datetime strings
            old_values = {}
            for key, value in kwargs.items():
                if hasattr(task, key) and value is not None:
                    old_values[key] = getattr(task, key)
                    
                    # Convert ISO format datetime strings to datetime objects
                    if key in ['created_at', 'updated_at', 'completed_at', 'due_date'] and isinstance(value, str):
                        try:
                            # Try to parse as ISO datetime string
                            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            # If parsing fails, keep original string
                            pass
                    
                    setattr(task, key, value)
            
            # Check if status is being updated from TODO to READY/DOING
            if 'status' in kwargs and 'status' in old_values:
                old_status = old_values['status']
                new_status = kwargs['status']
                
                if (old_status == TaskStatus.TODO.value and 
                    new_status == TaskStatus.READY.value):
                    # Count current files and set work_started_file_count
                    file_count = self._count_task_files(task_id)
                    task.work_started_file_count = file_count
            
            # Set updated timestamp if not explicitly provided
            if 'updated_at' not in kwargs:
                task.updated_at = datetime.now()
            
            # Log changes - ensure serializable for log entry
            log_message = f"Task updated: {', '.join(kwargs.keys())}"
            
            # Convert any datetime objects to ISO strings for logging
            clean_kwargs = {}
            clean_old_values = {}
            
            for k, v in kwargs.items():
                if isinstance(v, datetime):
                    clean_kwargs[k] = v.isoformat()
                else:
                    clean_kwargs[k] = v
                    
            for k, v in old_values.items():
                if isinstance(v, datetime):
                    clean_old_values[k] = v.isoformat()
                else:
                    clean_old_values[k] = v
            
            log_metadata = {"changes": clean_kwargs, "old_values": clean_old_values}
            
        else:
            # We got a Task object directly
            task = task_id_or_task
            task_id = task.id
            
            # Check that the task exists
            if not self.db.get_task(task_id):
                return None
            
            # Set updated timestamp if not already set
            if task.updated_at is None or task.updated_at == task.created_at:
                task.updated_at = datetime.now()
            
            # Simple log for direct task update
            log_message = "Task updated directly"
            log_metadata = {"updated_at": task.updated_at.isoformat()}
        
        # Save to database
        updated_task = self.db.update_task(task)
        
        # Log the update
        log_entry = LogEntry.create_task_log(
            task_id=task_id,
            entry_type=LogEntryType.TASK_UPDATED,
            message=log_message,
            user=task.assignee,
            metadata=log_metadata
        )
        self.db.add_log_entry(log_entry)
        
        return updated_task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        task = self.db.get_task(task_id)
        if not task:
            return False
        
        # Delete from database
        if self.db.delete_task(task_id):
            # Log the deletion
            log_entry = LogEntry.create_task_log(
                task_id=task_id,
                entry_type=LogEntryType.TASK_DELETED,
                message=f"Task '{task.title}' deleted",
                user=task.assignee
            )
            self.db.add_log_entry(log_entry)
            return True
        
        return False
    
    def list_tasks(self, assignee: Optional[str] = None,
                  status: Optional[str] = None,
                  project_id: Optional[str] = None,
                  priority: Optional[int] = None,
                  tags: List[str] = None,
                  exclude_status: Optional[str] = None,
                  sort_by: str = "order_num",
                  limit: Optional[int] = None) -> List[Task]:
        """List tasks with filtering."""
        filters = {}
        
        if assignee is not None:
            # If assignee is empty string, we want to see all tasks
            if assignee != "":
                filters["assignee"] = assignee
        elif self.config.get_default_assignee():
            filters["assignee"] = self.config.get_default_assignee()
        
        # Filter by project if provided, otherwise use current project
        if project_id is not None:
            filters["project_id"] = project_id
        elif self.config.get_current_project():
            filters["project_id"] = self.config.get_current_project()
        
        if status is not None:
            filters["status"] = status
        
        if exclude_status is not None:
            filters["exclude_status"] = exclude_status
        
        if priority is not None:
            filters["priority"] = priority
        
        if tags:
            filters["tags"] = tags
        
        return self.db.list_tasks(filters=filters, sort_by=sort_by, limit=limit)
    
    def get_next_task(self, assignee: Optional[str] = None, project_id: Optional[str] = None) -> Optional[Task]:
        """Get the next task in the queue."""
        # Use default assignee if none provided
        if assignee is None:
            assignee = self.config.get_default_assignee()
            
        # Use current project if none provided
        if project_id is None:
            project_id = self.config.get_current_project()
        
        # Exclude completed and canceled states
        exclude_states = [
            self.config.fixed_states["completed"],
            self.config.fixed_states["canceled"]
        ]
        
        return self.db.get_next_task(assignee=assignee, project_id=project_id, exclude_states=exclude_states)
    
    def advance_task(self, task_id: str) -> Dict[str, Any]:
        """Advance a task to the next state."""
        task = self.db.get_task(task_id)
        if not task:
            return {"success": False, "error": "Task not found"}
        
        # Get next state
        next_state = self.config.get_next_state(task.status)
        if not next_state:
            return {
                "success": False,
                "error": f"No next state available for {task.status}"
            }
        
        old_state = task.status
        task.advance_status(next_state)
        
        # Check if advancing from TODO to READY/DOING
        # Record current file count for strict file reference mode
        if (old_state == TaskStatus.TODO.value and 
            next_state == TaskStatus.READY.value):
            # Count current files associated with the task
            file_count = self._count_task_files(task_id)
            # Update task with work_started_file_count
            task.work_started_file_count = file_count
            # Debug logging
            import os
            if os.getenv('DEBUG_STRICT'):
                print(f"[DEBUG] Setting work_started_file_count = {file_count} for task {task_id}")
        
        # Save to database
        self.db.update_task(task)
        
        # Log the status change
        log_entry = LogEntry.create_task_log(
            task_id=task_id,
            entry_type=LogEntryType.STATUS_CHANGED,
            message=f"Status changed: {old_state} → {next_state}",
            user=task.assignee,
            metadata={"old_state": old_state, "new_state": next_state}
        )
        self.db.add_log_entry(log_entry)
        
        return {
            "success": True,
            "old_state": old_state,
            "new_state": next_state
        }
    
    def assign_task(self, task_id: str, assignee: str) -> Optional[Task]:
        """Assign a task to someone."""
        task = self.db.get_task(task_id)
        if not task:
            return None
        
        old_assignee = task.assignee
        task.assignee = assignee
        task.updated_at = datetime.now()
        
        # Save to database
        updated_task = self.db.update_task(task)
        
        # Log the assignment change
        log_entry = LogEntry.create_task_log(
            task_id=task_id,
            entry_type=LogEntryType.ASSIGNEE_CHANGED,
            message=f"Assignee changed: {old_assignee} → {assignee}",
            user=assignee,
            metadata={"old_assignee": old_assignee, "new_assignee": assignee}
        )
        self.db.add_log_entry(log_entry)
        
        return updated_task
    
    def link_tasks(self, parent_id: str, child_id: str,
                  relationship_type: RelationshipType = RelationshipType.PARENT_CHILD) -> TaskRelationship:
        """Create a relationship between tasks."""
        relationship = TaskRelationship(
            parent_id=parent_id,
            child_id=child_id,
            relationship_type=relationship_type
        )
        
        # Save to database
        created_relationship = self.db.create_relationship(relationship)
        
        # Log the relationship creation
        log_entry = LogEntry(
            entry_type=LogEntryType.RELATIONSHIP_CREATED,
            message=f"Relationship created: {parent_id} → {child_id} ({relationship_type})",
            metadata={
                "parent_id": parent_id,
                "child_id": child_id,
                "relationship_type": relationship_type
            }
        )
        self.db.add_log_entry(log_entry)
        
        return created_relationship
    
    def attach_file(self, task_id: str, file_path: str) -> FileAssociation:
        """Attach a file to a task."""
        association = FileAssociation(
            task_id=task_id,
            file_path=file_path
        )
        
        # Update file info from filesystem
        association.update_file_info()
        
        # Save to database
        created_association = self.db.add_file_association(association)
        
        # Log the file attachment
        log_entry = LogEntry.create_task_log(
            task_id=task_id,
            entry_type=LogEntryType.FILE_ADDED,
            message=f"File attached: {file_path}",
            metadata={"file_path": file_path, "file_type": association.file_type}
        )
        self.db.add_log_entry(log_entry)
        
        return created_association
    
    def add_log(self, task_id: str, message: str,
               user: Optional[str] = None) -> LogEntry:
        """Add a custom log entry for a task."""
        log_entry = LogEntry.create_task_log(
            task_id=task_id,
            entry_type=LogEntryType.USER_ACTION,
            message=message,
            user=user or self.config.get_default_assignee()
        )
        
        return self.db.add_log_entry(log_entry)
    
    def get_task_logs(self, task_id: str, limit: int = 100) -> List[LogEntry]:
        """Get log entries for a task."""
        return self.db.get_log_entries(task_id=task_id, limit=limit)
    
    def _count_task_files(self, task_id: str) -> int:
        """Count the number of files associated with a task."""
        try:
            # Count from file_associations table
            if hasattr(self.db, 'db_type') and self.db.db_type == 'postgresql':
                cursor = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM file_associations WHERE task_id = %s",
                    [task_id]
                )
            else:
                cursor = self.db.execute_query(
                    "SELECT COUNT(*) as count FROM file_associations WHERE task_id = ?",
                    [task_id]
                )
            
            result = cursor.fetchone()
            if result:
                if hasattr(result, 'get'):
                    file_count = result.get('count', 0)
                else:
                    file_count = result[0] if result else 0
            else:
                file_count = 0
            
            # Also check task_files table if it exists
            try:
                if hasattr(self.db, 'db_type') and self.db.db_type == 'postgresql':
                    cursor = self.db.execute_query(
                        "SELECT COUNT(*) as count FROM task_files WHERE task_id = %s",
                        [task_id]
                    )
                else:
                    cursor = self.db.execute_query(
                        "SELECT COUNT(*) as count FROM task_files WHERE task_id = ?",
                        [task_id]
                    )
                
                result = cursor.fetchone()
                if result:
                    if hasattr(result, 'get'):
                        file_count += result.get('count', 0)
                    else:
                        file_count += result[0] if result else 0
            except:
                # task_files table might not exist
                pass
            
            return file_count
        except Exception:
            # If any error, return 0
            return 0
    
    def close_connection(self) -> None:
        """Close database connection."""
        if self.db:
            self.db.disconnect()
    
    def __enter__(self):
        """Context manager entry."""
        self.db.connect()
        # Ensure schema is initialized before any operations
        if hasattr(self.db, 'ensure_schema_initialized'):
            self.db.ensure_schema_initialized()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.db.disconnect()
        return False