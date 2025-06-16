"""File association commands for TracLine."""

import click
from pathlib import Path
from rich.table import Table
from tracline.core import Config, TaskService

@click.command()
@click.argument('task_id')
@click.argument('file_path', type=click.Path(exists=True))
@click.pass_context
def attach(ctx, task_id, file_path):
    """Attach a file to a task."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    # Convert to absolute path
    file_path = Path(file_path).resolve()
    
    with TaskService(config) as service:
        # Verify task exists
        task = service.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        try:
            association = service.attach_file(task_id, str(file_path))
            console.print(
                f"[green]✓ File attached to {task_id}:[/green] {file_path}"
            )
            
            # Show file info
            console.print(f"  Type: {association.file_type or 'unknown'}")
            if association.file_size:
                console.print(f"  Size: {association.file_size:,} bytes")
                
        except Exception as e:
            console.print(f"[red]Error attaching file: {e}[/red]")

@click.command()
@click.argument('task_id')
@click.option('--details', '-d', is_flag=True, help='Show detailed file information')
@click.pass_context
def list_files(ctx, task_id, details):
    """List files associated with a task."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Verify task exists
        task = service.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        # Get file associations
        associations = service.db.get_file_associations(task_id)
        
        if not associations:
            console.print(f"[yellow]No files associated with {task_id}[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Files for {task_id}: {task.title}", box=None)
        table.add_column("File Path", style="cyan")
        table.add_column("Type", style="yellow")
        
        if details:
            table.add_column("Size", style="green")
            table.add_column("Modified", style="dim")
            table.add_column("Added", style="dim")
        
        for assoc in associations:
            row = [
                assoc.file_path,
                assoc.file_type or "unknown"
            ]
            
            if details:
                size_str = f"{assoc.file_size:,} bytes" if assoc.file_size else "unknown"
                modified_str = (
                    assoc.last_modified.strftime("%Y-%m-%d %H:%M")
                    if assoc.last_modified else "unknown"
                )
                added_str = assoc.created_at.strftime("%Y-%m-%d %H:%M")
                
                row.extend([size_str, modified_str, added_str])
            
            table.add_row(*row)
        
        console.print(table)
        console.print(f"\n[dim]Total files: {len(associations)}[/dim]")

@click.command()
@click.argument('task_id')
@click.option('--recursive', '-r', is_flag=True, help='Include files from related tasks')
@click.pass_context
def list_related_files(ctx, task_id, recursive):
    """List files from a task and its related tasks."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Verify task exists
        task = service.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        # Get tasks to check
        tasks_to_check = {task_id: task}
        
        if recursive:
            # Get related tasks
            relationships = service.db.get_relationships(task_id)
            
            for rel in relationships:
                # Add child tasks
                if rel.parent_id == task_id:
                    child_task = service.get_task(rel.child_id)
                    if child_task:
                        tasks_to_check[rel.child_id] = child_task
                # Add parent tasks
                else:
                    parent_task = service.get_task(rel.parent_id)
                    if parent_task:
                        tasks_to_check[rel.parent_id] = parent_task
        
        # Get files for all tasks
        all_files = []
        for check_task_id, check_task in tasks_to_check.items():
            files = service.db.get_file_associations(check_task_id)
            for f in files:
                all_files.append((check_task_id, check_task, f))
        
        if not all_files:
            console.print("[yellow]No files found[/yellow]")
            return
        
        # Create table
        title = f"Files for {task_id}"
        if recursive:
            title += " and related tasks"
        
        table = Table(title=title, box=None)
        table.add_column("Task", style="cyan")
        table.add_column("Task Title", style="white")
        table.add_column("File Path", style="green")
        table.add_column("Type", style="yellow")
        
        for task_id, task, file_assoc in all_files:
            table.add_row(
                task_id,
                task.title[:30] + "..." if len(task.title) > 30 else task.title,
                file_assoc.file_path,
                file_assoc.file_type or "unknown"
            )
        
        console.print(table)
        console.print(f"\n[dim]Total files: {len(all_files)}[/dim]")
        console.print(f"[dim]Tasks checked: {len(tasks_to_check)}[/dim]")
