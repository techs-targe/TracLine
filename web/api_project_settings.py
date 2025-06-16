"""Project settings API endpoints for TracLine Web."""

from fastapi import HTTPException
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def register_project_settings_endpoints(app, task_service):
    """Register project settings endpoints to the FastAPI app."""
    
    @app.get("/api/projects/{project_id}/settings")
    async def get_project_settings(project_id: str):
        """Get project settings including strict mode configurations."""
        try:
            with task_service.db as db:
                # Get project settings
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    query = """SELECT strict_doc_read, strict_file_ref, strict_log_entry, 
                              github_enabled, github_repo, monitor_enabled, monitor_interval
                       FROM project_settings 
                       WHERE project_id = %s"""
                    params = [project_id]
                else:
                    query = """SELECT strict_doc_read, strict_file_ref, strict_log_entry, 
                              github_enabled, github_repo, monitor_enabled, monitor_interval
                       FROM project_settings 
                       WHERE project_id = ?"""
                    params = [project_id]
                
                cursor = db.execute_query(query, params)
                
                row = cursor.fetchone()
                
                if row:
                    # Handle both dict and tuple returns
                    if isinstance(row, dict):
                        settings = {
                            'project_id': project_id,
                            'strict_doc_read': bool(row.get('strict_doc_read', False)),
                            'strict_file_ref': bool(row.get('strict_file_ref', False)),
                            'strict_log_entry': bool(row.get('strict_log_entry', False)),
                            'github_enabled': bool(row.get('github_enabled', False)),
                            'github_repo': row.get('github_repo', ''),
                            'monitor_enabled': bool(row.get('monitor_enabled', False)),
                            'monitor_interval': row.get('monitor_interval', 60)
                        }
                    else:
                        # SQLite returns tuples
                        settings = {
                            'project_id': project_id,
                            'strict_doc_read': bool(row[0]) if row[0] is not None else False,
                            'strict_file_ref': bool(row[1]) if row[1] is not None else False,
                            'strict_log_entry': bool(row[2]) if row[2] is not None else False,
                            'github_enabled': bool(row[3]) if row[3] is not None else False,
                            'github_repo': row[4] if row[4] is not None else '',
                            'monitor_enabled': bool(row[5]) if row[5] is not None else False,
                            'monitor_interval': row[6] if row[6] is not None else 60
                        }
                else:
                    # Return default settings if none exist
                    settings = {
                        'project_id': project_id,
                        'strict_doc_read': False,
                        'strict_file_ref': False,
                        'strict_log_entry': False,
                        'github_enabled': False,
                        'github_repo': '',
                        'monitor_enabled': False,
                        'monitor_interval': 60
                    }
                
                return settings
                
        except Exception as e:
            logger.error(f"Error getting project settings: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.put("/api/projects/{project_id}/settings")
    async def update_project_settings(project_id: str, settings: Dict[str, Any]):
        """Update project settings including strict mode configurations."""
        try:
            with task_service.db as db:
                # Check if settings exist
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    query = "SELECT project_id FROM project_settings WHERE project_id = %s"
                else:
                    query = "SELECT project_id FROM project_settings WHERE project_id = ?"
                
                cursor = db.execute_query(query, [project_id])
                
                exists = cursor.fetchone() is not None
                
                if exists:
                    # Update existing settings
                    update_fields = []
                    update_values = []
                    
                    # Handle strict mode settings
                    placeholder = '%s' if hasattr(db, 'db_type') and db.db_type == 'postgresql' else '?'
                    
                    if 'strict_doc_read' in settings:
                        update_fields.append(f"strict_doc_read = {placeholder}")
                        update_values.append(1 if settings['strict_doc_read'] else 0)
                    
                    if 'strict_file_ref' in settings:
                        update_fields.append(f"strict_file_ref = {placeholder}")
                        update_values.append(1 if settings['strict_file_ref'] else 0)
                    
                    if 'strict_log_entry' in settings:
                        update_fields.append(f"strict_log_entry = {placeholder}")
                        update_values.append(1 if settings['strict_log_entry'] else 0)
                    
                    # Handle other settings
                    if 'github_enabled' in settings:
                        update_fields.append(f"github_enabled = {placeholder}")
                        update_values.append(1 if settings['github_enabled'] else 0)
                    
                    if 'github_repo' in settings:
                        update_fields.append(f"github_repo = {placeholder}")
                        update_values.append(settings['github_repo'])
                    
                    if 'monitor_enabled' in settings:
                        update_fields.append(f"monitor_enabled = {placeholder}")
                        update_values.append(1 if settings['monitor_enabled'] else 0)
                    
                    if 'monitor_interval' in settings:
                        update_fields.append(f"monitor_interval = {placeholder}")
                        update_values.append(settings['monitor_interval'])
                    
                    if update_fields:
                        update_values.append(project_id)
                        query = f"UPDATE project_settings SET {', '.join(update_fields)} WHERE project_id = {placeholder}"
                        db.execute_query(query, update_values)
                else:
                    # Insert new settings
                    from datetime import datetime
                    
                    placeholder = '%s' if hasattr(db, 'db_type') and db.db_type == 'postgresql' else '?'
                    placeholders = ', '.join([placeholder] * 9)
                    
                    db.execute_query(
                        f"""INSERT INTO project_settings 
                           (project_id, strict_doc_read, strict_file_ref, strict_log_entry, 
                            github_enabled, github_repo, monitor_enabled, monitor_interval, created_at)
                           VALUES ({placeholders})""",
                        [
                            project_id,
                            1 if settings.get('strict_doc_read', False) else 0,
                            1 if settings.get('strict_file_ref', False) else 0,
                            1 if settings.get('strict_log_entry', False) else 0,
                            1 if settings.get('github_enabled', False) else 0,
                            settings.get('github_repo', ''),
                            1 if settings.get('monitor_enabled', False) else 0,
                            settings.get('monitor_interval', 60),
                            datetime.now().isoformat()
                        ]
                    )
                
                # Commit changes
                if hasattr(db, 'conn') and hasattr(db.conn, 'commit'):
                    db.conn.commit()
                
                return {"status": "success", "message": "Settings updated successfully"}
                
        except Exception as e:
            logger.error(f"Error updating project settings: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.get("/api/projects/{project_id}/settings/strict-mode")
    async def get_strict_mode_settings(project_id: str):
        """Get only strict mode settings for a project."""
        try:
            settings = await get_project_settings(project_id)
            return {
                'project_id': project_id,
                'strict_doc_read': settings['strict_doc_read'],
                'strict_file_ref': settings['strict_file_ref'],
                'strict_log_entry': settings['strict_log_entry']
            }
        except Exception as e:
            logger.error(f"Error getting strict mode settings: {e}")
            raise HTTPException(status_code=500, detail=str(e))