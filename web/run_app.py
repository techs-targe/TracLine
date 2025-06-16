#!/usr/bin/env python3
"""Run TracLine Web Interface with the configured database."""

import sys
import os
from pathlib import Path

# Ensure we're using the correct path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.requests import Request
from pathlib import Path
import json
import base64
from typing import List, Optional, Dict, Any
import uvicorn
from datetime import datetime

from tracline.core.config import Config, DatabaseConfig
from tracline.core.task_service import TaskService
from tracline.core.team_service import TeamService
from tracline.models import Task, TaskStatus, TaskPriority, Member, Project, ProjectMembership, TaskRelationship, FileAssociation
from tracline.models.member import Member
from tracline.models.project import Project
from tracline.db.factory import DatabaseFactory
from tracline.db.postgresql import PostgreSQLDatabase
from tracline.db.sqlite import SQLiteDatabase

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app
app = FastAPI(title="TracLine Web Interface")

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Register database implementations
DatabaseFactory.register("postgresql", PostgreSQLDatabase)
DatabaseFactory.register("sqlite", SQLiteDatabase)

# Try to load configuration
try:
    cli_config_path = os.environ.get("TRACLINE_CONFIG", None)
    config = Config(config_path=cli_config_path)
    logger.info(f"Using configuration: {config.config_path}")
    
    # Log the database configuration
    db_type = config.config.database.type
    logger.info(f"Database type: {db_type}")
    
    # Use model_dump if available (newer Pydantic), otherwise fall back to dict
    if hasattr(config.config.database, 'model_dump'):
        db_settings = config.config.database.model_dump()
    else:
        db_settings = config.config.database.dict()
        
    logger.info(f"Database settings: {db_settings}")
except Exception as e:
    logger.warning(f"Failed to load configuration: {e}. Using default configuration.")
    config = Config()
    logger.info(f"Using default database configuration: {config.config.database.type}")

# Create database connection using the configured type
db = DatabaseFactory.create(config.config.database)

# Initialize services
task_service = TaskService(config, db)
team_service = TeamService(config, db)

# Create minimal test data if database is empty
with db:
    # Check if we have any projects and tasks
    if db_type == "postgresql":
        try:
            # Check projects
            db.cursor.execute("SELECT COUNT(*) FROM projects")
            project_count = db.cursor.fetchone()[0]
            
            # Check tasks
            db.cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = db.cursor.fetchone()[0]
            
            # Check members
            db.cursor.execute("SELECT COUNT(*) FROM members")
            member_count = db.cursor.fetchone()[0]
            
            if project_count == 0:
                logger.info("No projects found. Creating minimal test data...")
                
                # Create test projects
                from tracline.models.project import Project
                
                projects = [
                    Project(id="test-project", name="Test Project", description="A test project"),
                    Project(id="comm-app-dev", name="Communication App Development", description="Communication app development project"),
                    Project(id="frontend-app", name="Frontend App", description="Frontend application development"),
                    Project(id="backend-api", name="Backend API", description="Backend API development"),
                    Project(id="mobile-app", name="Mobile App", description="Mobile application development"),
                    Project(id="data-analytics", name="Data Analytics", description="Data analytics platform")
                ]
                
                for project in projects:
                    db.create_project(project)
                
                logger.info(f"Created {len(projects)} test projects successfully")
            else:
                logger.info(f"Found {project_count} existing projects.")
            
            # Create test members if none exist
            if member_count == 0:
                logger.info("No members found. Creating test members...")
                
                from tracline.models.member import Member, MemberRole, MemberPosition
                
                members = [
                    Member(id="tech-leader", name="Tech Leader", role="DEVELOPER", position="LEADER"),
                    Member(id="sub-leader-1", name="Sub Leader 1", role="DEVELOPER", position="SUB_LEADER", leader_id="tech-leader"),
                    Member(id="sub-leader-2", name="Sub Leader 2", role="DEVELOPER", position="SUB_LEADER", leader_id="tech-leader"),
                    Member(id="dev-1", name="Developer 1", role="DEVELOPER", position="MEMBER", leader_id="sub-leader-1"),
                    Member(id="dev-2", name="Developer 2", role="DEVELOPER", position="MEMBER", leader_id="sub-leader-1"),
                    Member(id="dev-3", name="Developer 3", role="DEVELOPER", position="MEMBER", leader_id="sub-leader-2"),
                    Member(id="dev-4", name="Developer 4", role="DEVELOPER", position="MEMBER", leader_id="sub-leader-2"),
                    Member(id="dev-5", name="Developer 5", role="DEVELOPER", position="MEMBER", leader_id="sub-leader-1"),
                    Member(id="dev-6", name="Developer 6", role="DEVELOPER", position="MEMBER", leader_id="sub-leader-2"),
                    Member(id="dev-7", name="Developer 7", role="TESTER", position="MEMBER", leader_id="tech-leader"),
                    Member(id="dev-8", name="Developer 8", role="TESTER", position="MEMBER", leader_id="tech-leader"),
                ]
                
                for member in members:
                    try:
                        db.create_member(member)
                    except Exception as e:
                        logger.warning(f"Failed to create member {member.id}: {e}")
                
                # Add members to projects
                for project in ["frontend-app", "backend-api", "mobile-app", "data-analytics"]:
                    for member_id in ["tech-leader", "sub-leader-1", "sub-leader-2", "dev-1", "dev-2", "dev-3", "dev-4"]:
                        try:
                            db.add_project_member(project, member_id)
                        except Exception as e:
                            logger.warning(f"Failed to add member {member_id} to project {project}: {e}")
                
                logger.info(f"Created {len(members)} test members successfully")
            else:
                logger.info(f"Found {member_count} existing members.")
            
            # Create test tasks if none exist
            if task_count == 0:
                logger.info("No tasks found. Creating test tasks...")
                
                from tracline.models.task import Task, TaskStatus, TaskPriority
                from datetime import datetime, timedelta
                import uuid
                
                # Create 5 tasks for each project with different assignees
                projects = ["frontend-app", "backend-api", "mobile-app", "data-analytics"]
                assignees = ["dev-1", "dev-2", "dev-3", "dev-4", "dev-5", "dev-6", "dev-7", "dev-8"]
                statuses = ["TODO", "READY", "DOING", "TESTING", "DONE"]
                
                tasks_created = 0
                
                for project_id in projects:
                    for i in range(5):
                        try:
                            task_id = f"task-{uuid.uuid4().hex[:8]}"
                            status = statuses[i % len(statuses)]
                            assignee = assignees[i % len(assignees)]
                            
                            task = Task(
                                id=task_id,
                                title=f"Task {i+1} for {project_id}",
                                description=f"This is a test task {i+1} for project {project_id}",
                                status=status,
                                assignee=assignee,
                                priority=i % 3 + 1,
                                project_id=project_id,
                                due_date=datetime.now() + timedelta(days=i+10)
                            )
                            
                            db.create_task(task)
                            tasks_created += 1
                            
                        except Exception as e:
                            logger.warning(f"Failed to create task {i+1} for project {project_id}: {e}")
                
                logger.info(f"Created {tasks_created} test tasks successfully")
            else:
                logger.info(f"Found {task_count} existing tasks.")
                
        except Exception as e:
            logger.error(f"Error creating test data: {e}")
    else:
        logger.info(f"Using {db_type} database. Skipping test data creation.")

# Ensure static directories exist
static_dir = Path(__file__).parent / 'static'
static_dir.mkdir(exist_ok=True)
images_dir = static_dir / 'images'
images_dir.mkdir(exist_ok=True)

# If running from a different directory, also create relative dirs
rel_static_dir = Path('static')
rel_static_dir.mkdir(exist_ok=True)
rel_images_dir = rel_static_dir / 'images'
rel_images_dir.mkdir(exist_ok=True)

# Copy sample images from BACKUP if available
backup_images = Path(__file__).parent.parent / 'BACKUP' / 'web' / 'static' / 'images'
if backup_images.exists():
    import shutil
    for img in backup_images.glob('*.jpg'):
        try:
            shutil.copy(img, images_dir)
            # Also copy to relative path
            shutil.copy(img, rel_images_dir)
            logger.info(f"Copied sample image: {img.name}")
        except Exception as e:
            logger.warning(f"Failed to copy image {img.name}: {e}")

# Import API routes from app.py
from app import (
    index,
    get_projects,
    get_team_hierarchy,
    get_member,
    upload_member_photo,
    get_task,
    update_task_status,
    update_task_assignee,
    get_tasks,
    get_database_info,
    get_enhanced_traceability_matrix
)

# Register routes
app.get("/")(index)
app.get("/api/projects")(get_projects)
app.get("/api/projects/{project_id}/members")(get_team_hierarchy)
app.get("/api/members/{member_id}")(get_member)
app.post("/api/members/{member_id}/upload-photo")(upload_member_photo)
app.get("/api/tasks/{task_id}")(get_task)
app.put("/api/tasks/{task_id}/status")(update_task_status)
app.put("/api/tasks/{task_id}/assignee")(update_task_assignee)
app.get("/api/tasks")(get_tasks)
app.get("/api/database-info")(get_database_info)
app.get("/api/traceability-matrix")(get_enhanced_traceability_matrix)
app.get("/api/team-hierarchy/{project_id}")(get_team_hierarchy)
# WebSocket functionality not implemented

def main():
    """Run the app."""
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description="TracLine Web Interface")
    parser.add_argument('-p', '--port', type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument('--host', default="0.0.0.0", help="Host to bind the server to (default: 0.0.0.0)")
    
    # Parse arguments
    args = parser.parse_args()
    
    db_type = config.config.database.type
    logger.info(f"Starting TracLine Web Interface with {db_type.upper()} database on port {args.port}...")
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()