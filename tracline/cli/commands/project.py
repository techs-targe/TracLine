"""Project management commands for TracLine."""

import click
import json
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from tracline.core import Config, TeamService
from tracline.models import Member, Project


@click.command()
@click.argument('project_id')
@click.argument('name')
@click.option('--description', '-d', help='Project description')
@click.option('--owner', '-o', help='Project owner member ID')
@click.pass_context
def create(ctx, project_id, name, description, owner):
    """Create a new project."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        try:
            project = service.create_project(
                project_id=project_id,
                name=name,
                description=description,
                owner_id=owner
            )
            
            console.print(f"[green]✓ Project {project_id} created successfully[/green]")
            
            # Show project summary
            table = Table(box=None)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("ID", project.id)
            table.add_row("Name", project.name)
            table.add_row("Description", project.description or "N/A")
            table.add_row("Owner", project.owner_id or "None")
            table.add_row("Status", project.status)
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error creating project: {e}[/red]")


@click.command()
@click.argument('project_id')
@click.option('--name', help='New project name')
@click.option('--description', help='New project description')
@click.option('--owner', help='New project owner ID')
@click.option('--status', help='New project status')
@click.pass_context
def update(ctx, project_id, name, description, owner, status):
    """Update project information."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    from tracline.cli.commands.fixes import safe_update_project
    
    updates = {}
    if name:
        updates['name'] = name
    if description:
        updates['description'] = description
    if owner:
        updates['owner_id'] = owner
    if status:
        updates['status'] = status
    
    if not updates:
        console.print("[yellow]No updates provided[/yellow]")
        return
    
    with TeamService(config) as service:
        # Get the project first
        project = service.get_project(project_id)
        if not project:
            console.print(f"[red]Project {project_id} not found[/red]")
            return
            
        # Apply updates to project object
        for key, value in updates.items():
            setattr(project, key, value)
            
        # Use safe version that handles database-specific issues
        updated = safe_update_project(service.db, project)
        
        if updated:
            console.print(f"[green]✓ Project {project_id} updated successfully[/green]")
        else:
            console.print(f"[red]Failed to update project {project_id}[/red]")


@click.command()
@click.argument('project_id')
@click.option('--force', is_flag=True, help='Force deletion without confirmation')
@click.pass_context
def delete(ctx, project_id, force):
    """Delete a project."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        project = service.get_project(project_id)
        if not project:
            console.print(f"[red]Project {project_id} not found[/red]")
            return
        
        if not force:
            if not click.confirm(f"Are you sure you want to delete project '{project.name}'?"):
                console.print("[yellow]Deletion cancelled[/yellow]")
                return
        
        if service.delete_project(project_id):
            console.print(f"[green]✓ Project {project_id} deleted successfully[/green]")
        else:
            console.print(f"[red]Error deleting project[/red]")


@click.command()
@click.argument('project_id')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def show(ctx, project_id, as_json):
    """Show project details."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        project = service.get_project(project_id)
        if not project:
            console.print(f"[red]Project {project_id} not found[/red]")
            return
        
        if as_json:
            console.print(json.dumps(project.to_dict(), indent=2))
            return
        
        # Show project details
        panel = Panel(
            f"[bold]{project.name}[/bold]\n"
            f"{project.description or 'No description'}\n"
            f"Status: {project.status}",
            title=f"Project: {project.id}"
        )
        console.print(panel)
        
        table = Table(box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("ID", project.id)
        table.add_row("Name", project.name)
        table.add_row("Description", project.description or "N/A")
        table.add_row("Owner", project.owner_id or "None")
        table.add_row("Status", project.status)
        table.add_row("Created", project.created_at.strftime("%Y-%m-%d %H:%M:%S") if project.created_at else "N/A")
        table.add_row("Updated", project.updated_at.strftime("%Y-%m-%d %H:%M:%S") if project.updated_at else "N/A")
        
        console.print(table)
        
        # Show project members
        members = service.get_project_members(project_id)
        if members:
            console.print("\n[bold]Members:[/bold]")
            member_table = Table(box=None)
            member_table.add_column("ID", style="cyan")
            member_table.add_column("Name", style="white")
            member_table.add_column("Role", style="yellow")
            member_table.add_column("Position", style="green")
            
            for member in members:
                member_table.add_row(
                    member.id, member.name, member.role, member.position
                )
            
            console.print(member_table)


@click.command(name='list')
@click.option('--owner', help='Filter by owner ID')
@click.option('--status', help='Filter by status')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def list_projects(ctx, owner, status, as_json):
    """List all projects."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    filters = {}
    if owner:
        filters['owner_id'] = owner
    if status:
        filters['status'] = status
    
    with TeamService(config) as service:
        projects = service.list_projects(filters=filters)
        
        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            return
        
        if as_json:
            console.print(json.dumps([p.to_dict() for p in projects], indent=2))
            return
        
        # Create table
        table = Table(title=f"Projects ({len(projects)} found)", box=None)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Owner", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Created", style="blue")
        
        for project in projects:
            table.add_row(
                project.id,
                project.name,
                project.owner_id or "-",
                project.status,
                project.created_at.strftime("%Y-%m-%d")
            )
        
        console.print(table)


@click.command()
@click.argument('project_id')
@click.argument('member_ids', nargs=-1, required=True)
@click.pass_context
def add_members(ctx, project_id, member_ids):
    """Add members to a project."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        project = service.get_project(project_id)
        if not project:
            console.print(f"[red]Project {project_id} not found[/red]")
            return
        
        success_count = 0
        for member_id in member_ids:
            try:
                service.add_project_member(project_id, member_id)
                console.print(f"[green]✓ Added {member_id} to project[/green]")
                success_count += 1
            except Exception as e:
                console.print(f"[red]Error adding {member_id}: {e}[/red]")
        
        console.print(f"\n[bold]Added {success_count}/{len(member_ids)} members[/bold]")


@click.command()
@click.argument('project_id')
@click.argument('member_ids', nargs=-1, required=True)
@click.pass_context
def remove_members(ctx, project_id, member_ids):
    """Remove members from a project."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        project = service.get_project(project_id)
        if not project:
            console.print(f"[red]Project {project_id} not found[/red]")
            return
        
        success_count = 0
        for member_id in member_ids:
            if service.remove_project_member(project_id, member_id):
                console.print(f"[green]✓ Removed {member_id} from project[/green]")
                success_count += 1
            else:
                console.print(f"[red]Error removing {member_id}[/red]")
        
        console.print(f"\n[bold]Removed {success_count}/{len(member_ids)} members[/bold]")


@click.command()
@click.argument('project_id')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
@click.pass_context
def members(ctx, project_id, as_json):
    """Show project members."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    from tracline.cli.commands.fixes import safe_get_project_members
    
    with TeamService(config) as service:
        project = service.get_project(project_id)
        if not project:
            console.print(f"[red]Project {project_id} not found[/red]")
            return
        
        # Use safe version that handles database-specific issues
        members = safe_get_project_members(service.db, project_id)
        
        if not members:
            console.print(f"[yellow]No members in project {project.name}[/yellow]")
            return
        
        if as_json:
            console.print(json.dumps([m.to_dict() for m in members], indent=2))
            return
        
        console.print(f"[bold]Members of {project.name}:[/bold]")
        
        # Display hierarchically if possible
        leaders = [m for m in members if getattr(m, 'position', '') == "LEADER"]
        sub_leaders = [m for m in members if getattr(m, 'position', '') == "SUB_LEADER"]
        members_only = [m for m in members if getattr(m, 'position', '') == "MEMBER"]
        
        def print_member(member, indent=0):
            name = getattr(member, 'name', 'Unknown')
            role = getattr(member, 'role', 'Unknown')
            console.print("  " * indent + f"• {name} ({role})")
        
        for leader in leaders:
            print_member(leader)
            # Find sub-leaders under this leader
            for sub in sub_leaders:
                if getattr(sub, 'leader_id', None) == leader.id:
                    print_member(sub, 1)
                    # Find members under this sub-leader
                    for member in members_only:
                        if getattr(member, 'leader_id', None) == sub.id:
                            print_member(member, 2)
            # Find direct members under this leader
            for member in members_only:
                if getattr(member, 'leader_id', None) == leader.id:
                    print_member(member, 1)
        
        # Print any orphaned members
        orphans = []
        for sub in sub_leaders:
            if not any(getattr(sub, 'leader_id', None) == l.id for l in leaders):
                orphans.append(sub)
        for member in members_only:
            if not any(getattr(member, 'leader_id', None) == m.id for m in members if hasattr(m, 'id')):
                orphans.append(member)
        
        if orphans:
            console.print("\n[dim]Other members:[/dim]")
            for member in orphans:
                print_member(member)


@click.command()
@click.argument('project_id')
@click.option('--strict-doc-read/--no-strict-doc-read', default=None, help='Enable/disable document read enforcement')
@click.option('--strict-file-ref/--no-strict-file-ref', default=None, help='Enable/disable file reference enforcement')
@click.option('--strict-log-entry/--no-strict-log-entry', default=None, help='Enable/disable log entry enforcement')
@click.option('--github-enabled/--no-github-enabled', default=None, help='Enable/disable GitHub integration')
@click.option('--github-repo', help='GitHub repository (owner/repo format)')
@click.option('--github-token', help='GitHub personal access token')
@click.option('--monitor-enabled/--no-monitor-enabled', default=None, help='Enable/disable file monitoring')
@click.option('--monitor-interval', type=int, help='Monitor interval in seconds')
@click.option('--monitor-extensions', help='Comma-separated list of file extensions to monitor')
@click.option('--show', '-s', is_flag=True, help='Show current settings')
@click.pass_context
def settings(ctx, project_id, strict_doc_read, strict_file_ref, strict_log_entry,
             github_enabled, github_repo, github_token, monitor_enabled, 
             monitor_interval, monitor_extensions, show):
    """Manage project settings including strict mode enforcement."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    from tracline.db import get_database
    
    with get_database(config) as db:
        # Check if project exists
        cursor = db.execute_query(
            "SELECT id, name FROM projects WHERE id = ?",
            [project_id]
        )
        project_row = cursor.fetchone()
        if not project_row:
            console.print(f"[red]Project {project_id} not found[/red]")
            return
        
        # Convert to dict
        if hasattr(project_row, 'keys'):
            project = dict(project_row)
        else:
            # Handle tuple result
            project = {'id': project_row[0], 'name': project_row[1] if len(project_row) > 1 else 'Unknown'}
        
        # Get current settings
        try:
            cursor = db.execute_query(
                "SELECT * FROM project_settings WHERE project_id = ?",
                [project_id]
            )
            result = cursor.fetchone()
            if result:
                # Handle both dict-like and tuple results
                if hasattr(result, 'keys'):
                    # Result is already dict-like (Row object)
                    current_settings = dict(result)
                else:
                    # Result is a tuple, need to get column names
                    if cursor.description and len(cursor.description) > 0:
                        try:
                            columns = [desc[0] for desc in cursor.description]
                            current_settings = dict(zip(columns, result))
                        except (IndexError, TypeError):
                            # If we can't get column names, use default mapping
                            current_settings = {
                                'strict_doc_read': result[0] if len(result) > 0 else False,
                                'strict_file_ref': result[1] if len(result) > 1 else False,
                                'strict_log_entry': result[2] if len(result) > 2 else False,
                                'github_enabled': result[3] if len(result) > 3 else False,
                                'github_repo': result[4] if len(result) > 4 else None,
                                'github_token': result[5] if len(result) > 5 else None,
                                'monitor_enabled': result[6] if len(result) > 6 else False,
                                'monitor_interval': result[7] if len(result) > 7 else 300,
                                'monitor_extensions': result[8] if len(result) > 8 else None,
                            }
                    else:
                        # Fallback if no description available
                        current_settings = {
                            'strict_doc_read': result[0] if len(result) > 0 else False,
                            'strict_file_ref': result[1] if len(result) > 1 else False,
                            'strict_log_entry': result[2] if len(result) > 2 else False,
                            'github_enabled': result[3] if len(result) > 3 else False,
                            'github_repo': result[4] if len(result) > 4 else None,
                            'github_token': result[5] if len(result) > 5 else None,
                            'monitor_enabled': result[6] if len(result) > 6 else False,
                            'monitor_interval': result[7] if len(result) > 7 else 300,
                            'monitor_extensions': result[8] if len(result) > 8 else None,
                        }
            else:
                current_settings = None
        except Exception as e:
            # Table might not exist
            if 'no such table' in str(e) or 'does not exist' in str(e):
                # Create the table
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    db.execute_query('''
                        CREATE TABLE IF NOT EXISTS project_settings (
                            project_id TEXT PRIMARY KEY,
                            strict_doc_read BOOLEAN DEFAULT FALSE,
                            strict_file_ref BOOLEAN DEFAULT FALSE,
                            strict_log_entry BOOLEAN DEFAULT FALSE,
                            github_enabled BOOLEAN DEFAULT FALSE,
                            github_repo TEXT,
                            github_token TEXT,
                            monitor_enabled BOOLEAN DEFAULT FALSE,
                            monitor_interval INTEGER DEFAULT 300,
                            monitor_extensions TEXT[],
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                else:  # SQLite
                    db.execute_query('''
                        CREATE TABLE IF NOT EXISTS project_settings (
                            project_id TEXT PRIMARY KEY,
                            strict_doc_read BOOLEAN DEFAULT 0,
                            strict_file_ref BOOLEAN DEFAULT 0,
                            strict_log_entry BOOLEAN DEFAULT 0,
                            github_enabled BOOLEAN DEFAULT 0,
                            github_repo TEXT,
                            github_token TEXT,
                            monitor_enabled BOOLEAN DEFAULT 0,
                            monitor_interval INTEGER DEFAULT 300,
                            monitor_extensions TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                current_settings = None
            else:
                # Re-raise other errors
                console.print(f"[red]Error accessing project settings: {e}[/red]")
                return
        
        if show or all(opt is None for opt in [strict_doc_read, strict_file_ref, 
                                                strict_log_entry, github_enabled, 
                                                github_repo, github_token, 
                                                monitor_enabled, monitor_interval,
                                                monitor_extensions]):
            # Show current settings
            console.print(Panel(f"[bold cyan]Project Settings: {project['name']}[/bold cyan]"))
            
            table = Table(box=None)
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="white")
            table.add_column("Description", style="dim")
            
            if current_settings:
                # Strict mode settings
                table.add_row("Strict Document Read", 
                             "✓ Enabled" if current_settings.get('strict_doc_read') else "✗ Disabled",
                             "Require document confirmation on task next")
                table.add_row("Strict File Reference", 
                             "✓ Enabled" if current_settings.get('strict_file_ref') else "✗ Disabled",
                             "Require file associations on task done")
                table.add_row("Strict Log Entry", 
                             "✓ Enabled" if current_settings.get('strict_log_entry') else "✗ Disabled",
                             "Require log entries on task done")
                
                # GitHub settings
                table.add_row("", "", "")  # Separator
                table.add_row("GitHub Integration", 
                             "✓ Enabled" if current_settings.get('github_enabled') else "✗ Disabled",
                             "Sync with GitHub Issues")
                if current_settings.get('github_repo'):
                    table.add_row("GitHub Repository", current_settings['github_repo'], "")
                if current_settings.get('github_token'):
                    table.add_row("GitHub Token", "****" + current_settings['github_token'][-4:], "")
                
                # Monitor settings
                table.add_row("", "", "")  # Separator
                table.add_row("File Monitoring", 
                             "✓ Enabled" if current_settings.get('monitor_enabled') else "✗ Disabled",
                             "Auto-track file changes")
                if current_settings.get('monitor_interval'):
                    table.add_row("Monitor Interval", f"{current_settings['monitor_interval']}s", "")
                if current_settings.get('monitor_extensions'):
                    exts = current_settings['monitor_extensions']
                    if isinstance(exts, str):
                        exts = exts.split(',')
                    table.add_row("Monitor Extensions", ", ".join(exts), "")
            else:
                table.add_row("No settings", "Using defaults", "")
            
            console.print(table)
            return
        
        # Update settings
        updates = {}
        if strict_doc_read is not None:
            updates['strict_doc_read'] = strict_doc_read
        if strict_file_ref is not None:
            updates['strict_file_ref'] = strict_file_ref
        if strict_log_entry is not None:
            updates['strict_log_entry'] = strict_log_entry
        if github_enabled is not None:
            updates['github_enabled'] = github_enabled
        if github_repo is not None:
            updates['github_repo'] = github_repo
        if github_token is not None:
            updates['github_token'] = github_token
        if monitor_enabled is not None:
            updates['monitor_enabled'] = monitor_enabled
        if monitor_interval is not None:
            updates['monitor_interval'] = monitor_interval
        if monitor_extensions is not None:
            # Handle extensions based on database type
            if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                updates['monitor_extensions'] = '{' + monitor_extensions + '}'
            else:
                updates['monitor_extensions'] = monitor_extensions
        
        if not updates:
            console.print("[yellow]No settings to update[/yellow]")
            return
        
        try:
            # Start transaction
            db.begin_transaction()
            
            # Insert or update settings
            if current_settings:
                # Update existing settings
                db_type = config.config.database.type.lower()
                if db_type in ['postgresql', 'postgres']:
                    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
                    query = f"UPDATE project_settings SET {set_clause}, updated_at = NOW() WHERE project_id = ?"
                else:
                    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
                    query = f"UPDATE project_settings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE project_id = ?"
                params = list(updates.values()) + [project_id]
                db.execute_query(query, params)
            else:
                # Insert new settings
                updates['project_id'] = project_id
                
                # Handle timestamps based on database type
                db_type = config.config.database.type.lower()
                if db_type in ['postgresql', 'postgres']:
                    # PostgreSQL - use NOW() function
                    columns = list(updates.keys())
                    values = list(updates.values())
                    placeholders = ", ".join(["?" for _ in columns])
                    columns.extend(['created_at', 'updated_at'])
                    # Build query with NOW() function (not as parameter)
                    query = f"INSERT INTO project_settings ({', '.join(columns)}) VALUES ({placeholders}, NOW(), NOW())"
                    db.execute_query(query, values)
                else:  # SQLite
                    import datetime
                    now = datetime.datetime.now().isoformat()
                    updates['created_at'] = now
                    updates['updated_at'] = now
                    columns = list(updates.keys())
                    values = list(updates.values())
                    placeholders = ", ".join(["?" for _ in columns])
                    query = f"INSERT INTO project_settings ({', '.join(columns)}) VALUES ({placeholders})"
                    db.execute_query(query, values)
            
            db.commit_transaction()
            console.print(f"[green]✓ Project settings updated successfully[/green]")
            
            # Show what was updated
            for key, value in updates.items():
                if key.startswith('strict_'):
                    console.print(f"  {key.replace('_', ' ').title()}: {'Enabled' if value else 'Disabled'}")
                elif key.endswith('_enabled'):
                    console.print(f"  {key.replace('_', ' ').title()}: {'Enabled' if value else 'Disabled'}")
                else:
                    console.print(f"  {key.replace('_', ' ').title()}: {value}")
        except Exception as e:
            console.print(f"[red]Failed to update project settings: {str(e)}[/red]")
            import traceback
            traceback.print_exc()