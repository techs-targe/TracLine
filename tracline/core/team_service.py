"""Team management service for TracLine."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from tracline.core.config import Config
from tracline.db import DatabaseInterface, DatabaseFactory
from tracline.models import (
    Member, MemberRole, MemberPosition,
    Project, ProjectMembership,
    LogEntry, LogEntryType
)


class TeamService:
    """Service layer for team operations."""
    
    def __init__(self, config: Config, db: Optional[DatabaseInterface] = None):
        self.config = config
        self.db = db or DatabaseFactory.create(config.get_database_config())
    
    # Member operations
    def create_member(self, member_id: str, name: str,
                     role: MemberRole = MemberRole.ENGINEER,
                     position: MemberPosition = MemberPosition.MEMBER,
                     age: Optional[int] = None,
                     sex: Optional[str] = None,
                     profile: Optional[str] = None,
                     leader_id: Optional[str] = None,
                     profile_image_path: Optional[str] = None) -> Member:
        """Create a new team member."""
        member = Member(
            id=member_id,
            name=name,
            role=role,
            position=position,
            age=age,
            sex=sex,
            profile=profile,
            leader_id=leader_id,
            profile_image_path=profile_image_path
        )
        
        created_member = self.db.create_member(member)
        
        # Log the creation
        log_entry = LogEntry(
            entry_type=LogEntryType.USER_ACTION,
            message=f"Member '{name}' created",
            user=self.config.get_default_assignee(),
            metadata={"member_id": member_id, "role": role}
        )
        self.db.add_log_entry(log_entry)
        
        return created_member
    
    def get_member(self, member_id: str) -> Optional[Member]:
        """Get a member by ID."""
        return self.db.get_member(member_id)
    
    def update_member(self, member_id: str, **kwargs) -> Optional[Member]:
        """Update a member."""
        member = self.db.get_member(member_id)
        if not member:
            return None
        
        member.update(**kwargs)
        updated_member = self.db.update_member(member)
        
        # Log the update
        log_entry = LogEntry(
            entry_type=LogEntryType.USER_ACTION,
            message=f"Member '{member.name}' updated",
            user=self.config.get_default_assignee(),
            metadata={"member_id": member_id, "changes": kwargs}
        )
        self.db.add_log_entry(log_entry)
        
        return updated_member
    
    def delete_member(self, member_id: str) -> bool:
        """Delete a member."""
        member = self.db.get_member(member_id)
        if not member:
            return False
        
        if self.db.delete_member(member_id):
            # Log the deletion
            log_entry = LogEntry(
                entry_type=LogEntryType.USER_ACTION,
                message=f"Member '{member.name}' deleted",
                user=self.config.get_default_assignee(),
                metadata={"member_id": member_id}
            )
            self.db.add_log_entry(log_entry)
            return True
        
        return False
    
    def list_members(self, filters: Dict[str, Any] = None) -> List[Member]:
        """List members with filtering."""
        return self.db.list_members(filters=filters)
    
    def change_position(self, member_id: str, new_position: MemberPosition) -> Optional[Member]:
        """Change a member's organizational position."""
        member = self.db.get_member(member_id)
        if not member:
            return None
        
        old_position = member.position
        member.position = new_position
        member.updated_at = datetime.now()
        
        updated_member = self.db.update_member(member)
        
        # Log the position change
        log_entry = LogEntry(
            entry_type=LogEntryType.USER_ACTION,
            message=f"Position changed: {old_position} → {new_position}",
            user=self.config.get_default_assignee(),
            metadata={"member_id": member_id, "old_position": old_position, "new_position": new_position}
        )
        self.db.add_log_entry(log_entry)
        
        return updated_member
    
    def change_leader(self, member_id: str, new_leader_id: Optional[str]) -> Optional[Member]:
        """Change a member's leader/manager."""
        member = self.db.get_member(member_id)
        if not member:
            return None
        
        old_leader_id = member.leader_id
        member.leader_id = new_leader_id
        member.updated_at = datetime.now()
        
        updated_member = self.db.update_member(member)
        
        # Log the leader change
        log_entry = LogEntry(
            entry_type=LogEntryType.USER_ACTION,
            message=f"Leader changed: {old_leader_id} → {new_leader_id}",
            user=self.config.get_default_assignee(),
            metadata={"member_id": member_id, "old_leader": old_leader_id, "new_leader": new_leader_id}
        )
        self.db.add_log_entry(log_entry)
        
        return updated_member
    
    def get_team_structure(self, leader_id: str) -> Dict[str, Any]:
        """Get the hierarchical team structure under a leader."""
        leader = self.db.get_member(leader_id)
        if not leader:
            return {}
        
        def build_hierarchy(member_id: str) -> Dict[str, Any]:
            member = self.db.get_member(member_id)
            if not member:
                return {}
            
            # Get direct reports
            direct_reports = self.db.list_members(filters={"leader_id": member_id})
            
            hierarchy = {
                "id": member.id,
                "name": member.name,
                "role": member.role,
                "position": member.position,
                "direct_reports": []
            }
            
            for report in direct_reports:
                hierarchy["direct_reports"].append(build_hierarchy(report.id))
            
            return hierarchy
        
        return build_hierarchy(leader_id)
    
    # Project operations
    def create_project(self, project_id: str, name: str,
                      description: Optional[str] = None,
                      owner_id: Optional[str] = None) -> Project:
        """Create a new project."""
        project = Project(
            id=project_id,
            name=name,
            description=description,
            owner_id=owner_id
        )
        
        created_project = self.db.create_project(project)
        
        # Log the creation
        log_entry = LogEntry(
            entry_type=LogEntryType.USER_ACTION,
            message=f"Project '{name}' created",
            user=self.config.get_default_assignee(),
            metadata={"project_id": project_id}
        )
        self.db.add_log_entry(log_entry)
        
        return created_project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        return self.db.get_project(project_id)
    
    def update_project(self, project_id: str, **kwargs) -> Optional[Project]:
        """Update a project."""
        project = self.db.get_project(project_id)
        if not project:
            return None
        
        project.update(**kwargs)
        updated_project = self.db.update_project(project)
        
        # Log the update
        log_entry = LogEntry(
            entry_type=LogEntryType.USER_ACTION,
            message=f"Project '{project.name}' updated",
            user=self.config.get_default_assignee(),
            metadata={"project_id": project_id, "changes": kwargs}
        )
        self.db.add_log_entry(log_entry)
        
        return updated_project
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        project = self.db.get_project(project_id)
        if not project:
            return False
        
        if self.db.delete_project(project_id):
            # Log the deletion
            log_entry = LogEntry(
                entry_type=LogEntryType.USER_ACTION,
                message=f"Project '{project.name}' deleted",
                user=self.config.get_default_assignee(),
                metadata={"project_id": project_id}
            )
            self.db.add_log_entry(log_entry)
            return True
        
        return False
    
    def list_projects(self, filters: Dict[str, Any] = None) -> List[Project]:
        """List projects with filtering."""
        return self.db.list_projects(filters=filters)
    
    # Project membership operations
    def add_project_member(self, project_id: str, member_id: str) -> ProjectMembership:
        """Add a member to a project."""
        # Verify project and member exist
        project = self.db.get_project(project_id)
        member = self.db.get_member(member_id)
        
        if not project or not member:
            raise ValueError("Project or member not found")
        
        membership = ProjectMembership(
            project_id=project_id,
            member_id=member_id
        )
        
        created_membership = self.db.add_project_member(membership)
        
        # Log the addition
        log_entry = LogEntry(
            entry_type=LogEntryType.USER_ACTION,
            message=f"Member '{member.name}' added to project '{project.name}'",
            user=self.config.get_default_assignee(),
            metadata={"project_id": project_id, "member_id": member_id}
        )
        self.db.add_log_entry(log_entry)
        
        return created_membership
    
    def remove_project_member(self, project_id: str, member_id: str) -> bool:
        """Remove a member from a project."""
        # Verify project and member exist
        project = self.db.get_project(project_id)
        member = self.db.get_member(member_id)
        
        if not project or not member:
            return False
        
        if self.db.remove_project_member(project_id, member_id):
            # Log the removal
            log_entry = LogEntry(
                entry_type=LogEntryType.USER_ACTION,
                message=f"Member '{member.name}' removed from project '{project.name}'",
                user=self.config.get_default_assignee(),
                metadata={"project_id": project_id, "member_id": member_id}
            )
            self.db.add_log_entry(log_entry)
            return True
        
        return False
    
    def get_project_members(self, project_id: str) -> List[Member]:
        """Get all members of a project."""
        return self.db.get_project_members(project_id)
    
    def get_member_projects(self, member_id: str) -> List[Project]:
        """Get all projects a member belongs to."""
        return self.db.get_member_projects(member_id)
    
    def __enter__(self):
        """Context manager entry."""
        self.db.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.db.disconnect()
        return False