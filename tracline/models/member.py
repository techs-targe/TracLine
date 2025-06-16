"""Team member models for TracLine."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class MemberRole(str, Enum):
    """Team member roles."""
    OWNER = "OWNER"
    PM = "PM"  # Project Manager
    TL = "TL"  # Tech Lead
    ENGINEER = "ENGINEER"
    DB = "DB"  # Database Engineer
    TESTER = "TESTER"
    DESIGNER = "DESIGNER"
    ANALYST = "ANALYST"
    OTHER = "OTHER"


class MemberPosition(str, Enum):
    """Organizational hierarchy positions."""
    LEADER = "LEADER"
    SUB_LEADER = "SUB_LEADER"
    MEMBER = "MEMBER"


@dataclass
class Member:
    """Team member model."""
    id: str  # Unique identifier (username or ID)
    name: str
    role: MemberRole = MemberRole.ENGINEER
    position: MemberPosition = MemberPosition.MEMBER
    age: Optional[int] = None
    sex: Optional[str] = None
    profile: Optional[str] = None
    leader_id: Optional[str] = None  # ID of their leader/manager
    profile_image_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def update(self, **kwargs):
        """Update member fields."""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "position": self.position,
            "age": self.age,
            "sex": self.sex,
            "profile": self.profile,
            "leader_id": self.leader_id,
            "profile_image_path": self.profile_image_path,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }