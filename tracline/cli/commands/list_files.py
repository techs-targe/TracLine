"""List files command for TracLine (v1 compatible)."""

import click
from rich.table import Table
from tracline.core import Config, TaskService

@click.command(name='ls-files')
@click.argument('task_id', required=False)
@click.option('--details', '-d', is_flag=True, help='Show detailed file information')
@click.pass_context
def ls_files(ctx, task_id, details):
    """List files associated with a task (v1 compatible). If no task_id is provided, list all files."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        if task_id:
            # Verify task exists
            task = service.get_task(task_id)
            if not task:
                console.print(f"[red]Task {task_id} not found[/red]")
                return
            
            # Get file associations for specific task
            associations = service.db.get_file_associations(task_id)
            
            if not associations:
                console.print(f"[yellow]No files associated with {task_id}[/yellow]")
                return
            
            # Create table for specific task
            table = Table(title=f"Files for {task_id}: {task.title}", box=None)
        else:
            # Get all file associations
            associations = service.db.get_all_file_associations()
            
            if not associations:
                console.print("[yellow]No files found in the system[/yellow]")
                return
            
            # Create table for all files
            table = Table(title="All Files", box=None)
        table.add_column("ID", style="dim")
        if not task_id:  # Add task column if showing all files
            table.add_column("Task", style="magenta")
        table.add_column("File Path", style="cyan")
        table.add_column("Type", style="yellow")
        
        if details:
            table.add_column("Size", style="green")
            table.add_column("Modified", style="dim")
            table.add_column("Added", style="dim")
        
        for idx, assoc in enumerate(associations, 1):
            row = [str(idx)]
            
            if not task_id:  # Add task ID if showing all files
                row.append(assoc.task_id)
            
            row.extend([
                assoc.file_path,
                assoc.file_type or "unknown"
            ])
            
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
