"""Complete command for marking tasks as done directly."""

import click
from rich import print
from tracline.core import Config, SessionManager
from tracline.models import TaskStatus
from .workflow import check_strict_requirements_for_done


@click.command(name="complete")
@click.argument('task_id', required=False)
@click.option('--confirm-read', default=None, help='Confirmation code for document read')
@click.pass_context
def complete(ctx, task_id, confirm_read):
    """Mark task as complete (directly to DONE status)."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    session = SessionManager()
    
    # Get task service
    from tracline.core.task_service import TaskService
    
    with TaskService(config) as service:
        # If no task_id provided, use current task
        if not task_id:
            task_id = session.get_current_task()
            
            if not task_id:
                # Get next task for current assignee and project
                assignee = config.get_default_assignee()
                project = config.get_current_project()
                try:
                    task = service.get_next_task(assignee=assignee, project_id=project)
                    
                    if task:
                        task_id = task.id
                    else:
                        console.print("[red]No current task. Use 'next' to get a task.[/red]")
                        return
                except Exception as e:
                    console.print(f"[red]Error getting next task: {str(e)}[/red]")
                    return
        
        try:
            # Get current task state
            task = service.get_task(task_id)
            if not task:
                console.print(f"[red]Task {task_id} not found[/red]")
                return
            
            # Check if already done
            if task.status == TaskStatus.DONE.value:
                console.print(f"[yellow]Task {task_id} is already completed[/yellow]")
                return
            
            # Check strict mode requirements
            passed, expected_code = check_strict_requirements_for_done(config, console, task_id, confirm_read)
            if not passed:
                return
            
            # Update task status directly to DONE
            old_status = task.status
            updated_task = service.update_task(task_id, status=TaskStatus.DONE.value)
            
            if updated_task:
                # Log the status change
                from tracline.models import LogEntry, LogEntryType
                log_entry = LogEntry.create_task_log(
                    task_id=task_id,
                    entry_type=LogEntryType.STATUS_CHANGED,
                    message=f"Status changed: {old_status} → DONE (completed directly)",
                    user=task.assignee,
                    metadata={"old_state": old_status, "new_state": TaskStatus.DONE.value}
                )
                service.db.add_log_entry(log_entry)
                
                # Success message
                console.print(
                    f"[green]Task {task_id} completed: {old_status} → DONE[/green]"
                )
                console.print(f"[bold green]✓ Task {task_id} completed![/bold green]")
                
                # Clear current task from session
                session.clear_current_task()
            else:
                console.print(f"[red]Failed to complete task {task_id}[/red]")
                
        except Exception as e:
            console.print(f"[red]Error completing task: {str(e)}[/red]")
            import traceback
            import os
            if os.getenv('TRACLINE_DEBUG'):
                traceback.print_exc()