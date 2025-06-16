"""Task relationship model."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    """Types of task relationships."""
    PARENT_CHILD = "parent-child"
    BLOCKS = "blocks"
    RELATED = "related"
    DUPLICATE = "duplicate"
    REQUIREMENT_DESIGN = "requirement-design"
    DESIGN_IMPLEMENTATION = "design-implementation"
    IMPLEMENTATION_TEST = "implementation-test"


class TaskRelationship(BaseModel):
    """Task relationship model."""
    id: Optional[int] = Field(None, description="Relationship ID")
    parent_id: str = Field(..., description="Parent task ID")
    child_id: str = Field(..., description="Child task ID")
    relationship_type: RelationshipType = Field(
        default=RelationshipType.PARENT_CHILD,
        description="Type of relationship"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp"
    )
    created_by: Optional[str] = Field(None, description="User who created the relationship")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TaskRelationship':
        """Create from dictionary."""
        return cls(**data)