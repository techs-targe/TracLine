"""Log entry model."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Log levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class LogEntryType(str, Enum):
    """Types of log entries."""
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    STATUS_CHANGED = "status_changed"
    ASSIGNEE_CHANGED = "assignee_changed"
    FILE_ADDED = "file_added"
    FILE_REMOVED = "file_removed"
    RELATIONSHIP_CREATED = "relationship_created"
    RELATIONSHIP_DELETED = "relationship_deleted"
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    SYSTEM_EVENT = "system_event"
    USER_ACTION = "user_action"


class LogEntry(BaseModel):
    """Log entry model."""
    id: Optional[int] = Field(None, description="Log entry ID")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Log timestamp"
    )
    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Log level"
    )
    entry_type: LogEntryType = Field(
        ...,
        description="Type of log entry"
    )
    message: str = Field(
        ...,
        description="Log message"
    )
    task_id: Optional[str] = Field(
        None,
        description="Related task ID"
    )
    user: Optional[str] = Field(
        None,
        description="User who triggered the action"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LogEntry':
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def create_task_log(cls, task_id: str, entry_type: LogEntryType, 
                       message: str, user: Optional[str] = None,
                       **metadata) -> 'LogEntry':
        """Create a task-related log entry."""
        return cls(
            entry_type=entry_type,
            message=message,
            task_id=task_id,
            user=user,
            metadata=metadata
        )