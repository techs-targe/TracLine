"""Log management commands for TracLine."""

import click
from rich.table import Table
from tracline.core import Config, TaskService
from tracline.models import LogLevel, LogEntryType

@click.command()
@click.argument('task_id')
@click.argument('message')
@click.option('--level', '-l', 
              type=click.Choice(['INFO', 'WARNING', 'ERROR', 'DEBUG']),
              default='INFO',
              help='Log level')
@click.pass_context
def log(ctx, task_id, message, level):
    """Add a log entry for a task."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Verify task exists
        task = service.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        try:
            # Add log entry
            user = config.get_default_assignee() or "unknown"
            log_entry = service.add_log(task_id, message, user=user)
            
            console.print(f"[green]✓ Log entry added to {task_id}[/green]")
            console.print(f"  Time: {log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            console.print(f"  Message: {message}")
            
        except Exception as e:
            console.print(f"[red]Error adding log entry: {e}[/red]")

@click.command()
@click.option('--task', '-t', help='Filter logs by task ID')
@click.option('--limit', '-n', type=int, default=50, help='Number of entries to show')
@click.option('--type', help='Filter by entry type')
@click.option('--level', help='Filter by log level')
@click.pass_context
def show_logs(ctx, task, limit, type, level):
    """Show system logs."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Get log entries
        logs = service.db.get_log_entries(task_id=task, limit=limit)
        
        # Filter by type if specified
        if type:
            logs = [l for l in logs if l.entry_type == type]
        
        # Filter by level if specified
        if level:
            logs = [l for l in logs if l.level == level]
        
        if not logs:
            console.print("[yellow]No log entries found[/yellow]")
            return
        
        # Create table
        title = "System Logs"
        if task:
            title = f"Logs for {task}"
        
        table = Table(title=title, box=None)
        table.add_column("Time", style="dim")
        table.add_column("Level", style="yellow")
        table.add_column("Type", style="cyan")
        table.add_column("Task", style="green")
        table.add_column("Message")
        table.add_column("User", style="magenta")
        
        for log_entry in logs:
            # Color code level
            level_style = "yellow"
            if log_entry.level == LogLevel.ERROR:
                level_style = "red"
            elif log_entry.level == LogLevel.WARNING:
                level_style = "orange1"
            elif log_entry.level == LogLevel.DEBUG:
                level_style = "dim"
            
            table.add_row(
                log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                f"[{level_style}]{log_entry.level}[/{level_style}]",
                log_entry.entry_type,
                log_entry.task_id or "-",
                log_entry.message[:50] + "..." if len(log_entry.message) > 50 else log_entry.message,
                log_entry.user or "-"
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(logs)} entries[/dim]")
