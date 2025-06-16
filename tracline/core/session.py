"""Session management for TracLine."""

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


class SessionManager:
    """Manages current task session."""
    
    def __init__(self):
        self.session_dir = Path.home() / ".tracline"
        self.session_file = self.session_dir / "session.json"
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    def set_current_task(self, task_id: str) -> None:
        """Set the current task being worked on."""
        data = {
            'current_task': task_id,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.session_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_current_task(self) -> Optional[str]:
        """Get the current task being worked on."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    return data.get('current_task')
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def clear_current_task(self) -> None:
        """Clear the current task."""
        if self.session_file.exists():
            self.session_file.unlink()
    
    def get_session_info(self) -> dict:
        """Get full session information."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def update_session(self, data: dict) -> None:
        """Update session with additional data."""
        current_data = self.get_session_info()
        current_data.update(data)
        current_data['last_updated'] = datetime.now().isoformat()
        
        with open(self.session_file, 'w') as f:
            json.dump(current_data, f, indent=2)