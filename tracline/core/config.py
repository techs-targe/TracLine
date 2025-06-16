"""Configuration management for TracLine."""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class DatabaseConfig(BaseModel):
    """Database configuration."""
    type: str = Field(default="postgresql")
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="tracline")
    user: str = Field(default="postgres")
    password: Optional[str] = None
    url: Optional[str] = None
    path: Optional[str] = None  # For SQLite databases


class WorkflowConfig(BaseModel):
    """Workflow configuration."""
    custom_states: List[str] = Field(default_factory=lambda: ["DOING", "TESTING"])
    transitions: Dict[str, List[str]] = Field(default_factory=dict)


class DefaultsConfig(BaseModel):
    """Default values configuration."""
    assignee: Optional[str] = None
    project: Optional[str] = None
    priority: int = Field(default=3)


class TracLineConfig(BaseModel):
    """Main configuration model."""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)


class Config:
    """Configuration manager for TracLine."""
    
    def __init__(self, config_path: Optional[str] = None):
        load_dotenv()
        
        # Set up configuration paths
        self.config_path = config_path or os.getenv(
            "TRACLINE_CONFIG",
            self._get_default_config_path()
        )
        
        # Load configuration
        self.config = self._load_config()
        
        # Apply environment variable overrides
        self._apply_env_overrides()
        
        # Fixed states
        self.fixed_states = {
            "initial": "TODO",
            "ready": "READY",
            "completed": "DONE",
            "pending": "PENDING",
            "canceled": "CANCELED"
        }
    
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Check current directory first
        local_config = Path("tracline.yaml")
        if local_config.exists():
            return str(local_config)
        
        # Legacy support - check for old taskshell.yaml
        legacy_config = Path("taskshell.yaml")
        if legacy_config.exists():
            return str(legacy_config)
        
        # Check home directory - try tracline.yaml first (what installers create)
        home_tracline = Path.home() / ".tracline" / "tracline.yaml"
        if home_tracline.exists():
            return str(home_tracline)
            
        # Then try config.yaml for backward compatibility
        home_config = Path.home() / ".tracline" / "config.yaml"
        if home_config.exists():
            return str(home_config)
            
        # Default to the standard location (what installers create)
        return str(home_tracline)
    
    def _load_config(self) -> TracLineConfig:
        """Load configuration from file."""
        config_path = Path(self.config_path)
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                return TracLineConfig(**data)
        
        # Return default configuration
        return TracLineConfig()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # Database overrides
        if db_type := os.getenv("TRACLINE_DB_TYPE"):
            self.config.database.type = db_type
        
        if db_url := os.getenv("TRACLINE_DB_URL"):
            self.config.database.url = db_url
        
        if db_password := os.getenv("TRACLINE_DB_PASSWORD"):
            self.config.database.password = db_password
        
        # Default assignee (support both TRACLINE_ASSIGNEE and TASK_ASSIGNEE)
        if assignee := os.getenv("TRACLINE_ASSIGNEE"):
            self.config.defaults.assignee = assignee
        elif assignee := os.getenv("TASK_ASSIGNEE"):
            self.config.defaults.assignee = assignee
            
        # Current project
        if project := os.getenv("TRACLINE_PROJECT"):
            self.config.defaults.project = project
        # Also check TRACLINE_PROJECT_ID (takes precedence)
        if project_id := os.getenv("TRACLINE_PROJECT_ID"):
            self.config.defaults.project = project_id
    
    def get_default_assignee(self) -> Optional[str]:
        """Get the default assignee from config or environment."""
        return self.config.defaults.assignee
        
    def get_current_project(self) -> Optional[str]:
        """Get the current project from config or environment."""
        return self.config.defaults.project
        
    def set_current_project(self, project_id: str) -> None:
        """Set the current project and save to config."""
        self.config.defaults.project = project_id
        self.save_config()
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.config.database
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Get workflow configuration."""
        return self.config.workflow
    
    def get_all_states(self) -> List[str]:
        """Get all available states in order."""
        states = [self.fixed_states["initial"], self.fixed_states["ready"]]
        states.extend(self.config.workflow.custom_states)
        states.extend([
            self.fixed_states["completed"],
            self.fixed_states["pending"],
            self.fixed_states["canceled"]
        ])
        return states
    
    def get_active_states(self) -> List[str]:
        """Get states that represent active work."""
        states = [self.fixed_states["ready"]]
        states.extend(self.config.workflow.custom_states)
        return states
    
    def get_next_state(self, current_state: str) -> Optional[str]:
        """Get the next state in the workflow."""
        transitions = self.config.workflow.transitions
        
        # Check custom transitions first
        if current_state in transitions:
            next_states = transitions[current_state]
            # Ensure next_states is a list and not empty
            if isinstance(next_states, list) and len(next_states) > 0:
                return next_states[0]
        
        # Default workflow progression
        all_states = self.get_all_states()
        try:
            current_idx = all_states.index(current_state)
            # Find next non-terminal state
            for i in range(current_idx + 1, len(all_states)):
                next_state = all_states[i]
                if next_state not in [self.fixed_states["pending"], 
                                     self.fixed_states["canceled"]]:
                    return next_state
        except ValueError:
            pass
        
        return None
    
    def get_project_strict_settings(self, project_id: str) -> Dict[str, bool]:
        """Get strict mode settings for a project from environment variables.
        
        Environment variables:
        - TRACLINE_STRICT_DOC_READ_<PROJECT_ID>: Enable/disable document read enforcement
        - TRACLINE_STRICT_FILE_REF_<PROJECT_ID>: Enable/disable file reference enforcement
        - TRACLINE_STRICT_LOG_ENTRY_<PROJECT_ID>: Enable/disable log entry enforcement
        
        If project-specific env vars are not set, check global ones:
        - TRACLINE_STRICT_DOC_READ: Global document read enforcement
        - TRACLINE_STRICT_FILE_REF: Global file reference enforcement
        - TRACLINE_STRICT_LOG_ENTRY: Global log entry enforcement
        """
        settings = {}
        
        # Convert project ID to uppercase and replace special chars for env var names
        env_project_id = project_id.upper().replace('-', '_').replace(' ', '_')
        
        # Check project-specific settings first, then global
        strict_doc_read = os.getenv(f"TRACLINE_STRICT_DOC_READ_{env_project_id}")
        if strict_doc_read is None:
            strict_doc_read = os.getenv("TRACLINE_STRICT_DOC_READ")
        if strict_doc_read is not None:
            settings['strict_doc_read'] = strict_doc_read.lower() in ('true', '1', 'yes', 'on')
        
        strict_file_ref = os.getenv(f"TRACLINE_STRICT_FILE_REF_{env_project_id}")
        if strict_file_ref is None:
            strict_file_ref = os.getenv("TRACLINE_STRICT_FILE_REF")
        if strict_file_ref is not None:
            settings['strict_file_ref'] = strict_file_ref.lower() in ('true', '1', 'yes', 'on')
        
        strict_log_entry = os.getenv(f"TRACLINE_STRICT_LOG_ENTRY_{env_project_id}")
        if strict_log_entry is None:
            strict_log_entry = os.getenv("TRACLINE_STRICT_LOG_ENTRY")
        if strict_log_entry is not None:
            settings['strict_log_entry'] = strict_log_entry.lower() in ('true', '1', 'yes', 'on')
        
        return settings
    
    def save_config(self):
        """Save configuration to file."""
        config_path = Path(self.config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(self.config.dict(), f, default_flow_style=False)