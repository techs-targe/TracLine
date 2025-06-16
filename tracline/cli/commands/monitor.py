"""File system monitoring commands for TracLine."""

import click
import json
from pathlib import Path
from ...core.config import Config
from ...db.factory import DatabaseFactory
from ...monitor.daemon import MonitorDaemon
from tabulate import tabulate


@click.group()
def monitor():
    """Manage file system monitoring."""
    pass


@monitor.command()
@click.argument('project_id')
@click.argument('path', type=click.Path(exists=True))
@click.option('--daemon', '-d', is_flag=True, help='Run as background daemon')
@click.option('--extensions', '-e', multiple=True, help='File extensions to monitor (e.g., .py .js)')
def start(project_id, path, daemon, extensions):
    """Start monitoring a project directory.
    
    Example:
        tracline monitor start PROJECT1 /path/to/project --daemon
        tracline monitor start PROJECT1 . -d -e .py -e .js -e .ts
    """
    # Save monitoring settings
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        # Convert extensions to list
        ext_list = list(extensions) if extensions else None
        
        # Update project settings
        if config.config.database.type == "postgresql":
            query = """
            INSERT INTO project_settings (project_id, monitor_enabled, monitor_path, monitor_extensions)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (project_id) DO UPDATE
            SET monitor_enabled = EXCLUDED.monitor_enabled,
                monitor_path = EXCLUDED.monitor_path,
                monitor_extensions = EXCLUDED.monitor_extensions,
                updated_at = NOW()
            """
            params = [project_id, True, path, ext_list]
        else:
            # SQLite doesn't support arrays, so store as JSON
            query = """
            INSERT OR REPLACE INTO project_settings 
            (project_id, monitor_enabled, monitor_path, monitor_extensions, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            from datetime import datetime
            params = [project_id, True, path, json.dumps(ext_list) if ext_list else None, datetime.now().isoformat(), datetime.now().isoformat()]
            
        db.execute_query(query, params)
        db.conn.commit()
        
    finally:
        db.disconnect()
    
    # Start monitor
    monitor_daemon = MonitorDaemon(project_id, path)
    
    if daemon:
        monitor_daemon.start(as_daemon=True)
        click.echo(f"Started monitoring {path} for project {project_id} in background")
        click.echo(f"Use 'tracline monitor status' to check status")
    else:
        click.echo(f"Starting monitor for {path} (project: {project_id})")
        click.echo("Press Ctrl+C to stop...")
        monitor_daemon.start(as_daemon=False)


@monitor.command()
@click.argument('project_id')
def stop(project_id):
    """Stop monitoring a project."""
    monitor_daemon = MonitorDaemon(project_id, '.')  # Path not needed for stop
    
    if monitor_daemon.stop():
        click.echo(f"Stopped monitoring for project {project_id}")
        
        # Update database
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        
        try:
            db.connect()
            
            if config.config.database.type == "postgresql":
                query = "UPDATE project_settings SET monitor_enabled = false WHERE project_id = %s"
                params = [project_id]
            else:
                query = "UPDATE project_settings SET monitor_enabled = false WHERE project_id = ?"
                params = [project_id]
                
            db.execute_query(query, params)
            db.conn.commit()
            
        finally:
            db.disconnect()
    else:
        click.echo(f"No monitor running for project {project_id}", err=True)


@monitor.command()
def status():
    """Show status of all monitors."""
    monitors = MonitorDaemon.list_monitors()
    
    if not monitors:
        click.echo("No monitors running")
        return
        
    # Get additional info from database
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        monitor_data = []
        for mon in monitors:
            # Get project settings
            if config.config.database.type == "postgresql":
                query = "SELECT monitor_path, monitor_extensions FROM project_settings WHERE project_id = %s"
                params = [mon['project_id']]
            else:
                query = "SELECT monitor_path, monitor_extensions FROM project_settings WHERE project_id = ?"
                params = [mon['project_id']]
                
            cursor = db.execute_query(query, params)
            result = cursor.fetchone()
            
            if result:
                if isinstance(result, dict):
                    path = result['monitor_path']
                    extensions = result['monitor_extensions']
                else:
                    path = result[0]
                    extensions = json.loads(result[1]) if result[1] else []
            else:
                path = 'Unknown'
                extensions = []
                
            monitor_data.append({
                'Project': mon['project_id'],
                'Status': mon['status'],
                'PID': mon['pid'] or '-',
                'Path': path,
                'Extensions': ', '.join(extensions) if extensions else 'All'
            })
            
        click.echo("\nFile System Monitors:")
        click.echo(tabulate(monitor_data, headers='keys', tablefmt='grid'))
        
    finally:
        db.disconnect()


@monitor.command()
@click.argument('project_id')
def logs(project_id):
    """Show monitor logs for a project."""
    out_file = f'/tmp/tracline-monitor-{project_id}.out'
    err_file = f'/tmp/tracline-monitor-{project_id}.err'
    
    click.echo(f"=== Monitor logs for {project_id} ===\n")
    
    if Path(out_file).exists():
        click.echo("--- Standard Output ---")
        with open(out_file, 'r') as f:
            click.echo(f.read())
    else:
        click.echo("No output logs found")
        
    if Path(err_file).exists():
        click.echo("\n--- Error Output ---")
        with open(err_file, 'r') as f:
            content = f.read()
            if content.strip():
                click.echo(content)
            else:
                click.echo("No errors")
    else:
        click.echo("\nNo error logs found")


@monitor.command()
@click.argument('project_id')
@click.option('--limit', '-n', type=int, default=50, help='Number of recent accesses to show')
def history(project_id, limit):
    """Show file access history for a project."""
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        if config.config.database.type == "postgresql":
            query = """
            SELECT file_path, access_type, task_id, timestamp
            FROM file_access_log
            WHERE project_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """
            params = [project_id, limit]
        else:
            query = """
            SELECT file_path, access_type, task_id, timestamp
            FROM file_access_log
            WHERE project_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """
            params = [project_id, limit]
            
        cursor = db.execute_query(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            click.echo(f"No file access history for project {project_id}")
            return
            
        history_data = []
        for row in rows:
            if isinstance(row, dict):
                history_data.append({
                    'Time': str(row['timestamp'])[:19],
                    'Action': row['access_type'],
                    'File': row['file_path'],
                    'Task': row['task_id'] or '-'
                })
            else:
                history_data.append({
                    'Time': str(row[3])[:19],
                    'Action': row[1],
                    'File': row[0],
                    'Task': row[2] or '-'
                })
                
        click.echo(f"\nRecent file activity for project {project_id}:")
        click.echo(tabulate(history_data, headers='keys', tablefmt='grid'))
        
    finally:
        db.disconnect()