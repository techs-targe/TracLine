"""Enhanced traceability matrix API for TracLine Web."""

from fastapi import HTTPException, Query
from typing import Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def register_traceability_matrix_endpoints(app, task_service):
    """Register enhanced traceability matrix endpoints."""
    
    @app.get("/api/traceability-matrix/enhanced")
    async def get_enhanced_traceability_matrix(
        project_id: Optional[str] = Query(None, description="Filter by project ID"),
        file_extension: Optional[str] = Query(None, description="Filter by file extension (e.g., .py, .js)"),
        file_name_contains: Optional[str] = Query(None, description="Filter files containing this text"),
        task_name_contains: Optional[str] = Query(None, description="Filter tasks containing this text"),
        include_reference_counts: bool = Query(True, description="Include file reference counts")
    ):
        """Get enhanced traceability matrix with filtering and reference counts."""
        try:
            logger.info(f"Getting enhanced traceability matrix with filters: "
                       f"project={project_id}, ext={file_extension}, "
                       f"file_contains={file_name_contains}, task_contains={task_name_contains}")
            
            with task_service:
                # Get tasks with optional project filter
                filters = {}
                if project_id:
                    filters['project_id'] = project_id
                
                all_tasks = task_service.db.list_tasks(filters=filters)
                
                # Filter tasks by name if specified
                if task_name_contains:
                    all_tasks = [
                        task for task in all_tasks 
                        if task_name_contains.lower() in task.title.lower()
                    ]
                
                # Get all file associations
                all_files = set()
                task_files = {}
                file_reference_counts = {}
                
                for task in all_tasks:
                    files = task_service.db.get_file_associations(task.id)
                    task_file_paths = []
                    
                    for f in files:
                        file_path = f.file_path
                        
                        # Apply file filters
                        if file_extension:
                            if not file_path.endswith(file_extension):
                                continue
                        
                        if file_name_contains:
                            if file_name_contains.lower() not in file_path.lower():
                                continue
                        
                        task_file_paths.append(file_path)
                        all_files.add(file_path)
                        
                        # Count references
                        file_reference_counts[file_path] = file_reference_counts.get(file_path, 0) + 1
                    
                    task_files[task.id] = task_file_paths
                
                # Create matrix data
                sorted_files = sorted(list(all_files))
                
                matrix_data = {
                    "tasks": [
                        {
                            "id": t.id, 
                            "title": t.title,
                            "status": t.status,
                            "assignee": t.assignee,
                            "priority": t.priority
                        } for t in all_tasks
                    ],
                    "files": sorted_files,
                    "matrix": [],
                    "filters": {
                        "project_id": project_id,
                        "file_extension": file_extension,
                        "file_name_contains": file_name_contains,
                        "task_name_contains": task_name_contains
                    }
                }
                
                # Add reference counts if requested
                if include_reference_counts:
                    matrix_data["file_reference_counts"] = {
                        file: file_reference_counts.get(file, 0) 
                        for file in sorted_files
                    }
                
                # Build matrix
                for task in all_tasks:
                    row = []
                    for file_path in sorted_files:
                        row.append(1 if file_path in task_files.get(task.id, []) else 0)
                    matrix_data["matrix"].append(row)
                
                # Add summary statistics
                matrix_data["summary"] = {
                    "total_tasks": len(all_tasks),
                    "total_files": len(sorted_files),
                    "total_associations": sum(file_reference_counts.values()),
                    "avg_files_per_task": round(sum(file_reference_counts.values()) / len(all_tasks), 2) if all_tasks else 0,
                    "most_referenced_files": sorted(
                        [(f, c) for f, c in file_reference_counts.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]  # Top 10 most referenced files
                }
                
                return matrix_data
                
        except Exception as e:
            logger.error(f"Error in enhanced traceability matrix: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.get("/api/traceability-matrix/file-extensions")
    async def get_file_extensions(project_id: Optional[str] = None):
        """Get all unique file extensions in the project."""
        try:
            with task_service:
                filters = {}
                if project_id:
                    filters['project_id'] = project_id
                
                tasks = task_service.db.list_tasks(filters=filters)
                
                extensions = set()
                for task in tasks:
                    files = task_service.db.get_file_associations(task.id)
                    for f in files:
                        ext = Path(f.file_path).suffix
                        if ext:
                            extensions.add(ext)
                
                return sorted(list(extensions))
                
        except Exception as e:
            logger.error(f"Error getting file extensions: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.get("/api/traceability-matrix/file-stats")
    async def get_file_statistics(project_id: Optional[str] = None):
        """Get detailed file statistics for the project."""
        try:
            with task_service:
                filters = {}
                if project_id:
                    filters['project_id'] = project_id
                
                tasks = task_service.db.list_tasks(filters=filters)
                
                file_stats = {}
                extension_stats = {}
                
                for task in tasks:
                    files = task_service.db.get_file_associations(task.id)
                    for f in files:
                        file_path = f.file_path
                        ext = Path(file_path).suffix or 'no_extension'
                        
                        # File-level stats
                        if file_path not in file_stats:
                            file_stats[file_path] = {
                                'path': file_path,
                                'extension': ext,
                                'reference_count': 0,
                                'tasks': []
                            }
                        
                        file_stats[file_path]['reference_count'] += 1
                        file_stats[file_path]['tasks'].append({
                            'id': task.id,
                            'title': task.title,
                            'status': task.status
                        })
                        
                        # Extension-level stats
                        if ext not in extension_stats:
                            extension_stats[ext] = {
                                'extension': ext,
                                'file_count': 0,
                                'total_references': 0
                            }
                        
                        extension_stats[ext]['total_references'] += 1
                
                # Count unique files per extension
                for file_path, stats in file_stats.items():
                    ext = stats['extension']
                    extension_stats[ext]['file_count'] += 1
                
                return {
                    'file_stats': list(file_stats.values()),
                    'extension_stats': list(extension_stats.values()),
                    'total_files': len(file_stats),
                    'total_references': sum(s['reference_count'] for s in file_stats.values())
                }
                
        except Exception as e:
            logger.error(f"Error getting file statistics: {e}")
            raise HTTPException(status_code=500, detail=str(e))