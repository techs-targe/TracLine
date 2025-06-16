"""Task model for TracLine."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHEST = 5


class TaskStatus(str, Enum):
    """Fixed task status values."""
    TODO = "TODO"
    READY = "READY"
    DONE = "DONE"
    PENDING = "PENDING"
    CANCELED = "CANCELED"


class Task(BaseModel):
    """Task model."""
    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: str = Field(default=TaskStatus.TODO, description="Current task status")
    assignee: Optional[str] = Field(None, description="Person assigned to the task")
    priority: int = Field(default=TaskPriority.MEDIUM, description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    project_id: Optional[str] = Field(None, description="Project this task belongs to")
    tags: List[str] = Field(default_factory=list, description="Task tags")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    order_num: int = Field(default=0, description="Order number for sorting")
    work_started_file_count: Optional[int] = Field(None, description="File count when work started (for strict mode)")
    
    # External integration fields
    external_id: Optional[str] = Field(None, description="External system ID")
    external_url: Optional[str] = Field(None, description="External system URL")
    sync_status: Optional[str] = Field(None, description="Synchronization status")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def advance_status(self, next_status: str) -> None:
        """Advance task to next status."""
        self.status = next_status
        self.updated_at = datetime.now()
        
        if next_status == TaskStatus.DONE:
            self.completed_at = datetime.now()
    
    def is_active(self) -> bool:
        """Check if task is in active state."""
        return self.status not in [TaskStatus.DONE, TaskStatus.CANCELED, TaskStatus.PENDING]
    
    def is_complete(self) -> bool:
        """Check if task is complete."""
        return self.status == TaskStatus.DONE
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """Create from dictionary."""
        return cls(**data)