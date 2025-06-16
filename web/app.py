"""Web interface for TracLine - FIXED VERSION."""

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import os
from typing import List, Optional, Dict, Any
import uvicorn
from datetime import datetime
import logging

# Setup logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder for datetime objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Custom JSONResponse that uses the CustomJSONEncoder
class CustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

# Create FastAPI app
app = FastAPI(title="TracLine Web Interface", default_response_class=CustomJSONResponse)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get current file directory
current_dir = Path(__file__).parent.absolute()

# Mount static files
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")

# Templates
templates = Jinja2Templates(directory=current_dir / "templates")

# IMPORTANT: Define critical API endpoints FIRST before any complex imports

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API is working."""
    return {"status": "ok", "timestamp": datetime.now()}

@app.get("/api/projects/{project_id}/settings")
async def get_project_settings(project_id: str):
    """Get project settings including strict mode configurations."""
    logger.info(f"[SETTINGS API] Getting settings for project: {project_id}")
    
    try:
        # For now, return default settings to ensure endpoint works
        settings = {
            'project_id': project_id,
            'strict_doc_read': False,
            'strict_file_ref': False,
            'strict_log_entry': False,
            'github_enabled': False,
            'github_repo': '',
            'monitor_enabled': False,
            'monitor_interval': 60,
            'project_root': ''
        }
        
        # Try to get from database if available
        try:
            from tracline.core.config import Config
            from tracline.db.factory import DatabaseFactory
            
            config = Config()
            db = DatabaseFactory.create(config.config.database)
            db.connect()
            
            # Get settings from database
            if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                query = """SELECT strict_doc_read, strict_file_ref, strict_log_entry, 
                          github_enabled, github_repo, monitor_enabled, monitor_interval, project_root
                   FROM project_settings 
                   WHERE project_id = %s"""
                params = [project_id]
            else:
                query = """SELECT strict_doc_read, strict_file_ref, strict_log_entry, 
                          github_enabled, github_repo, monitor_enabled, monitor_interval, project_root
                   FROM project_settings 
                   WHERE project_id = ?"""
                params = [project_id]
            
            cursor = db.execute_query(query, params)
            row = cursor.fetchone()
            
            if row:
                if isinstance(row, dict):
                    settings.update({
                        'strict_doc_read': bool(row.get('strict_doc_read', False)),
                        'strict_file_ref': bool(row.get('strict_file_ref', False)),
                        'strict_log_entry': bool(row.get('strict_log_entry', False)),
                        'github_enabled': bool(row.get('github_enabled', False)),
                        'github_repo': row.get('github_repo', ''),
                        'monitor_enabled': bool(row.get('monitor_enabled', False)),
                        'monitor_interval': row.get('monitor_interval', 60),
                        'project_root': row.get('project_root', '')
                    })
                else:
                    # SQLite returns tuples
                    settings.update({
                        'strict_doc_read': bool(row[0]) if row[0] is not None else False,
                        'strict_file_ref': bool(row[1]) if row[1] is not None else False,
                        'strict_log_entry': bool(row[2]) if row[2] is not None else False,
                        'github_enabled': bool(row[3]) if row[3] is not None else False,
                        'github_repo': row[4] if row[4] is not None else '',
                        'monitor_enabled': bool(row[5]) if row[5] is not None else False,
                        'monitor_interval': row[6] if row[6] is not None else 60,
                        'project_root': row[7] if row[7] is not None else ''
                    })
                    
            db.disconnect()
            
        except Exception as e:
            logger.warning(f"Could not get settings from database: {e}")
            # Return default settings
        
        return settings
        
    except Exception as e:
        logger.error(f"Error in get_project_settings: {e}")
        return settings

@app.put("/api/projects/{project_id}/settings")
async def update_project_settings(project_id: str, settings: Dict[str, Any]):
    """Update project settings."""
    logger.info(f"[SETTINGS API] Updating settings for project: {project_id}")
    logger.info(f"Settings to save: {settings}")
    
    try:
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # First check if settings exist for this project
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            # Check if record exists
            check_query = "SELECT project_id FROM project_settings WHERE project_id = %s"
            cursor = db.execute_query(check_query, [project_id])
            exists = cursor.fetchone() is not None
            
            if exists:
                # Update existing settings
                from datetime import datetime
                now = datetime.utcnow().isoformat()
                update_query = """UPDATE project_settings 
                                SET strict_doc_read = %s, strict_file_ref = %s, strict_log_entry = %s,
                                    github_enabled = %s, github_repo = %s, 
                                    monitor_enabled = %s, monitor_interval = %s, project_root = %s,
                                    updated_at = %s
                                WHERE project_id = %s"""
                params = [
                    settings.get('strict_doc_read', False),
                    settings.get('strict_file_ref', False),
                    settings.get('strict_log_entry', False),
                    settings.get('github_enabled', False),
                    settings.get('github_repo', ''),
                    settings.get('monitor_enabled', False),
                    settings.get('monitor_interval', 60),
                    settings.get('project_root', ''),
                    now,
                    project_id
                ]
            else:
                # Insert new settings
                from datetime import datetime
                now = datetime.utcnow().isoformat()
                update_query = """INSERT INTO project_settings 
                                (project_id, strict_doc_read, strict_file_ref, strict_log_entry,
                                 github_enabled, github_repo, monitor_enabled, monitor_interval, project_root,
                                 created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                params = [
                    project_id,
                    settings.get('strict_doc_read', False),
                    settings.get('strict_file_ref', False),
                    settings.get('strict_log_entry', False),
                    settings.get('github_enabled', False),
                    settings.get('github_repo', ''),
                    settings.get('monitor_enabled', False),
                    settings.get('monitor_interval', 60),
                    settings.get('project_root', ''),
                    now,
                    now
                ]
            
            db.execute_query(update_query, params)
            if hasattr(db, 'conn'):
                db.conn.commit()
            
        else:
            # SQLite
            check_query = "SELECT project_id FROM project_settings WHERE project_id = ?"
            cursor = db.execute_query(check_query, [project_id])
            exists = cursor.fetchone() is not None
            
            if exists:
                from datetime import datetime
                now = datetime.utcnow().isoformat()
                update_query = """UPDATE project_settings 
                                SET strict_doc_read = ?, strict_file_ref = ?, strict_log_entry = ?,
                                    github_enabled = ?, github_repo = ?, 
                                    monitor_enabled = ?, monitor_interval = ?, project_root = ?,
                                    updated_at = ?
                                WHERE project_id = ?"""
                params = [
                    1 if settings.get('strict_doc_read', False) else 0,
                    1 if settings.get('strict_file_ref', False) else 0,
                    1 if settings.get('strict_log_entry', False) else 0,
                    1 if settings.get('github_enabled', False) else 0,
                    settings.get('github_repo', ''),
                    1 if settings.get('monitor_enabled', False) else 0,
                    settings.get('monitor_interval', 60),
                    settings.get('project_root', ''),
                    now,
                    project_id
                ]
            else:
                from datetime import datetime
                now = datetime.utcnow().isoformat()
                update_query = """INSERT INTO project_settings 
                                (project_id, strict_doc_read, strict_file_ref, strict_log_entry,
                                 github_enabled, github_repo, monitor_enabled, monitor_interval, project_root,
                                 created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                params = [
                    project_id,
                    1 if settings.get('strict_doc_read', False) else 0,
                    1 if settings.get('strict_file_ref', False) else 0,
                    1 if settings.get('strict_log_entry', False) else 0,
                    1 if settings.get('github_enabled', False) else 0,
                    settings.get('github_repo', ''),
                    1 if settings.get('monitor_enabled', False) else 0,
                    settings.get('monitor_interval', 60),
                    settings.get('project_root', ''),
                    now,
                    now
                ]
            
            db.execute_query(update_query, params)
            if hasattr(db, 'conn'):
                db.conn.commit()
            elif hasattr(db, 'connection'):
                db.connection.commit()
        
        db.disconnect()
        
        logger.info(f"Settings saved successfully for project {project_id}")
        return {"status": "success", "message": "Settings updated successfully"}
        
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.get("/api/database-info")
async def get_database_info():
    """Get database connection information."""
    logger.info("[DATABASE API] Getting database info")
    
    try:
        from tracline.core.config import Config
        config = Config()
        
        # Get database type and basic info
        db_info = {
            'type': getattr(config.config.database, 'type', 'unknown'),
            'status': 'connected',
            'details': {}
        }
        
        if db_info['type'] == 'postgresql':
            db_info['details'] = {
                'host': getattr(config.config.database, 'host', 'localhost'),
                'port': getattr(config.config.database, 'port', 5432),
                'database': getattr(config.config.database, 'name', 'tracline'),
                'user': getattr(config.config.database, 'user', 'postgres')
            }
        elif db_info['type'] == 'sqlite':
            # Expand path and make it absolute for clarity
            import os
            db_path = getattr(config.config.database, 'path', 'tracline.db')
            if db_path.startswith('~'):
                db_path = os.path.expanduser(db_path)
            db_path = os.path.abspath(db_path)
            
            db_info['details'] = {
                'path': db_path,
                'size': 'Unknown',
                'location': 'Local filesystem'
            }
            
            # Try to get file size if database exists
            try:
                if os.path.exists(db_path):
                    size_bytes = os.path.getsize(db_path)
                    # Format size nicely
                    if size_bytes < 1024:
                        db_info['details']['size'] = f"{size_bytes} bytes"
                    elif size_bytes < 1024 * 1024:
                        db_info['details']['size'] = f"{size_bytes / 1024:.1f} KB"
                    else:
                        db_info['details']['size'] = f"{size_bytes / (1024 * 1024):.1f} MB"
            except:
                pass
        
        return db_info
        
    except Exception as e:
        logger.error(f"Error getting database info: {e}")
        return {
            'type': 'unknown',
            'status': 'error',
            'error': str(e),
            'details': {}
        }

@app.get("/api/traceability-matrix/enhanced")
async def get_enhanced_traceability_matrix(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    file_extension: Optional[str] = Query(None, description="Filter by file extension"),
    file_name_contains: Optional[str] = Query(None, description="Filter files containing text"),
    task_name_contains: Optional[str] = Query(None, description="Filter tasks containing text"),
    include_reference_counts: bool = Query(True, description="Include reference counts")
):
    """Get enhanced traceability matrix with filtering and reference counts."""
    logger.info(f"[MATRIX API] Called with filters: project={project_id}, ext={file_extension}")
    
    try:
        # Return test data for now to ensure endpoint works
        matrix_data = {
            "tasks": [],
            "files": [],
            "matrix": [],
            "file_reference_counts": {},
            "summary": {
                "total_tasks": 0,
                "total_files": 0,
                "total_associations": 0,
                "avg_files_per_task": 0,
                "most_referenced_files": []
            },
            "filters": {
                "project_id": project_id,
                "file_extension": file_extension,
                "file_name_contains": file_name_contains,
                "task_name_contains": task_name_contains
            }
        }
        
        # Try to get real data if available
        try:
            from tracline.core.config import Config
            from tracline.core.task_service import TaskService
            from tracline.db.factory import DatabaseFactory
            
            config = Config()
            db = DatabaseFactory.create(config.config.database)
            task_service = TaskService(config, db)
            
            with task_service:
                # Get tasks
                filters = {}
                if project_id:
                    filters['project_id'] = project_id
                
                all_tasks = task_service.db.list_tasks(filters=filters)
                
                # Filter by task name
                if task_name_contains:
                    all_tasks = [
                        task for task in all_tasks 
                        if task_name_contains.lower() in task.title.lower()
                    ]
                
                # Get file associations
                all_files = set()
                task_files = {}
                file_reference_counts = {}
                
                for task in all_tasks:
                    files = task_service.db.get_file_associations(task.id)
                    task_file_paths = []
                    
                    for f in files:
                        file_path = f.file_path
                        
                        # Apply filters
                        if file_extension and not file_path.endswith(file_extension):
                            continue
                        if file_name_contains and file_name_contains.lower() not in file_path.lower():
                            continue
                        
                        task_file_paths.append(file_path)
                        all_files.add(file_path)
                        file_reference_counts[file_path] = file_reference_counts.get(file_path, 0) + 1
                    
                    task_files[task.id] = task_file_paths
                
                # Build matrix
                sorted_files = sorted(list(all_files))
                
                matrix_data["tasks"] = [
                    {
                        "id": t.id,
                        "title": t.title,
                        "status": t.status if isinstance(t.status, str) else t.status.value,
                        "assignee": t.assignee,
                        "priority": t.priority
                    } for t in all_tasks
                ]
                matrix_data["files"] = sorted_files
                
                if include_reference_counts:
                    matrix_data["file_reference_counts"] = file_reference_counts
                
                # Build matrix
                for task in all_tasks:
                    row = []
                    for file_path in sorted_files:
                        row.append(1 if file_path in task_files.get(task.id, []) else 0)
                    matrix_data["matrix"].append(row)
                
                # Update summary
                total_associations = sum(file_reference_counts.values()) if file_reference_counts else 0
                matrix_data["summary"] = {
                    "total_tasks": len(all_tasks),
                    "total_files": len(sorted_files),
                    "total_associations": total_associations,
                    "avg_files_per_task": round(total_associations / len(all_tasks), 2) if all_tasks else 0,
                    "most_referenced_files": sorted(
                        [(f, c) for f, c in file_reference_counts.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                }
                
        except Exception as e:
            logger.warning(f"Could not get real matrix data: {e}")
            # Return empty matrix data
        
        return matrix_data
        
    except Exception as e:
        logger.error(f"Error in get_enhanced_traceability_matrix: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/traceability-matrix/file-extensions")
async def get_file_extensions(project_id: Optional[str] = None):
    """Get all unique file extensions in the project."""
    logger.info(f"[EXTENSIONS API] Getting file extensions for project: {project_id}")
    
    # Return common extensions for now
    return [".py", ".js", ".html", ".css", ".yaml", ".md", ".json"]

@app.get("/api/tasks")
async def get_tasks(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[int] = Query(None, description="Filter by priority")
):
    """Get tasks for a project."""
    logger.info(f"[TASKS API] Getting tasks - project: {project_id}, assignee: {assignee}, status: {status}, priority: {priority}")
    
    try:
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Direct database query - note: SQLite uses task_id, not id
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            query = """SELECT id, title, status, priority, assignee, created_at, 
                      updated_at, project_id, description 
                      FROM tasks 
                      WHERE 1=1"""
            params = []
            
            if project_id:
                query += " AND project_id = %s"
                params.append(project_id)
            if assignee:
                query += " AND assignee = %s"
                params.append(assignee)
            if status:
                query += " AND status = %s"
                params.append(status)
            if priority:
                query += " AND priority = %s"
                params.append(priority)
                
            query += " ORDER BY created_at DESC"
            if not project_id:
                query += " LIMIT 100"
        else:
            # SQLite - use task_id instead of id
            query = """SELECT task_id as id, title, status, priority, assignee, created_at, 
                      updated_at, project_id, description 
                      FROM tasks 
                      WHERE 1=1"""
            params = []
            
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            if assignee:
                query += " AND assignee = ?"
                params.append(assignee)
            if status:
                query += " AND status = ?"
                params.append(status)
            if priority:
                query += " AND priority = ?"
                params.append(priority)
                
            query += " ORDER BY created_at DESC"
            if not project_id:
                query += " LIMIT 100"
        
        cursor = db.execute_query(query, params)
        rows = cursor.fetchall()
        
        task_list = []
        for row in rows:
            if isinstance(row, dict):
                task_dict = {
                    'id': row['id'],
                    'title': row['title'],
                    'status': row['status'],
                    'priority': row.get('priority', 3),
                    'assignee': row.get('assignee', ''),
                    'created_at': row['created_at'].isoformat() if hasattr(row.get('created_at'), 'isoformat') else row.get('created_at'),
                    'updated_at': row['updated_at'].isoformat() if hasattr(row.get('updated_at'), 'isoformat') else row.get('updated_at'),
                    'project_id': row.get('project_id', ''),
                    'description': row.get('description', '')
                }
            else:
                # Handle tuples
                task_dict = {
                    'id': row[0],
                    'title': row[1],
                    'status': row[2],
                    'priority': row[3] or 3,
                    'assignee': row[4] or '',
                    'created_at': row[5].isoformat() if hasattr(row[5], 'isoformat') else row[5],
                    'updated_at': row[6].isoformat() if hasattr(row[6], 'isoformat') else row[6],
                    'project_id': row[7] or '',
                    'description': row[8] or ''
                }
            
            # Fetch relationships for this task
            relationships = []
            try:
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    rel_query = """SELECT parent_id, child_id, relationship_type 
                                  FROM task_relationships 
                                  WHERE parent_id = %s OR child_id = %s"""
                    rel_params = [task_dict['id'], task_dict['id']]
                else:
                    # SQLite
                    rel_query = """SELECT parent_id, child_id, relationship_type 
                                  FROM task_relationships 
                                  WHERE parent_id = ? OR child_id = ?"""
                    rel_params = [task_dict['id'], task_dict['id']]
                
                rel_cursor = db.execute_query(rel_query, rel_params)
                rel_rows = rel_cursor.fetchall()
                
                for rel_row in rel_rows:
                    if isinstance(rel_row, dict):
                        relationships.append({
                            'parent_id': rel_row['parent_id'],
                            'child_id': rel_row['child_id'],
                            'relationship_type': rel_row['relationship_type']
                        })
                    else:
                        relationships.append({
                            'parent_id': rel_row[0],
                            'child_id': rel_row[1],
                            'relationship_type': rel_row[2]
                        })
                
                logger.info(f"Task {task_dict['id']} has {len(relationships)} relationships")
            except Exception as e:
                logger.warning(f"Could not fetch relationships for task {task_dict['id']}: {e}")
            
            task_dict['relationships'] = relationships
            
            # Fetch file associations for this task (with error handling)
            files = []
            try:
                # First try file_associations table
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    file_query = """SELECT file_path, 
                                  COALESCE(file_type, '') as file_type,
                                  COALESCE(description, '') as description 
                                  FROM file_associations 
                                  WHERE task_id = %s"""
                    file_params = [task_dict['id']]
                else:
                    # SQLite
                    file_query = """SELECT file_path, 
                                  COALESCE(file_type, '') as file_type,
                                  COALESCE(description, '') as description 
                                  FROM file_associations 
                                  WHERE task_id = ?"""
                    file_params = [task_dict['id']]
                
                file_cursor = db.execute_query(file_query, file_params)
                file_rows = file_cursor.fetchall()
                
                # If no files found in file_associations, try task_files table
                if not file_rows:
                    try:
                        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                            file_query = """SELECT file_path, file_type as description 
                                          FROM task_files 
                                          WHERE task_id = %s"""
                            file_params = [task_dict['id']]
                        else:
                            # SQLite
                            file_query = """SELECT file_path, file_type as description 
                                          FROM task_files 
                                          WHERE task_id = ?"""
                            file_params = [task_dict['id']]
                        
                        file_cursor = db.execute_query(file_query, file_params)
                        file_rows = file_cursor.fetchall()
                    except Exception as e:
                        # task_files table might not exist
                        logger.debug(f"Could not query task_files table: {e}")
                        file_rows = []
                
                for file_row in file_rows:
                    if isinstance(file_row, dict):
                        files.append({
                            'file_path': file_row['file_path'],
                            'file_type': file_row.get('file_type', ''),
                            'description': file_row.get('description', '')
                        })
                    else:
                        # Columns are: file_path, file_type, description
                        files.append({
                            'file_path': file_row[0],
                            'file_type': file_row[1] if len(file_row) > 1 and file_row[1] else '',
                            'description': file_row[2] if len(file_row) > 2 and file_row[2] else ''
                        })
            except Exception as e:
                # Log error but don't fail the entire request
                logger.warning(f"Could not fetch file associations for task {task_dict['id']}: {e}")
            
            task_dict['files'] = files
            task_list.append(task_dict)
        
        db.disconnect()
        
        logger.info(f"Found {len(task_list)} tasks for project {project_id}")
        return task_list
        
    except Exception as e:
        logger.error(f"Error in get_tasks: {e}")
        return []

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a single task with relationships."""
    logger.info(f"[TASKS API] Getting task: {task_id}")
    
    try:
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Get task details
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            query = """SELECT id, title, status, priority, assignee, created_at, 
                      updated_at, project_id, description 
                      FROM tasks 
                      WHERE id = %s"""
            params = [task_id]
        else:
            # SQLite - use task_id
            query = """SELECT task_id as id, title, status, priority, assignee, created_at, 
                      updated_at, project_id, description 
                      FROM tasks 
                      WHERE task_id = ?"""
            params = [task_id]
        
        cursor = db.execute_query(query, params)
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Build task dict
        if isinstance(row, dict):
            task_dict = {
                'id': row['id'],
                'title': row['title'],
                'status': row['status'],
                'priority': row.get('priority', 3),
                'assignee': row.get('assignee', ''),
                'created_at': row['created_at'].isoformat() if hasattr(row.get('created_at'), 'isoformat') else row.get('created_at'),
                'updated_at': row['updated_at'].isoformat() if hasattr(row.get('updated_at'), 'isoformat') else row.get('updated_at'),
                'project_id': row.get('project_id', ''),
                'description': row.get('description', '')
            }
        else:
            # Handle tuples
            task_dict = {
                'id': row[0],
                'title': row[1],
                'status': row[2],
                'priority': row[3] or 3,
                'assignee': row[4] or '',
                'created_at': row[5].isoformat() if hasattr(row[5], 'isoformat') else row[5],
                'updated_at': row[6].isoformat() if hasattr(row[6], 'isoformat') else row[6],
                'project_id': row[7] or '',
                'description': row[8] or ''
            }
        
        # Fetch relationships
        relationships = []
        try:
            if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                rel_query = """SELECT parent_id, child_id, relationship_type 
                              FROM task_relationships 
                              WHERE parent_id = %s OR child_id = %s"""
                rel_params = [task_id, task_id]
            else:
                # SQLite
                rel_query = """SELECT parent_id, child_id, relationship_type 
                              FROM task_relationships 
                              WHERE parent_id = ? OR child_id = ?"""
                rel_params = [task_id, task_id]
            
            rel_cursor = db.execute_query(rel_query, rel_params)
            rel_rows = rel_cursor.fetchall()
            
            for rel_row in rel_rows:
                if isinstance(rel_row, dict):
                    relationships.append({
                        'parent_id': rel_row['parent_id'],
                        'child_id': rel_row['child_id'],
                        'relationship_type': rel_row['relationship_type']
                    })
                else:
                    relationships.append({
                        'parent_id': rel_row[0],
                        'child_id': rel_row[1],
                        'relationship_type': rel_row[2]
                    })
            
            logger.info(f"Individual task {task_id} has {len(relationships)} relationships")
        except Exception as e:
            logger.warning(f"Could not fetch relationships for individual task {task_id}: {e}")
        
        task_dict['relationships'] = relationships
        
        # Fetch file associations (with error handling)
        files = []
        try:
            # First try file_associations table
            if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                file_query = """SELECT file_path, 
                              COALESCE(file_type, '') as file_type,
                              COALESCE(description, '') as description 
                              FROM file_associations 
                              WHERE task_id = %s"""
                file_params = [task_id]
            else:
                # SQLite
                file_query = """SELECT file_path,
                              COALESCE(file_type, '') as file_type,
                              COALESCE(description, '') as description 
                              FROM file_associations 
                              WHERE task_id = ?"""
                file_params = [task_id]
            
            file_cursor = db.execute_query(file_query, file_params)
            file_rows = file_cursor.fetchall()
            
            # If no files found in file_associations, try task_files table
            if not file_rows:
                try:
                    if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                        file_query = """SELECT file_path, file_type as description 
                                      FROM task_files 
                                      WHERE task_id = %s"""
                        file_params = [task_id]
                    else:
                        # SQLite
                        file_query = """SELECT file_path, file_type as description 
                                      FROM task_files 
                                      WHERE task_id = ?"""
                        file_params = [task_id]
                    
                    file_cursor = db.execute_query(file_query, file_params)
                    file_rows = file_cursor.fetchall()
                except Exception as e:
                    # task_files table might not exist
                    logger.debug(f"Could not query task_files table: {e}")
                    file_rows = []
            
            for file_row in file_rows:
                if isinstance(file_row, dict):
                    files.append({
                        'file_path': file_row['file_path'],
                        'file_type': file_row.get('file_type', ''),
                        'description': file_row.get('description', '')
                    })
                else:
                    # Columns are: file_path, file_type, description
                    files.append({
                        'file_path': file_row[0],
                        'file_type': file_row[1] if len(file_row) > 1 and file_row[1] else '',
                        'description': file_row[2] if len(file_row) > 2 and file_row[2] else ''
                    })
        except Exception as e:
            # Log error but don't fail the entire request
            logger.warning(f"Could not fetch file associations for task {task_id}: {e}")
        
        task_dict['files'] = files
        
        db.disconnect()
        
        logger.info(f"Found task {task_id} with {len(relationships)} relationships and {len(files)} files")
        return task_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/status")
async def update_task_status(task_id: str, status_update: Dict[str, str]):
    """Update task status."""
    logger.info(f"[TASKS API] Updating status for task: {task_id}")
    
    try:
        new_status = status_update.get('status')
        if not new_status:
            raise HTTPException(status_code=400, detail="Status is required")
        
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Update task status
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            query = "UPDATE tasks SET status = %s, updated_at = NOW() WHERE id = %s"
            params = [new_status, task_id]
        else:
            # SQLite - use task_id
            query = "UPDATE tasks SET status = ?, updated_at = datetime('now') WHERE task_id = ?"
            params = [new_status, task_id]
        
        cursor = db.execute_query(query, params)
        
        # Check if task was updated
        if cursor.rowcount == 0:
            db.disconnect()
            raise HTTPException(status_code=404, detail="Task not found")
        
        # IMPORTANT: Commit the changes
        if hasattr(db, 'conn') and db.conn:
            db.conn.commit()
        elif hasattr(db, 'connection') and db.connection:
            db.connection.commit()
        
        db.disconnect()
        
        return {"id": task_id, "status": new_status, "message": "Status updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/relationships")
async def create_relationship(relationship: Dict[str, str]):
    """Create a relationship between two tasks."""
    logger.info(f"[RELATIONSHIP API] Creating relationship: {relationship}")
    
    try:
        parent_id = relationship.get('parent_id')
        child_id = relationship.get('child_id')
        rel_type = relationship.get('relationship_type', 'parent-child')
        
        if not parent_id or not child_id:
            raise HTTPException(status_code=400, detail="Both parent_id and child_id are required")
        
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Insert relationship
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            query = """INSERT INTO task_relationships 
                      (parent_id, child_id, relationship_type, created_at)
                      VALUES (%s, %s, %s, NOW())"""
            params = [parent_id, child_id, rel_type]
        else:
            # SQLite
            from datetime import datetime
            query = """INSERT INTO task_relationships 
                      (parent_id, child_id, relationship_type, created_at)
                      VALUES (?, ?, ?, ?)"""
            params = [parent_id, child_id, rel_type, datetime.now().isoformat()]
        
        db.execute_query(query, params)
        
        if hasattr(db, 'conn'):
            db.conn.commit()
        elif hasattr(db, 'connection'):
            db.connection.commit()
        
        db.disconnect()
        
        logger.info(f"Created relationship: {parent_id} -> {child_id} ({rel_type})")
        return {"status": "success", "message": "Relationship created"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/relationships")
async def delete_relationship(relationship: Dict[str, str]):
    """Delete a relationship between two tasks."""
    logger.info(f"[RELATIONSHIP API] Deleting relationship: {relationship}")
    
    try:
        parent_id = relationship.get('parent_id')
        child_id = relationship.get('child_id')
        
        if not parent_id or not child_id:
            raise HTTPException(status_code=400, detail="Both parent_id and child_id are required")
        
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Delete relationship
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            query = """DELETE FROM task_relationships 
                      WHERE parent_id = %s AND child_id = %s"""
            params = [parent_id, child_id]
        else:
            # SQLite
            query = """DELETE FROM task_relationships 
                      WHERE parent_id = ? AND child_id = ?"""
            params = [parent_id, child_id]
        
        cursor = db.execute_query(query, params)
        
        if hasattr(db, 'conn'):
            db.conn.commit()
        elif hasattr(db, 'connection'):
            db.connection.commit()
        
        db.disconnect()
        
        logger.info(f"Deleted relationship: {parent_id} -> {child_id}")
        return {"status": "success", "message": "Relationship deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/assignee")
async def update_task_assignee(task_id: str, assignee_update: Dict[str, Any]):
    """Update task assignee."""
    logger.info(f"[TASKS API] Updating assignee for task: {task_id}")
    logger.info(f"[TASKS API] Received assignee_update: {assignee_update}")
    
    try:
        # Handle null/None assignee for unassignment
        new_assignee = assignee_update.get('assignee')
        if new_assignee is None:
            new_assignee = ''  # Convert None to empty string for DB
        
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Update task assignee
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            query = "UPDATE tasks SET assignee = %s, updated_at = NOW() WHERE id = %s"
            params = [new_assignee, task_id]
        else:
            # SQLite - use task_id
            query = "UPDATE tasks SET assignee = ?, updated_at = datetime('now') WHERE task_id = ?"
            params = [new_assignee, task_id]
        
        cursor = db.execute_query(query, params)
        
        # Check if task was updated
        if cursor.rowcount == 0:
            db.disconnect()
            raise HTTPException(status_code=404, detail="Task not found")
        
        # IMPORTANT: Commit the changes
        if hasattr(db, 'conn') and db.conn:
            db.conn.commit()
        elif hasattr(db, 'connection') and db.connection:
            db.connection.commit()
        
        db.disconnect()
        
        return {"id": task_id, "assignee": new_assignee, "message": "Assignee updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task assignee: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/team-hierarchy/{project_id}")
async def get_team_hierarchy(project_id: str):
    """Get team hierarchy for a project."""
    logger.info(f"[TEAM API] Getting team hierarchy for project: {project_id}")
    
    try:
        # Try to get real team data from database
        try:
            from tracline.core.config import Config
            from tracline.db.factory import DatabaseFactory
            
            config = Config()
            db = DatabaseFactory.create(config.config.database)
            db.connect()
            
            # Get team members
            if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                # Get members for this specific project using project_memberships
                query = """SELECT m.id, m.name, m.role, m.position, m.leader_id, m.profile_image_path
                          FROM members m
                          INNER JOIN project_memberships pm ON m.id = pm.member_id
                          WHERE pm.project_id = %s
                          ORDER BY 
                            CASE m.position 
                              WHEN 'LEADER' THEN 1 
                              WHEN 'SUB_LEADER' THEN 2 
                              ELSE 3 
                            END, m.name"""
                params = [project_id]
            else:
                # For SQLite, also use project_memberships
                query = """SELECT m.id, m.name, m.role, m.position, m.leader_id, m.profile_image_path
                          FROM members m
                          INNER JOIN project_memberships pm ON m.id = pm.member_id
                          WHERE pm.project_id = ?
                          ORDER BY m.name"""
                params = [project_id]
            
            cursor = db.execute_query(query, params)
            rows = cursor.fetchall()
            
            members = []
            for row in rows:
                if isinstance(row, dict):
                    member = {
                        'id': row['id'],
                        'name': row['name'],
                        'email': '',  # No email column in schema
                        'role': row.get('role', 'MEMBER'),
                        'position': row.get('position', 'MEMBER'),
                        'avatar_url': row.get('profile_image_path', ''),
                        'profile_image_path': row.get('profile_image_path', ''),
                        'manager_id': row.get('leader_id')  # leader_id is the manager
                    }
                else:
                    # Handle tuples - columns: id, name, role, position, leader_id, profile_image_path
                    member = {
                        'id': row[0],
                        'name': row[1],
                        'email': '',
                        'role': row[2] or 'MEMBER',
                        'position': row[3] or 'MEMBER',
                        'avatar_url': row[5] or '',
                        'profile_image_path': row[5] or '',
                        'manager_id': row[4]  # leader_id
                    }
                    
                members.append(member)
            
            # Now get task count and recent tasks for each member
            for member in members:
                # Get task count
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    count_query = """SELECT COUNT(*) as count FROM tasks 
                                   WHERE assignee = %s AND project_id = %s"""
                    count_params = [member['id'], project_id]
                    
                    # Get recent tasks - order by status priority first (DOING > TESTING > READY > TODO)
                    tasks_query = """SELECT id, title, status, priority 
                                   FROM tasks 
                                   WHERE assignee = %s AND project_id = %s 
                                   AND status NOT IN ('DONE', 'CANCELED')
                                   ORDER BY 
                                     CASE status 
                                       WHEN 'DOING' THEN 0
                                       WHEN 'TESTING' THEN 1
                                       WHEN 'READY' THEN 2
                                       WHEN 'TODO' THEN 3
                                       WHEN 'PENDING' THEN 4
                                       ELSE 5
                                     END,
                                     priority DESC, 
                                     created_at ASC 
                                   LIMIT 5"""
                    tasks_params = [member['id'], project_id]
                else:
                    # SQLite
                    count_query = """SELECT COUNT(*) as count FROM tasks 
                                   WHERE assignee = ? AND project_id = ?"""
                    count_params = [member['id'], project_id]
                    
                    # Order by status priority first (DOING > TESTING > READY > TODO)
                    tasks_query = """SELECT task_id as id, title, status, priority 
                                   FROM tasks 
                                   WHERE assignee = ? AND project_id = ? 
                                   AND status NOT IN ('DONE', 'CANCELED')
                                   ORDER BY 
                                     CASE status 
                                       WHEN 'DOING' THEN 0
                                       WHEN 'TESTING' THEN 1
                                       WHEN 'READY' THEN 2
                                       WHEN 'TODO' THEN 3
                                       WHEN 'PENDING' THEN 4
                                       ELSE 5
                                     END,
                                     priority DESC, 
                                     created_at ASC 
                                   LIMIT 5"""
                    tasks_params = [member['id'], project_id]
                
                # Execute count query
                count_cursor = db.execute_query(count_query, count_params)
                count_row = count_cursor.fetchone()
                
                if isinstance(count_row, dict):
                    member['task_count'] = count_row.get('count', 0)
                else:
                    member['task_count'] = count_row[0] if count_row else 0
                
                # Get status-specific counts
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    status_query = """SELECT status, COUNT(*) as count FROM tasks 
                                     WHERE assignee = %s AND project_id = %s 
                                     AND status NOT IN ('DONE', 'CANCELED')
                                     GROUP BY status"""
                    status_params = [member['id'], project_id]
                else:
                    status_query = """SELECT status, COUNT(*) as count FROM tasks 
                                     WHERE assignee = ? AND project_id = ? 
                                     AND status NOT IN ('DONE', 'CANCELED')
                                     GROUP BY status"""
                    status_params = [member['id'], project_id]
                
                status_cursor = db.execute_query(status_query, status_params)
                status_counts = status_cursor.fetchall()
                
                # Initialize counts
                member['todo_count'] = 0
                member['ready_count'] = 0
                member['doing_count'] = 0
                member['testing_count'] = 0
                
                for status_row in status_counts:
                    if isinstance(status_row, dict):
                        status = status_row['status']
                        count = status_row['count']
                    else:
                        status = status_row[0]
                        count = status_row[1]
                    
                    if status == 'TODO':
                        member['todo_count'] = count
                    elif status == 'READY':
                        member['ready_count'] = count
                    elif status == 'DOING':
                        member['doing_count'] = count
                    elif status == 'TESTING':
                        member['testing_count'] = count
                
                # Debug logging for AI-TARGE
                if member['id'] == 'AI-TARGE':
                    logger.info(f"[TEAM API DEBUG] AI-TARGE task count query result: {count_row}")
                    logger.info(f"[TEAM API DEBUG] AI-TARGE task_count set to: {member['task_count']}")
                    logger.info(f"[TEAM API DEBUG] AI-TARGE status counts: TODO={member['todo_count']}, READY={member['ready_count']}, DOING={member['doing_count']}, TESTING={member['testing_count']}")
                    logger.info(f"[TEAM API DEBUG] Count query: {count_query}")
                    logger.info(f"[TEAM API DEBUG] Count params: {count_params}")
                
                # Execute tasks query
                tasks_cursor = db.execute_query(tasks_query, tasks_params)
                tasks_rows = tasks_cursor.fetchall()
                
                recent_tasks = []
                for task_row in tasks_rows:
                    if isinstance(task_row, dict):
                        recent_tasks.append({
                            'id': task_row['id'],
                            'title': task_row['title'],
                            'status': task_row['status'],
                            'priority': task_row.get('priority', 3)
                        })
                    else:
                        recent_tasks.append({
                            'id': task_row[0],
                            'title': task_row[1],
                            'status': task_row[2],
                            'priority': task_row[3] if task_row[3] else 3
                        })
                
                member['recent_tasks'] = recent_tasks
                
                # Extract task IDs by status for frontend display
                member['doing_task_ids'] = [task['id'] for task in recent_tasks if task['status'] == 'DOING']
                member['testing_task_ids'] = [task['id'] for task in recent_tasks if task['status'] == 'TESTING']
                member['ready_task_ids'] = [task['id'] for task in recent_tasks if task['status'] == 'READY']
                member['todo_task_ids'] = [task['id'] for task in recent_tasks if task['status'] == 'TODO']
                member['pending_task_ids'] = [task['id'] for task in recent_tasks if task['status'] == 'PENDING']
                
                # Debug log for task ordering
                if recent_tasks:
                    logger.info(f"[TEAM API] Member {member['id']} recent_tasks order: {[(t['id'], t['status']) for t in recent_tasks[:3]]}")
                
                # Debug log for DOING tasks
                if member['doing_task_ids']:
                    logger.info(f"[TEAM API] Member {member['id']} has {len(member['doing_task_ids'])} DOING tasks: {member['doing_task_ids']}")
            
            db.disconnect()
            
            # Build hierarchy tree and return just the tree
            tree = build_hierarchy_tree(members)
            
            # Return the tree array directly, as JavaScript expects
            return tree
            
        except Exception as e:
            logger.warning(f"Could not get team hierarchy from database: {e}")
            # Return empty array
            return []
            
    except Exception as e:
        logger.error(f"Error in get_team_hierarchy: {e}")
        return []

@app.get("/api/members/{member_id}")
async def get_member(member_id: str):
    """Get member details by ID."""
    try:
        # Get database instance
        db_instance = task_service.db
        
        with db_instance:
            member = db_instance.get_member(member_id)
            if not member:
                raise HTTPException(status_code=404, detail="Member not found")
            
            # Convert to dict
            if hasattr(member, 'model_dump'):
                return member.model_dump()
            else:
                return member.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting member {member_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/members/{member_id}/upload-photo")
async def upload_member_photo(member_id: str, file: UploadFile = File(...)):
    """Upload a photo for a team member."""
    logger.info(f"[UPLOAD API] Uploading photo for member: {member_id}")
    
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Create static/images directory if it doesn't exist
        images_dir = current_dir / "static" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp to avoid caching issues
        import time
        timestamp = int(time.time())
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"{member_id}_profile_{timestamp}.{file_extension}"
        file_path = images_dir / filename
        
        # Save the file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Clean up old profile images for this member
        try:
            for old_file in images_dir.glob(f"{member_id}_profile_*"):
                if old_file.name != filename:
                    old_file.unlink()
                    logger.info(f"Deleted old profile image: {old_file.name}")
        except Exception as e:
            logger.warning(f"Could not clean up old images: {e}")
        
        # Update database with the image path
        try:
            from tracline.core.config import Config
            from tracline.db.factory import DatabaseFactory
            
            config = Config()
            db = DatabaseFactory.create(config.config.database)
            db.connect()
            
            # Update member's profile_image_path
            relative_path = f"/static/images/{filename}"
            
            if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                query = "UPDATE members SET profile_image_path = %s WHERE id = %s"
                params = [relative_path, member_id]
            else:
                query = "UPDATE members SET profile_image_path = ? WHERE id = ?"
                params = [relative_path, member_id]
            
            cursor = db.execute_query(query, params)
            
            # IMPORTANT: Always commit the changes
            if hasattr(db, 'conn') and db.conn:
                db.conn.commit()
            elif hasattr(db, 'connection') and db.connection:
                db.connection.commit()
            else:
                logger.error("WARNING: No commit method found on database connection!")
            
            db.disconnect()
            
            logger.info(f"Photo uploaded successfully for member {member_id}: {relative_path}")
            return {
                "status": "success",
                "message": "Photo uploaded successfully",
                "path": relative_path
            }
            
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            # Still return success if file was saved
            return {
                "status": "success",
                "message": "Photo uploaded (database update failed)",
                "path": f"/static/images/{filename}"
            }
            
    except Exception as e:
        logger.error(f"Error uploading photo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def build_hierarchy_tree(members):
    """Build a tree structure from flat member list."""
    member_dict = {m['id']: m for m in members}
    tree = []
    
    # Initialize direct_reports for all members
    for member in members:
        member['direct_reports'] = []
    
    # Build the hierarchy
    for member in members:
        if member['manager_id'] is None:
            # Root level member
            tree.append(member)
        else:
            # Add to manager's direct_reports
            manager = member_dict.get(member['manager_id'])
            if manager:
                manager['direct_reports'].append(member)
    
    return tree

# List all endpoints for debugging
@app.get("/api/endpoints")
async def list_endpoints():
    """List all registered API endpoints."""
    endpoints = []
    for route in app.routes:
        if hasattr(route, 'path') and '/api/' in route.path:
            endpoints.append({
                "path": route.path,
                "methods": list(route.methods) if hasattr(route, 'methods') else [],
                "name": route.name if hasattr(route, 'name') else None
            })
    return {"endpoints": endpoints, "count": len(endpoints)}

# Basic routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/projects")
async def get_projects():
    """Get all projects."""
    logger.info("[PROJECTS API] Getting projects")
    
    # Initialize empty projects list
    projects = []
    
    try:
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        query = "SELECT * FROM projects"
        cursor = db.execute_query(query)
        rows = cursor.fetchall()
        
        if rows:
            projects = []
            for row in rows:
                if isinstance(row, dict):
                    projects.append({
                        'id': row['id'],
                        'name': row['name'],
                        'description': row['description']
                    })
                else:
                    projects.append({
                        'id': row[0],
                        'name': row[1],
                        'description': row[2]
                    })
                    
        db.disconnect()
        
    except Exception as e:
        logger.warning(f"Could not get projects from database: {e}")
    
    # Add current project info
    current_project_id = None
    try:
        current_project_id = config.get_current_project()
    except:
        pass
    
    return {
        "projects": projects,
        "current_project": current_project_id
    }

# Now import the rest of TracLine components
try:
    from tracline.core.config import Config
    from tracline.core.task_service import TaskService
    from tracline.core.team_service import TeamService
    from tracline.db.factory import DatabaseFactory
    
    # Initialize configuration and database
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    # Initialize services
    task_service = TaskService(config, db)
    team_service = TeamService(config, db)
    
    logger.info("TracLine components initialized successfully")
    
except Exception as e:
    logger.error(f"Error initializing TracLine components: {e}")
    config = None
    db = None
    task_service = None
    team_service = None

# File viewer endpoint
@app.get("/api/files/view")
async def view_file(
    file_path: str = Query(..., description="File path to view"),
    project_id: Optional[str] = Query(None, description="Project ID for relative path resolution")
):
    """View file contents with security checks and project root resolution."""
    logger.info(f"[FILE VIEWER API] Request to view file: {file_path}, project: {project_id}")
    
    try:
        import os
        from pathlib import Path
        
        # Initialize resolved path
        resolved_path = None
        
        # If project_id is provided, try to get project root
        if project_id:
            try:
                from tracline.core.config import Config
                from tracline.db.factory import DatabaseFactory
                
                config = Config()
                db = DatabaseFactory.create(config.config.database)
                db.connect()
                
                # Get project root from project_settings
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    query = "SELECT project_root FROM project_settings WHERE project_id = %s"
                    params = [project_id]
                else:
                    query = "SELECT project_root FROM project_settings WHERE project_id = ?"
                    params = [project_id]
                
                try:
                    cursor = db.execute_query(query, params)
                    row = cursor.fetchone()
                    
                    if row:
                        project_root = row[0] if isinstance(row, tuple) else row.get('project_root')
                        if project_root and not os.path.isabs(file_path):
                            # Resolve relative path with project root
                            resolved_path = os.path.join(project_root, file_path)
                            logger.info(f"Resolved relative path: {file_path} -> {resolved_path}")
                except Exception as e:
                    logger.warning(f"Could not get project root: {e}")
                
                db.disconnect()
                
            except Exception as e:
                logger.error(f"Error accessing project settings: {e}")
        
        # If not resolved yet, use the path as-is (must be absolute)
        if not resolved_path:
            if not os.path.isabs(file_path):
                raise HTTPException(
                    status_code=400, 
                    detail="File path must be absolute when project root is not configured"
                )
            resolved_path = file_path
        
        # Security checks
        resolved_path = os.path.abspath(resolved_path)  # Normalize path
        
        # Check if file exists
        if not os.path.exists(resolved_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if it's a file (not directory)
        if not os.path.isfile(resolved_path):
            raise HTTPException(status_code=400, detail="Path is not a file")
        
        # Check file size (limit to 10MB)
        file_size = os.path.getsize(resolved_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
        
        # Determine file type and encoding
        file_extension = Path(resolved_path).suffix.lower()
        is_binary = file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.tar', '.gz', '.exe', '.bin']
        
        if is_binary:
            # For binary files, return metadata only
            return {
                "file_path": file_path,
                "resolved_path": resolved_path,
                "file_size": file_size,
                "file_type": "binary",
                "extension": file_extension,
                "content": None,
                "error": "Binary file preview not supported"
            }
        
        # Try to read text file
        try:
            # Try UTF-8 first
            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Limit content size for response
            max_chars = 1000000  # 1MB of text
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n... (truncated)"
                
            return {
                "file_path": file_path,
                "resolved_path": resolved_path,
                "file_size": file_size,
                "file_type": "text",
                "extension": file_extension,
                "content": content,
                "line_count": content.count('\n') + 1
            }
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(resolved_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    
                if len(content) > max_chars:
                    content = content[:max_chars] + "\n\n... (truncated)"
                    
                return {
                    "file_path": file_path,
                    "resolved_path": resolved_path,
                    "file_size": file_size,
                    "file_type": "text",
                    "extension": file_extension,
                    "content": content,
                    "encoding": "latin-1",
                    "line_count": content.count('\n') + 1
                }
            except Exception as e:
                return {
                    "file_path": file_path,
                    "resolved_path": resolved_path,
                    "file_size": file_size,
                    "file_type": "unknown",
                    "extension": file_extension,
                    "content": None,
                    "error": f"Could not decode file: {str(e)}"
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Project logs endpoint
@app.get("/api/projects/{project_id}/logs")
async def get_project_logs(
    project_id: str,
    limit: Optional[int] = Query(100, description="Maximum number of logs to return"),
    offset: Optional[int] = Query(0, description="Number of logs to skip")
):
    """Get logs for a specific project."""
    logger.info(f"[LOGS API] Getting logs for project: {project_id}, limit: {limit}, offset: {offset}")
    
    try:
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Query logs for the project
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            # Get logs both by direct project metadata and by task association
            query = """
                SELECT le.id, le.task_id, le.message, le.level, le.user, le.entry_type, le.created_at, le.metadata,
                       t.project_id as task_project_id
                FROM log_entries le
                LEFT JOIN tasks t ON le.task_id = t.id
                WHERE (le.metadata->>'project_id' = %s) 
                   OR (t.project_id = %s)
                ORDER BY le.created_at DESC
                LIMIT %s OFFSET %s
            """
            params = [project_id, project_id, limit, offset]
        else:
            # SQLite version with JSON extract
            query = """
                SELECT le.id, le.task_id, le.message, le.level, le.user, le.entry_type, le.timestamp as created_at, le.metadata,
                       t.project_id as task_project_id
                FROM log_entries le
                LEFT JOIN tasks t ON le.task_id = t.task_id
                WHERE (json_extract(le.metadata, '$.project_id') = ?) 
                   OR (t.project_id = ?)
                ORDER BY le.timestamp DESC
                LIMIT ? OFFSET ?
            """
            params = [project_id, project_id, limit, offset]
        
        cursor = db.execute_query(query, params)
        logs = cursor.fetchall()
        
        # Convert to list of dictionaries
        log_list = []
        for log in logs:
            log_dict = dict(log)
            # Ensure datetime is properly serialized with UTC timezone
            if log_dict.get('created_at'):
                if hasattr(log_dict['created_at'], 'isoformat'):
                    # Ensure the timestamp includes timezone info (Z for UTC)
                    timestamp = log_dict['created_at'].isoformat()
                    if not ('+' in timestamp or 'Z' in timestamp):
                        timestamp += 'Z'  # Add Z to indicate UTC
                    log_dict['created_at'] = timestamp
                else:
                    log_dict['created_at'] = str(log_dict['created_at'])
            log_list.append(log_dict)
        
        # Get total count for pagination
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            count_query = """
                SELECT COUNT(*) as total
                FROM log_entries le
                LEFT JOIN tasks t ON le.task_id = t.id
                WHERE (le.metadata->>'project_id' = %s) 
                   OR (t.project_id = %s)
            """
            count_params = [project_id, project_id]
        else:
            count_query = """
                SELECT COUNT(*) as total
                FROM log_entries le
                LEFT JOIN tasks t ON le.task_id = t.task_id
                WHERE (json_extract(le.metadata, '$.project_id') = ?) 
                   OR (t.project_id = ?)
            """
            count_params = [project_id, project_id]
        
        cursor = db.execute_query(count_query, count_params)
        total_result = cursor.fetchone()
        total_count = total_result[0] if isinstance(total_result, tuple) else total_result['total']
        
        db.disconnect()
        
        return {
            'logs': log_list,
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'project_id': project_id
        }
        
    except Exception as e:
        logger.error(f"Error getting project logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Project statistics endpoint
@app.get("/api/projects/{project_id}/statistics")
async def get_project_statistics(project_id: str):
    """Get statistics for a specific project."""
    logger.info(f"[STATS API] Getting statistics for project: {project_id}")
    
    try:
        from tracline.core.config import Config
        from tracline.db.factory import DatabaseFactory
        
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Get project creation date
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            project_query = "SELECT created_at FROM projects WHERE id = %s"
            params = [project_id]
        else:
            project_query = "SELECT created_at FROM projects WHERE id = ?"
            params = [project_id]
        
        cursor = db.execute_query(project_query, params)
        project_result = cursor.fetchone()
        
        if not project_result:
            db.disconnect()
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_created_at = project_result[0] if isinstance(project_result, tuple) else project_result['created_at']
        
        # Get latest log entry date for this project
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            latest_log_query = """
                SELECT MAX(le.created_at) as latest_log
                FROM log_entries le
                LEFT JOIN tasks t ON le.task_id = t.id
                WHERE (le.metadata->>'project_id' = %s) 
                   OR (t.project_id = %s)
            """
            params = [project_id, project_id]
        else:
            latest_log_query = """
                SELECT MAX(le.timestamp) as latest_log
                FROM log_entries le
                LEFT JOIN tasks t ON le.task_id = t.task_id
                WHERE (json_extract(le.metadata, '$.project_id') = ?) 
                   OR (t.project_id = ?)
            """
            params = [project_id, project_id]
        
        cursor = db.execute_query(latest_log_query, params)
        latest_log_result = cursor.fetchone()
        latest_log_at = latest_log_result[0] if isinstance(latest_log_result, tuple) else latest_log_result['latest_log']
        
        # Get task counts by status
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            task_stats_query = """
                SELECT status, COUNT(*) as count
                FROM tasks
                WHERE project_id = %s
                GROUP BY status
            """
            params = [project_id]
        else:
            task_stats_query = """
                SELECT status, COUNT(*) as count
                FROM tasks
                WHERE project_id = ?
                GROUP BY status
            """
            params = [project_id]
        
        cursor = db.execute_query(task_stats_query, params)
        task_stats = cursor.fetchall()
        
        # Get total tasks count
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            total_tasks_query = "SELECT COUNT(*) as total FROM tasks WHERE project_id = %s"
            params = [project_id]
        else:
            total_tasks_query = "SELECT COUNT(*) as total FROM tasks WHERE project_id = ?"
            params = [project_id]
        
        cursor = db.execute_query(total_tasks_query, params)
        total_tasks_result = cursor.fetchone()
        total_tasks = total_tasks_result[0] if isinstance(total_tasks_result, tuple) else total_tasks_result['total']
        
        # Get log count for this project
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            log_count_query = """
                SELECT COUNT(*) as total
                FROM log_entries le
                LEFT JOIN tasks t ON le.task_id = t.id
                WHERE (le.metadata->>'project_id' = %s) 
                   OR (t.project_id = %s)
            """
            params = [project_id, project_id]
        else:
            log_count_query = """
                SELECT COUNT(*) as total
                FROM log_entries le
                LEFT JOIN tasks t ON le.task_id = t.task_id
                WHERE (json_extract(le.metadata, '$.project_id') = ?) 
                   OR (t.project_id = ?)
            """
            params = [project_id, project_id]
        
        cursor = db.execute_query(log_count_query, params)
        log_count_result = cursor.fetchone()
        total_logs = log_count_result[0] if isinstance(log_count_result, tuple) else log_count_result['total']
        
        db.disconnect()
        
        # Format task statistics
        task_status_counts = {}
        for stat in task_stats:
            status = stat[0] if isinstance(stat, tuple) else stat['status']
            count = stat[1] if isinstance(stat, tuple) else stat['count']
            task_status_counts[status] = count
        
        # Format dates for JSON serialization
        def format_datetime(dt):
            if dt:
                return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
            return None
        
        return {
            'project_id': project_id,
            'project_created_at': format_datetime(project_created_at),
            'latest_log_at': format_datetime(latest_log_at),
            'total_tasks': total_tasks,
            'total_logs': total_logs,
            'task_status_counts': task_status_counts,
            'period': {
                'start': format_datetime(project_created_at),
                'end': format_datetime(latest_log_at) if latest_log_at else format_datetime(project_created_at),
                'active': latest_log_at is not None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add remaining endpoints here...

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='TracLine Web Application')
    parser.add_argument('-p', '--port', type=int, default=8001, help='Port number to run server on')
    
    args = parser.parse_args()
    
    # Display startup message
    print(f"\n{'='*60}")
    print(f"TracLine Web Interface Starting (FIXED VERSION)")
    print(f"{'='*60}")
    print(f"Server URL: http://localhost:{args.port}")
    print(f"API Endpoints:")
    print(f"  - Test: http://localhost:{args.port}/api/test")
    print(f"  - Endpoints: http://localhost:{args.port}/api/endpoints")
    print(f"  - Projects: http://localhost:{args.port}/api/projects")
    print(f"  - Settings: http://localhost:{args.port}/api/projects/{{project_id}}/settings")
    print(f"  - Matrix: http://localhost:{args.port}/api/traceability-matrix/enhanced")
    print(f"{'='*60}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=args.port)