"""Clean minimal CLI for TracLine."""

import click
from rich.console import Console
from tracline.core import Config, TaskService
from tracline.db import get_database
from tracline.models import Task, FileAssociation, LogEntry
from datetime import datetime
from tracline import __version__

@click.group()
@click.version_option(version=__version__, prog_name="TracLine")
@click.pass_context
def cli(ctx):
    """TracLine - Task Management System"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config()
    ctx.obj['console'] = Console()

# Register init command from commands/init.py
from tracline.cli.commands.init import init
cli.add_command(init)

# Database check command
@cli.command()
@click.pass_context
def dbcheck(ctx):
    """Check database health and fix common issues."""
    from tracline.cli.commands.dbcheck import dbcheck_command
    ctx.invoke(dbcheck_command)

# Project group
@cli.group()
def project():
    """Project management commands."""
    pass

# Member group
@cli.group()
def member():
    """Team member management commands."""
    pass

@project.command('create')
@click.argument('project_id')
@click.argument('name')
@click.pass_context
def project_create(ctx, project_id, name):
    """Create a new project."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    try:
        with get_database(config) as db:
            # Insert project
            db.execute_query(
                "INSERT INTO projects (id, name, status, created_at) VALUES (?, ?, ?, ?)",
                [project_id, name, 'ACTIVE', datetime.now().isoformat()]
            )
            
            # Commit
            if hasattr(db, 'conn') and hasattr(db.conn, 'commit'):
                db.conn.commit()
            
            console.print(f"[green]✓ Project {project_id} created successfully[/green]")
            
            # Display info
            from rich.table import Table
            table = Table(box=None)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            table.add_row("ID", project_id)
            table.add_row("Name", name)
            table.add_row("Description", "N/A")
            table.add_row("Owner", "None")
            table.add_row("Status", "ACTIVE")
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error creating project: {e}[/red]")

@project.command('settings_old')
@click.argument('project_id')
@click.option('--strict-doc-read', is_flag=True)
@click.option('--strict-file-ref', is_flag=True) 
@click.option('--strict-log-entry', is_flag=True)
@click.pass_context
def project_settings_old(ctx, project_id, strict_doc_read, strict_file_ref, strict_log_entry):
    """View or update project settings."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    try:
        with get_database(config) as db:
            if strict_doc_read or strict_file_ref or strict_log_entry:
                # Update settings
                db.execute_query("DELETE FROM project_settings WHERE project_id = ?", [project_id])
                
                # Determine database type and use appropriate boolean values
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    # PostgreSQL uses true/false
                    values = [project_id, 
                             strict_doc_read,
                             strict_file_ref,
                             strict_log_entry,
                             datetime.now().isoformat()]
                else:
                    # SQLite uses 1/0
                    values = [project_id, 
                             1 if strict_doc_read else 0,
                             1 if strict_file_ref else 0,
                             1 if strict_log_entry else 0,
                             datetime.now().isoformat(),
                             datetime.now().isoformat()]
                
                db.execute_query(
                    """INSERT INTO project_settings 
                    (project_id, strict_doc_read, strict_file_ref, strict_log_entry, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    values
                )
                
                if hasattr(db, 'conn') and hasattr(db.conn, 'commit'):
                    db.conn.commit()
                
                console.print("[green]✓ Project settings updated successfully[/green]")
                if strict_doc_read:
                    console.print("  Strict Doc Read: Enabled")
                if strict_file_ref:
                    console.print("  Strict File Ref: Enabled")
                if strict_log_entry:
                    console.print("  Strict Log Entry: Enabled")
                console.print(f"  Project Id: {project_id}")
                
            else:
                # View settings
                cursor = db.execute_query(
                    "SELECT * FROM project_settings WHERE project_id = ?", 
                    [project_id]
                )
                settings = cursor.fetchone()
                
                console.print(f"\n[bold]Project Settings: {project_id}[/bold]\n")
                
                if settings:
                    # Handle both dict-like and tuple results
                    if hasattr(settings, 'keys'):
                        # Result is dict-like (Row object)
                        console.print(f"Strict Document Read: {'✓ Enabled' if settings['strict_doc_read'] else '✗ Disabled'}")
                        console.print(f"Strict File Reference: {'✓ Enabled' if settings['strict_file_ref'] else '✗ Disabled'}")
                        console.print(f"Strict Log Entry: {'✓ Enabled' if settings['strict_log_entry'] else '✗ Disabled'}")
                    else:
                        # Result is a tuple, need to get column names
                        if cursor.description and len(cursor.description) > 0:
                            try:
                                columns = [desc[0] for desc in cursor.description]
                                settings_dict = dict(zip(columns, settings))
                                console.print(f"Strict Document Read: {'✓ Enabled' if settings_dict.get('strict_doc_read', False) else '✗ Disabled'}")
                                console.print(f"Strict File Reference: {'✓ Enabled' if settings_dict.get('strict_file_ref', False) else '✗ Disabled'}")
                                console.print(f"Strict Log Entry: {'✓ Enabled' if settings_dict.get('strict_log_entry', False) else '✗ Disabled'}")
                            except (IndexError, TypeError):
                                # If we can't get column names, use positional access
                                console.print(f"Strict Document Read: {'✓ Enabled' if (len(settings) > 1 and settings[1]) else '✗ Disabled'}")
                                console.print(f"Strict File Reference: {'✓ Enabled' if (len(settings) > 2 and settings[2]) else '✗ Disabled'}")
                                console.print(f"Strict Log Entry: {'✓ Enabled' if (len(settings) > 3 and settings[3]) else '✗ Disabled'}")
                        else:
                            # Fallback to positional access (project_id is index 0)
                            console.print(f"Strict Document Read: {'✓ Enabled' if (len(settings) > 1 and settings[1]) else '✗ Disabled'}")
                            console.print(f"Strict File Reference: {'✓ Enabled' if (len(settings) > 2 and settings[2]) else '✗ Disabled'}")
                            console.print(f"Strict Log Entry: {'✓ Enabled' if (len(settings) > 3 and settings[3]) else '✗ Disabled'}")
                else:
                    console.print("No custom settings (all disabled)")
                    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

# Register more project commands
from tracline.cli.commands import (
    project_update, project_delete, project_show, project_list,
    project_add_members, project_remove_members, project_members,
    project_current, project_change, project_settings
)

project.add_command(project_update, name='update')
project.add_command(project_delete, name='delete')
project.add_command(project_show, name='show')
project.add_command(project_list, name='list')
project.add_command(project_add_members, name='add-members')
project.add_command(project_remove_members, name='remove-members')
project.add_command(project_members, name='members')
project.add_command(project_current, name='current')
project.add_command(project_change, name='change')
project.add_command(project_settings, name='settings')

# Trace group
@cli.group()
def trace():
    """File traceability commands."""
    pass

@trace.command('add-file')
@click.argument('task_id')
@click.argument('file_path')
@click.pass_context
def trace_add_file(ctx, task_id, file_path):
    """Add file to task."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    try:
        with get_database(config) as db:
            # Add file association
            file_assoc = FileAssociation(
                task_id=task_id,
                file_path=file_path
            )
            db.add_file_association(file_assoc)
            
            if hasattr(db, 'conn') and hasattr(db.conn, 'commit'):
                db.conn.commit()
            
            console.print(f"Added file '{file_path}' to task '{task_id}'")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

# Register trace commands from trace.py
from tracline.cli.commands.trace import list_trace, remove_file, stats
trace.add_command(list_trace, name='ls-trace')
trace.add_command(remove_file, name='remove-file')
trace.add_command(stats, name='stats')

# Task commands
@cli.command()
@click.argument('task_id')
@click.argument('title')
@click.option('--project', '-j')
@click.option('--assignee', '-a')
@click.option('--description', '-d', help='Task description')
@click.option('--priority', '-p', type=int, default=3, help='Priority (1-5)')
@click.pass_context
def add(ctx, task_id, title, project, assignee, description, priority):
    """Add a new task."""
    from tracline.cli.commands.task import add as add_cmd
    ctx.invoke(add_cmd, task_id=task_id, title=title, project=project, assignee=assignee, description=description, priority=priority)

@cli.command()
@click.option('--project', '-j', help='Filter by project ID')
@click.option('--assignee', '-a', help='Filter by assignee')
@click.option('--status', '-s', help='Filter by status')
@click.option('--priority', '-p', type=int, help='Filter by priority')
@click.option('--show-done', is_flag=True, help='Include completed tasks')
@click.option('--all', is_flag=True, help='Show all tasks (ignore default assignee)')
@click.pass_context
def list(ctx, project, assignee, status, priority, show_done, all):
    """List tasks."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    try:
        with TaskService(config) as service:
            # Build exclude_status based on show_done flag
            exclude_status = None if show_done else 'DONE'
            
            # If --all flag is set, explicitly pass empty assignee to avoid default
            if all:
                assignee = ""  # Empty string to override default assignee
            
            tasks = service.list_tasks(
                project_id=project,
                assignee=assignee,
                status=status,
                priority=priority,
                exclude_status=exclude_status
            )
            
            if not tasks:
                console.print("[yellow]No tasks found[/yellow]")
                return
            
            from rich.table import Table
            table = Table(title=f"Tasks ({len(tasks)} found)", box=None)
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Status", style="yellow")
            table.add_column("Assignee", style="green")
            table.add_column("Priority", style="magenta")
            
            for task in tasks:
                table.add_row(
                    task.id,
                    task.title[:40] + "..." if len(task.title) > 40 else task.title,
                    task.status,
                    task.assignee or "-",
                    str(task.priority)
                )
            
            console.print(table)
            
            # Summary
            status_counts = {}
            for task in tasks:
                status_counts[task.status] = status_counts.get(task.status, 0) + 1
            
            summary = ", ".join(f"{status}: {count}" for status, count in status_counts.items())
            console.print(f"\n[dim]Summary: {summary}[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.argument('task_id')
@click.argument('message')
@click.option('--level', type=click.Choice(['INFO', 'WARNING', 'ERROR', 'DEBUG']), default='INFO', help='Log level')
@click.pass_context
def log(ctx, task_id, message, level):
    """Add log entry to task."""
    from tracline.cli.commands.logs import log as log_cmd
    ctx.invoke(log_cmd, task_id=task_id, message=message, level=level)

@cli.command()
@click.option('--project', '-j')
@click.pass_context
def next(ctx, project):
    """Get next task."""
    from tracline.cli.commands.workflow import next_task
    ctx.invoke(next_task, project=project)

@cli.command()
@click.argument('task_id', required=False)
@click.option('--confirm-read', default=None)
@click.pass_context
def done(ctx, task_id, confirm_read):
    """Mark task as done."""
    from tracline.cli.commands.workflow import done as done_cmd
    ctx.invoke(done_cmd, task_id=task_id, confirm_read=confirm_read)

@cli.command()
@click.argument('task_id', required=False)
@click.option('--confirm-read', default=None, help='Confirmation code for document read')
@click.pass_context
def complete(ctx, task_id, confirm_read):
    """Mark task as DONE directly."""
    from tracline.cli.commands.complete import complete as complete_cmd
    ctx.invoke(complete_cmd, task_id=task_id, confirm_read=confirm_read)

@cli.command()
@click.argument('task_id')
@click.option('--status', type=click.Choice(['TODO', 'READY', 'DOING', 'TESTING', 'DONE', 'PENDING', 'CANCELED']))
@click.option('--title')
@click.option('--assignee')
@click.option('--priority', type=int)
@click.option('--project', help='New project ID')
@click.pass_context
def update(ctx, task_id, status, title, assignee, priority, project):
    """Update task details."""
    from tracline.cli.commands.task import update as update_cmd
    ctx.invoke(update_cmd, task_id=task_id, status=status, title=title, assignee=assignee, priority=priority, project=project)

@cli.command()
@click.argument('task_id')
@click.option('--force', is_flag=True)
@click.pass_context
def delete(ctx, task_id, force):
    """Delete a task."""
    from tracline.cli.commands.task import delete as delete_cmd
    ctx.invoke(delete_cmd, task_id=task_id, confirm=force)

@cli.command()
@click.argument('task_id')
@click.option('--logs', is_flag=True)
@click.option('--files', is_flag=True)
@click.option('--relationships', is_flag=True)
@click.option('--doc', is_flag=True)
@click.option('--json', 'as_json', is_flag=True)
@click.pass_context
def show(ctx, task_id, logs, files, relationships, doc, as_json):
    """Show task details."""
    from tracline.cli.commands.task import show as show_cmd
    ctx.invoke(show_cmd, task_id=task_id, logs=logs, files=files, relationships=relationships)

@cli.command()
@click.argument('task_id')
@click.argument('assignee')
@click.pass_context
def assign(ctx, task_id, assignee):
    """Assign task to someone."""
    from tracline.cli.commands.assign import assign as assign_cmd
    ctx.invoke(assign_cmd, task_id=task_id, assignee=assignee)

@cli.command()
@click.argument('parent_id')
@click.argument('child_id')
@click.option('--type', 'rel_type', default='parent-child')
@click.pass_context
def link(ctx, parent_id, child_id, rel_type):
    """Create task relationship."""
    from tracline.cli.commands.relationship import link as link_cmd
    ctx.invoke(link_cmd, parent_id=parent_id, child_id=child_id, type=rel_type)

@cli.command()
@click.argument('task_id')
@click.argument('file_path')
@click.option('--description')
@click.pass_context
def attach(ctx, task_id, file_path, description):
    """Attach file to task."""
    from tracline.cli.commands.files import attach as attach_cmd
    ctx.invoke(attach_cmd, task_id=task_id, file_path=file_path)

@cli.command('ls-tasks')
@click.option('--project', '-j')
@click.pass_context
def ls_tasks(ctx, project):
    """List tasks (v1 alias)."""
    ctx.invoke(list, project=project)

@cli.command('ls-relations')
@click.argument('task_id', required=False)
@click.option('--type', 'rel_type')
@click.option('--json', 'as_json', is_flag=True)
@click.pass_context
def ls_relations(ctx, task_id, rel_type, as_json):
    """List task relationships."""
    from tracline.cli.commands.list_relations import list_relations as list_relations_cmd
    ctx.invoke(list_relations_cmd, task_id=task_id, type=rel_type)

@cli.command('ls-files')
@click.argument('task_id')
@click.option('--details', is_flag=True)
@click.option('--json', 'as_json', is_flag=True)
@click.pass_context
def ls_files(ctx, task_id, details, as_json):
    """List files attached to task."""
    from tracline.cli.commands.list_files import ls_files as ls_files_cmd
    ctx.invoke(ls_files_cmd, task_id=task_id, details=details)

@cli.command('project-current')
@click.pass_context
def project_current_alias(ctx):
    """Show current project (shorthand)."""
    from tracline.cli.commands.project_v2 import show_current_project
    ctx.invoke(show_current_project)

@cli.command()
@click.pass_context
def config(ctx):
    """Configuration management."""
    from tracline.cli.commands.config import config_cmd
    ctx.invoke(config_cmd)

@cli.command()
@click.option('--from-v1', 'from_v1')
@click.option('--to-postgresql', is_flag=True)
@click.pass_context
def migrate(ctx, from_v1, to_postgresql):
    """Database migration."""
    from tracline.cli.commands.migrate import migrate as migrate_cmd
    ctx.invoke(migrate_cmd, from_v1=from_v1, to_postgresql=to_postgresql)

# Monitoring commands
@cli.group()
def monitor():
    """Monitoring daemon commands."""
    pass

from tracline.cli.commands.monitor import start, stop, status as monitor_status, logs, history
monitor.add_command(start, name='start')
monitor.add_command(stop, name='stop')
monitor.add_command(monitor_status, name='status')
monitor.add_command(logs, name='logs')
monitor.add_command(history, name='history')

# GitHub commands
@cli.group()
def github():
    """GitHub integration commands."""
    pass

from tracline.cli.commands.github import setup, sync, status, test
github.add_command(setup, name='setup')
github.add_command(sync, name='sync')
github.add_command(status, name='status')
github.add_command(test, name='test')

# Project root commands
from tracline.cli.commands.projectroot import projectroot
cli.add_command(projectroot)

# Register member commands
from tracline.cli.commands import (
    member_add, member_update, member_delete, member_show,
    member_list, member_change_position, member_change_leader,
    member_team_structure
)

member.add_command(member_add, name='add')
member.add_command(member_update, name='update')
member.add_command(member_delete, name='delete')
member.add_command(member_show, name='show')
member.add_command(member_list, name='list')
member.add_command(member_change_position, name='change-position')
member.add_command(member_change_leader, name='change-leader')
member.add_command(member_team_structure, name='team-structure')

def main():
    """Main entry point."""
    cli()

if __name__ == '__main__':
    main()