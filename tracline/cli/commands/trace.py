"""Traceability commands for TracLine."""

import click
from pathlib import Path
from ...core.config import Config
from ...db.factory import DatabaseFactory
# from ...utils import format_task_table, format_date
import os


@click.group()
def trace():
    """Manage file traceability."""
    pass


@trace.command("ls-trace")
@click.argument("file_path")
@click.option("--project", "-p", help="Filter by project ID")
@click.option("--status", "-s", help="Filter by task status")
@click.option("--format", "-f", type=click.Choice(["table", "list", "json"]), default="table", help="Output format")
def list_trace(file_path, project, status, format):
    """List tasks that reference a specific file.
    
    Example:
        tracline trace ls-trace hello.c
        tracline trace ls-trace src/main.py -p PROJECT1
        tracline trace ls-trace test.js --status TODO
    """
    # Normalize file path
    abs_path = Path(file_path).absolute()
    rel_path = file_path
    
    # Check if file exists
    file_exists = abs_path.exists()
    
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        # Query to find all tasks that reference this file
        if config.config.database.type == "postgresql":
            query = """
            SELECT DISTINCT t.id, t.title, t.status, t.assignee, t.priority, 
                   t.project_id, t.created_at, t.updated_at,
                   fa.created_at as associated_at
            FROM tasks t
            JOIN file_associations fa ON t.id = fa.task_id
            WHERE (fa.file_path = %s OR fa.file_path = %s)
            """
            params = [str(abs_path), rel_path]
            
            if project:
                query += " AND t.project_id = %s"
                params.append(project)
            
            if status:
                query += " AND t.status = %s"
                params.append(status)
                
            query += " ORDER BY fa.created_at DESC"
            
        else:  # SQLite
            query = """
            SELECT DISTINCT t.id, t.title, t.status, t.assignee, t.priority, 
                   t.project_id, t.created_at, t.updated_at,
                   fa.created_at as associated_at
            FROM tasks t
            JOIN file_associations fa ON t.id = fa.task_id
            WHERE (fa.file_path = ? OR fa.file_path = ?)
            """
            params = [str(abs_path), rel_path]
            
            if project:
                query += " AND t.project_id = ?"
                params.append(project)
            
            if status:
                query += " AND t.status = ?"
                params.append(status)
                
            query += " ORDER BY fa.created_at DESC"
        
        cursor = db.execute_query(query, params)
        rows = cursor.fetchall()
        
        if format == "json":
            import json
            tasks = []
            for row in rows:
                if isinstance(row, dict):
                    task = {
                        "task_id": row.get('id', row.get('task_id')),
                        "title": row['title'],
                        "status": row['status'],
                        "assignee": row['assignee'],
                        "priority": row['priority'],
                        "project_id": row['project_id'],
                        "created_at": str(row['created_at']) if row.get('created_at') else None,
                        "updated_at": str(row['updated_at']) if row.get('updated_at') else None,
                        "associated_at": str(row['associated_at']) if row.get('associated_at') else None
                    }
                else:
                    task = {
                        "task_id": row[0],
                        "title": row[1],
                        "status": row[2],
                        "assignee": row[3],
                        "priority": row[4],
                        "project_id": row[5],
                        "created_at": str(row[6]) if row[6] else None,
                        "updated_at": str(row[7]) if row[7] else None,
                        "associated_at": str(row[8]) if row[8] else None
                    }
                tasks.append(task)
            click.echo(json.dumps(tasks, indent=2))
            
        elif format == "list":
            if not rows:
                click.echo(f"No tasks reference '{file_path}'")
            else:
                click.echo(f"\nTasks referencing '{file_path}':")
                if not file_exists:
                    click.echo(click.style("⚠️  Warning: File does not exist", fg="yellow"))
                click.echo(f"Found {len(rows)} task(s)\n")
                
                for row in rows:
                    if isinstance(row, dict):
                        task_id = row.get('id', row.get('task_id'))
                        title = row['title']
                        status = row['status']
                        assignee = row['assignee']
                        project = row['project_id']
                    else:
                        task_id = row[0]
                        title = row[1]
                        status = row[2]
                        assignee = row[3]
                        project = row[5]
                    
                    click.echo(f"• [{task_id}] {title}")
                    click.echo(f"  Status: {status}, Assignee: {assignee or 'Unassigned'}, Project: {project}")
                    
        else:  # table format
            if not rows:
                click.echo(f"No tasks reference '{file_path}'")
            else:
                # Convert rows to list of dicts for table formatting
                tasks = []
                for row in rows:
                    if isinstance(row, dict):
                        tasks.append(row)
                    else:
                        tasks.append({
                            "ID": row[0],
                            "Title": row[1],
                            "Status": row[2],
                            "Assignee": row[3] or "-",
                            "Priority": row[4],
                            "Project": row[5],
                            "Associated": str(row[8])[:10] if row[8] else "-"
                        })
                
                click.echo(f"\nTasks referencing '{file_path}':")
                if not file_exists:
                    click.echo(click.style("⚠️  Warning: File does not exist", fg="yellow"))
                    
                # Use format_task_table utility if available
                from tabulate import tabulate
                click.echo(tabulate(tasks, headers="keys", tablefmt="grid"))
                
    finally:
        db.disconnect()


@trace.command("add-file")
@click.argument("task_id")
@click.argument("file_path")
def add_file(task_id, file_path):
    """Add a file association to a task."""
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        # Check if task exists
        task = db.get_task(task_id)
        if not task:
            click.echo(f"Error: Task '{task_id}' not found", err=True)
            return
        
        # Add file association
        from ...models.file_association import FileAssociation
        # Convert to absolute path
        abs_path = Path(file_path).resolve()
        association = FileAssociation(
            task_id=task_id,
            file_path=str(abs_path)
        )
        
        db.add_file_association(association)
        
        # Commit the transaction
        if hasattr(db, 'commit'):
            db.commit()
        elif hasattr(db, 'conn') and hasattr(db.conn, 'commit'):
            db.conn.commit()
            
        click.echo(f"Added file '{file_path}' to task '{task_id}'")
        
    finally:
        db.disconnect()


@trace.command("remove-file")  
@click.argument("task_id")
@click.argument("file_path")
def remove_file(task_id, file_path):
    """Remove a file association from a task."""
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        # Remove file association
        if config.config.database.type == "postgresql":
            query = "DELETE FROM file_associations WHERE task_id = %s AND file_path = %s"
            params = [task_id, file_path]
        else:
            query = "DELETE FROM file_associations WHERE task_id = ? AND file_path = ?"
            params = [task_id, file_path]
            
        cursor = db.execute_query(query, params)
        
        if db.conn.commit:
            db.conn.commit()
            
        click.echo(f"Removed file '{file_path}' from task '{task_id}'")
        
    finally:
        db.disconnect()


@trace.command("stats")
@click.option("--project", "-p", help="Filter by project ID")
@click.option("--top", "-t", type=int, default=10, help="Show top N referenced files")
def stats(project, top):
    """Show file reference statistics."""
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        # Query to get file reference counts
        if config.config.database.type == "postgresql":
            query = """
            SELECT fa.file_path, COUNT(DISTINCT fa.task_id) as task_count,
                   COUNT(DISTINCT t.assignee) as assignee_count,
                   COUNT(DISTINCT t.project_id) as project_count
            FROM file_associations fa
            JOIN tasks t ON fa.task_id = t.task_id
            """
            params = []
            
            if project:
                query += " WHERE t.project_id = %s"
                params.append(project)
                
            query += f" GROUP BY fa.file_path ORDER BY task_count DESC LIMIT %s"
            params.append(top)
            
        else:  # SQLite
            query = """
            SELECT fa.file_path, COUNT(DISTINCT fa.task_id) as task_count,
                   COUNT(DISTINCT t.assignee) as assignee_count,
                   COUNT(DISTINCT t.project_id) as project_count
            FROM file_associations fa
            JOIN tasks t ON fa.task_id = t.task_id
            """
            params = []
            
            if project:
                query += " WHERE t.project_id = ?"
                params.append(project)
                
            query += f" GROUP BY fa.file_path ORDER BY task_count DESC LIMIT ?"
            params.append(top)
        
        cursor = db.execute_query(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            click.echo("No file associations found")
        else:
            click.echo(f"\nTop {min(len(rows), top)} referenced files:")
            if project:
                click.echo(f"Project: {project}")
            click.echo()
            
            # Format as table
            stats_data = []
            for i, row in enumerate(rows, 1):
                if isinstance(row, dict):
                    stats_data.append({
                        "#": i,
                        "File": row['file_path'],
                        "Tasks": row['task_count'],
                        "Assignees": row['assignee_count'],
                        "Projects": row['project_count']
                    })
                else:
                    stats_data.append({
                        "#": i,
                        "File": row[0],
                        "Tasks": row[1],
                        "Assignees": row[2],
                        "Projects": row[3]
                    })
            
            from tabulate import tabulate
            click.echo(tabulate(stats_data, headers="keys", tablefmt="grid"))
            
    finally:
        db.disconnect()