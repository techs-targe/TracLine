"""Project root configuration commands."""

import logging
from pathlib import Path
import click
from tracline.core.config import Config
from tracline.db.factory import DatabaseFactory

logger = logging.getLogger(__name__)


@click.group(help='Project root directory configuration')
def projectroot():
    """Manage project root directory settings."""
    pass


@projectroot.command('set')
@click.argument('project_id')
@click.argument('root_path')
@click.option('--force', '-f', is_flag=True, help='Force set even if directory does not exist')
def set_project_root(project_id, root_path, force):
    """Set the project root directory for a project.
    
    This allows file associations to use relative paths instead of absolute paths.
    
    \b
    Arguments:
        PROJECT_ID: The project identifier
        ROOT_PATH: The absolute path to the project root directory
    
    \b
    Examples:
        tracline projectroot set MY-PROJECT /home/user/projects/myproject
        tracline projectroot set MY-PROJECT /Users/john/work/project --force
    """
    try:
        # Validate path
        path = Path(root_path).resolve()
        
        if not force and not path.exists():
            click.echo(f"Error: Directory does not exist: {root_path}", err=True)
            click.echo("Use --force to set anyway", err=True)
            return
        
        if not force and not path.is_dir():
            click.echo(f"Error: Path is not a directory: {root_path}", err=True)
            click.echo("Use --force to set anyway", err=True)
            return
        
        # Get database connection
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Check if project exists
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            check_query = "SELECT id FROM projects WHERE id = %s"
            check_params = [project_id]
        else:
            check_query = "SELECT id FROM projects WHERE id = ?"
            check_params = [project_id]
        
        cursor = db.execute_query(check_query, check_params)
        if not cursor.fetchone():
            click.echo(f"Error: Project not found: {project_id}", err=True)
            db.disconnect()
            return
        
        # Update project root
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            # Check if settings exist
            check_settings_query = "SELECT project_id FROM project_settings WHERE project_id = %s"
            cursor = db.execute_query(check_settings_query, [project_id])
            
            if cursor.fetchone():
                # Update existing
                update_query = "UPDATE project_settings SET project_root = %s WHERE project_id = %s"
                params = [str(path), project_id]
            else:
                # Insert new
                update_query = """INSERT INTO project_settings (project_id, project_root, 
                                 strict_doc_read, strict_file_ref, strict_log_entry,
                                 github_enabled, monitor_enabled, monitor_interval)
                                 VALUES (%s, %s, false, false, false, false, false, 60)"""
                params = [project_id, str(path)]
        else:
            # SQLite
            check_settings_query = "SELECT project_id FROM project_settings WHERE project_id = ?"
            cursor = db.execute_query(check_settings_query, [project_id])
            
            if cursor.fetchone():
                # Update existing
                update_query = "UPDATE project_settings SET project_root = ? WHERE project_id = ?"
                params = [str(path), project_id]
            else:
                # Insert new
                update_query = """INSERT INTO project_settings (project_id, project_root,
                                 strict_doc_read, strict_file_ref, strict_log_entry,
                                 github_enabled, monitor_enabled, monitor_interval)
                                 VALUES (?, ?, 0, 0, 0, 0, 0, 60)"""
                params = [project_id, str(path)]
        
        db.execute_query(update_query, params)
        
        # Commit changes
        if hasattr(db, 'conn'):
            db.conn.commit()
        elif hasattr(db, 'connection'):
            db.connection.commit()
        
        db.disconnect()
        
        click.echo(f"✓ Project root set successfully for {project_id}")
        click.echo(f"  Path: {path}")
        
        if not path.exists():
            click.echo("  ⚠️  Warning: Directory does not exist")
        
    except Exception as e:
        logger.error(f"Error setting project root: {e}")
        click.echo(f"Error: {e}", err=True)


@projectroot.command('get')
@click.argument('project_id')
def get_project_root(project_id):
    """Get the current project root directory for a project.
    
    \b
    Arguments:
        PROJECT_ID: The project identifier
    
    \b
    Example:
        tracline projectroot get MY-PROJECT
    """
    try:
        # Get database connection
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Get project root
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            query = "SELECT project_root FROM project_settings WHERE project_id = %s"
            params = [project_id]
        else:
            query = "SELECT project_root FROM project_settings WHERE project_id = ?"
            params = [project_id]
        
        cursor = db.execute_query(query, params)
        row = cursor.fetchone()
        
        db.disconnect()
        
        if not row:
            click.echo(f"No project root configured for project: {project_id}")
            return
        
        project_root = row[0] if isinstance(row, tuple) else row.get('project_root')
        
        if not project_root:
            click.echo(f"No project root configured for project: {project_id}")
        else:
            click.echo(f"Project root for {project_id}: {project_root}")
            
            # Check if it exists
            path = Path(project_root)
            if not path.exists():
                click.echo("  ⚠️  Warning: Directory does not exist", err=True)
            elif not path.is_dir():
                click.echo("  ⚠️  Warning: Path is not a directory", err=True)
        
    except Exception as e:
        logger.error(f"Error getting project root: {e}")
        click.echo(f"Error: {e}", err=True)


@projectroot.command('clear')
@click.argument('project_id')
@click.option('--confirm', is_flag=True, help='Confirm clearing project root')
def clear_project_root(project_id, confirm):
    """Clear the project root directory setting for a project.
    
    This will require all file associations to use absolute paths.
    
    \b
    Arguments:
        PROJECT_ID: The project identifier
    
    \b
    Example:
        tracline projectroot clear MY-PROJECT --confirm
    """
    if not confirm:
        click.echo("Are you sure you want to clear the project root?")
        click.echo("This will require all file associations to use absolute paths.")
        click.echo("Use --confirm to proceed.", err=True)
        return
    
    try:
        # Get database connection
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Clear project root
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            update_query = "UPDATE project_settings SET project_root = '' WHERE project_id = %s"
            params = [project_id]
        else:
            update_query = "UPDATE project_settings SET project_root = '' WHERE project_id = ?"
            params = [project_id]
        
        cursor = db.execute_query(update_query, params)
        
        # Check if any rows were updated
        if cursor.rowcount == 0:
            click.echo(f"No project settings found for project: {project_id}")
        else:
            # Commit changes
            if hasattr(db, 'conn'):
                db.conn.commit()
            elif hasattr(db, 'connection'):
                db.connection.commit()
            
            click.echo(f"✓ Project root cleared for {project_id}")
        
        db.disconnect()
        
    except Exception as e:
        logger.error(f"Error clearing project root: {e}")
        click.echo(f"Error: {e}", err=True)


@projectroot.command('list')
def list_project_roots():
    """List all projects with configured root directories.
    
    \b
    Example:
        tracline projectroot list
    """
    try:
        # Get database connection
        config = Config()
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        # Get all project roots
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            query = """SELECT ps.project_id, ps.project_root, p.name 
                      FROM project_settings ps
                      LEFT JOIN projects p ON ps.project_id = p.id
                      WHERE ps.project_root IS NOT NULL AND ps.project_root != ''
                      ORDER BY ps.project_id"""
        else:
            query = """SELECT ps.project_id, ps.project_root, p.name 
                      FROM project_settings ps
                      LEFT JOIN projects p ON ps.project_id = p.id
                      WHERE ps.project_root IS NOT NULL AND ps.project_root != ''
                      ORDER BY ps.project_id"""
        
        cursor = db.execute_query(query)
        rows = cursor.fetchall()
        
        db.disconnect()
        
        if not rows:
            click.echo("No projects have configured root directories.")
            return
        
        click.echo("\nProjects with configured root directories:")
        click.echo("-" * 80)
        
        for row in rows:
            if isinstance(row, dict):
                project_id = row['project_id']
                project_root = row['project_root']
                project_name = row.get('name', 'Unknown')
            else:
                project_id = row[0]
                project_root = row[1]
                project_name = row[2] if row[2] else 'Unknown'
            
            # Check if path exists
            status = ""
            if project_root:
                path = Path(project_root)
                if not path.exists():
                    status = " [⚠️  Does not exist]"
                elif not path.is_dir():
                    status = " [⚠️  Not a directory]"
                else:
                    status = " [✓ Valid]"
            
            click.echo(f"\nProject: {project_id} ({project_name})")
            click.echo(f"Root:    {project_root}{status}")
        
        click.echo("\n" + "-" * 80)
        
    except Exception as e:
        logger.error(f"Error listing project roots: {e}")
        click.echo(f"Error: {e}", err=True)