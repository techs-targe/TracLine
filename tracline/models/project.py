"""Project models for TracLine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class Project:
    """Project model."""
    id: str  # Unique project ID
    name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None  # Member ID of project owner
    status: str = "ACTIVE"  # ACTIVE, COMPLETED, ARCHIVED, CANCELLED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update(self, **kwargs):
        """Update project fields."""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ProjectMembership:
    """Project membership relationship."""
    project_id: str
    member_id: str
    joined_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "member_id": self.member_id,
            "joined_at": self.joined_at.isoformat()
        }