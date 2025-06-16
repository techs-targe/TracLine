"""Assign command for TracLine."""

import click
from tracline.core import Config, TaskService

@click.command()
@click.argument('task_id')
@click.argument('assignee')
@click.pass_context
def assign(ctx, task_id, assignee):
    """Assign a task to someone."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Get existing task
        task = service.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        old_assignee = task.assignee
        
        try:
            updated_task = service.assign_task(task_id, assignee)
            console.print(
                f"[green]✓ Task {task_id} assigned: "
                f"{old_assignee or 'Unassigned'} → {assignee}[/green]"
            )
        except Exception as e:
            console.print(f"[red]Error assigning task: {e}[/red]")
