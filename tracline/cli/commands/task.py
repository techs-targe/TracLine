"""Task management commands for TracLine."""

import click
from datetime import datetime
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint
from tracline.core import Config, TaskService
from tracline.models import TaskPriority, TaskStatus

@click.command()
@click.argument('task_id')
@click.argument('title')
@click.option('--description', '-d', help='Task description')
@click.option('--assignee', '-a', help='Task assignee')
@click.option('--project', '-j', help='Project ID to associate with this task')
@click.option('--priority', '-p', type=int, default=TaskPriority.MEDIUM, help='Priority (1-5)')
@click.option('--tags', '-t', multiple=True, help='Task tags')
@click.option('--due-date', type=click.DateTime(formats=['%Y-%m-%d']), help='Due date')
@click.pass_context
def add(ctx, task_id, title, description, assignee, project, priority, tags, due_date):
    """Add a new task."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    # Use default assignee if not provided
    if not assignee:
        assignee = config.get_default_assignee()
    
    # Use current project if not provided
    if not project:
        project = config.get_current_project()
        if project:
            console.print(f"[dim]Using current project: {project}[/dim]")
    
    with TaskService(config) as service:
        try:
            task = service.create_task(
                task_id=task_id,
                title=title,
                description=description,
                assignee=assignee,
                project_id=project,
                priority=priority,
                tags=list(tags) if tags else []
            )
            
            # Set due date if provided
            if due_date:
                service.update_task(task.id, due_date=due_date)
            
            console.print(f"[green]✓ Task {task_id} created successfully[/green]")
            
            # Show task summary
            table = Table(box=None)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("ID", task.id)
            table.add_row("Title", task.title)
            table.add_row("Status", task.status)
            table.add_row("Assignee", task.assignee or "Unassigned")
            table.add_row("Project", task.project_id or "None")
            table.add_row("Priority", str(task.priority))
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]Error creating task: {e}[/red]")

@click.command()
@click.argument('task_id')
@click.option('--title', help='New title')
@click.option('--description', help='New description')
@click.option('--assignee', help='New assignee')
@click.option('--priority', type=int, help='New priority (1-5)')
@click.option('--status', help='New status')
@click.option('--project', help='New project ID')
@click.option('--tags', multiple=True, help='New tags (replaces existing)')
@click.option('--due-date', type=click.DateTime(formats=['%Y-%m-%d']), help='New due date')
@click.pass_context
def update(ctx, task_id, title, description, assignee, priority, status, project, tags, due_date):
    """Update an existing task."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Get existing task
        task = service.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        # Build update dictionary
        updates = {}
        if title is not None:
            updates['title'] = title
        if description is not None:
            updates['description'] = description
        if assignee is not None:
            updates['assignee'] = assignee
        if priority is not None:
            updates['priority'] = priority
        if status is not None:
            # Validate status
            if status not in config.get_all_states():
                console.print(f"[red]Invalid status: {status}[/red]")
                console.print(f"Valid states: {', '.join(config.get_all_states())}")
                return
            updates['status'] = status
        if project is not None:
            updates['project_id'] = project
        if tags:
            updates['tags'] = list(tags)
        if due_date is not None:
            updates['due_date'] = due_date
        
        if not updates:
            console.print("[yellow]No updates specified[/yellow]")
            return
        
        try:
            updated_task = service.update_task(task_id, **updates)
            console.print(f"[green]✓ Task {task_id} updated successfully[/green]")
            
            # Show updated fields
            for field, value in updates.items():
                console.print(f"  {field}: {value}")
                
        except Exception as e:
            console.print(f"[red]Error updating task: {e}[/red]")

@click.command()
@click.argument('task_id')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def delete(ctx, task_id, confirm):
    """Delete a task."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Get task to show details
        task = service.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        # Show task details
        console.print(f"Task to delete: {task.id} - {task.title}")
        
        # Confirm deletion
        if not confirm:
            if not click.confirm("Are you sure you want to delete this task?"):
                console.print("[yellow]Deletion cancelled[/yellow]")
                return
        
        try:
            if service.delete_task(task_id):
                console.print(f"[green]✓ Task {task_id} deleted successfully[/green]")
            else:
                console.print(f"[red]Failed to delete task {task_id}[/red]")
        except Exception as e:
            console.print(f"[red]Error deleting task: {e}[/red]")

@click.command()
@click.argument('task_id')
@click.option('--logs', is_flag=True, help='Show task logs')
@click.option('--files', is_flag=True, help='Show associated files')
@click.option('--relationships', is_flag=True, help='Show task relationships')
@click.pass_context
def show(ctx, task_id, logs, files, relationships):
    """Show detailed information about a task."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Get task
        task = service.get_task(task_id)
        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            return
        
        # Main task information
        table = Table(title=f"Task Details: {task.id}", box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("ID", task.id)
        table.add_row("Title", task.title)
        table.add_row("Description", task.description or "")
        table.add_row("Status", task.status)
        table.add_row("Assignee", task.assignee or "Unassigned")
        table.add_row("Project", task.project_id or "None")
        table.add_row("Priority", str(task.priority))
        table.add_row("Tags", ", ".join(task.tags) if task.tags else "")
        table.add_row("Created", task.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row("Updated", task.updated_at.strftime("%Y-%m-%d %H:%M:%S"))
        
        if task.due_date:
            table.add_row("Due Date", task.due_date.strftime("%Y-%m-%d"))
        
        if task.completed_at:
            table.add_row("Completed", task.completed_at.strftime("%Y-%m-%d %H:%M:%S"))
        
        console.print(table)
        
        # Show logs if requested
        if logs:
            console.print("\n[bold]Task Logs:[/bold]")
            task_logs = service.get_task_logs(task_id, limit=10)
            
            if task_logs:
                log_table = Table(box=None)
                log_table.add_column("Time", style="dim")
                log_table.add_column("Type", style="yellow")
                log_table.add_column("Message")
                
                for log in task_logs:
                    log_table.add_row(
                        log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        log.entry_type,
                        log.message
                    )
                
                console.print(log_table)
            else:
                console.print("  No logs found")
        
        # Show files if requested
        if files:
            console.print("\n[bold]Associated Files:[/bold]")
            file_associations = service.db.get_file_associations(task_id)
            
            if file_associations:
                file_table = Table(box=None)
                file_table.add_column("File", style="cyan")
                file_table.add_column("Type", style="yellow")
                file_table.add_column("Size", style="green")
                
                for assoc in file_associations:
                    file_table.add_row(
                        assoc.file_path,
                        assoc.file_type or "unknown",
                        f"{assoc.file_size or 0} bytes"
                    )
                
                console.print(file_table)
            else:
                console.print("  No files associated")
        
        # Show relationships if requested
        if relationships:
            console.print("\n[bold]Task Relationships:[/bold]")
            rels = service.db.get_relationships(task_id)
            
            if rels:
                rel_table = Table(box=None)
                rel_table.add_column("Type", style="yellow")
                rel_table.add_column("Direction", style="cyan")
                rel_table.add_column("Related Task", style="white")
                
                for rel in rels:
                    if rel.parent_id == task_id:
                        rel_table.add_row(
                            rel.relationship_type,
                            "→",
                            rel.child_id
                        )
                    else:
                        rel_table.add_row(
                            rel.relationship_type,
                            "←",
                            rel.parent_id
                        )
                
                console.print(rel_table)
            else:
                console.print("  No relationships found")

@click.command(name='list')
@click.option('--assignee', '-a', help='Filter by assignee')
@click.option('--status', '-s', help='Filter by status')
@click.option('--priority', '-p', type=int, help='Filter by priority')
@click.option('--tag', '-t', help='Filter by tag')
@click.option('--sort', default='order_num', 
              type=click.Choice(['order_num', 'created_at', 'updated_at', 'priority', 'due_date']),
              help='Sort by field')
@click.option('--reverse', is_flag=True, help='Reverse sort order')
@click.option('--limit', '-n', type=int, default=10, help='Limit number of results (default: 10)')
@click.option('--all', is_flag=True, help='Show all tasks (ignore default assignee filter)')
@click.option('--show-done', is_flag=True, help='Include completed tasks')
@click.pass_context
def list_tasks(ctx, assignee, status, priority, tag, sort, reverse, limit, all, show_done):
    """List tasks with filtering options."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    # Default to current assignee unless --all is specified
    if not all and not assignee:
        assignee = config.get_default_assignee()
    
    with TaskService(config) as service:
        # Build filters
        filters = {}
        if assignee:
            filters['assignee'] = assignee
        if status:
            filters['status'] = status
        if priority:
            filters['priority'] = priority
        
        # Exclude 'done' tasks by default unless explicitly requested
        if not show_done and not status:
            filters['exclude_status'] = config.fixed_states.get('completed', 'DONE')
        
        # Handle tag filtering separately due to list nature
        tasks = service.list_tasks(
            assignee=assignee if not all else None,
            status=status,
            priority=priority,
            exclude_status=filters.get('exclude_status'),
            sort_by=sort,
            limit=limit
        )
        
        # Filter by tag if specified
        if tag:
            tasks = [t for t in tasks if tag in t.tags]
        
        # Reverse if requested
        if reverse:
            tasks.reverse()
        
        if not tasks:
            console.print("[yellow]No tasks found matching criteria[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Tasks ({len(tasks)} found)", box=None)
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Assignee", style="green")
        table.add_column("Priority", style="magenta")
        table.add_column("Due Date", style="red")
        table.add_column("Tags", style="blue")
        
        for task in tasks:
            # Color code status
            status_style = "yellow"
            if task.status == TaskStatus.DONE:
                status_style = "green"
            elif task.status in [TaskStatus.PENDING, TaskStatus.CANCELED]:
                status_style = "dim"
            
            table.add_row(
                task.id,
                task.title[:50] + "..." if len(task.title) > 50 else task.title,
                f"[{status_style}]{task.status}[/{status_style}]",
                task.assignee or "Unassigned",
                str(task.priority),
                task.due_date.strftime("%Y-%m-%d") if task.due_date else "",
                ", ".join(task.tags[:3]) if task.tags else ""
            )
        
        console.print(table)
        
        # Summary
        status_counts = {}
        for task in tasks:
            status_counts[task.status] = status_counts.get(task.status, 0) + 1
        
        summary = []
        for status, count in status_counts.items():
            summary.append(f"{status}: {count}")
        
        console.print(f"\n[dim]Summary: {' | '.join(summary)}[/dim]")
