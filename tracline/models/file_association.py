"""File association model."""

from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, validator


class FileAssociation(BaseModel):
    """File association model."""
    id: Optional[int] = Field(None, description="Association ID")
    task_id: str = Field(..., description="Associated task ID")
    file_path: str = Field(..., description="File path")
    relative_path: Optional[str] = Field(None, description="Relative path from project root")
    file_type: Optional[str] = Field(None, description="File type/extension")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp"
    )
    created_by: Optional[str] = Field(None, description="User who created the association")
    last_modified: Optional[datetime] = Field(None, description="File last modified time")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    
    @validator('file_path')
    def validate_file_path(cls, v):
        """Validate file path."""
        path = Path(v)
        if not path.is_absolute():
            raise ValueError("File path must be absolute")
        return str(path)
    
    @validator('file_type')
    def extract_file_type(cls, v, values):
        """Extract file type from path if not provided."""
        if v is None and 'file_path' in values:
            path = Path(values['file_path'])
            return path.suffix.lstrip('.')
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def update_file_info(self) -> None:
        """Update file information from filesystem."""
        path = Path(self.file_path)
        if path.exists():
            stat = path.stat()
            self.last_modified = datetime.fromtimestamp(stat.st_mtime)
            self.file_size = stat.st_size
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.dict()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FileAssociation':
        """Create from dictionary."""
        return cls(**data)