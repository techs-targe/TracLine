"""Project management commands for TracLine."""

import click
import os
from tracline.core.config import Config
from tracline.core.team_service import TeamService


@click.command(name="current")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def show_current_project(ctx, as_json):
    """Show the current project."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    current_project_id = config.get_current_project()
    
    if not current_project_id:
        console.print("[yellow]No current project set[/yellow]")
        console.print("Use 'tracline project change <project_id>' to set the current project.")
        return
    
    with TeamService(config) as service:
        project = service.get_project(current_project_id)
        
        if not project:
            console.print(f"[red]Current project '{current_project_id}' not found in database[/red]")
            console.print("The project may have been deleted. Please set a new current project.")
            return
        
        if as_json:
            import json
            console.print(json.dumps(project.to_dict(), indent=2))
            return
        
        console.print(f"[bold green]Current project:[/bold green] {project.name} ([cyan]{project.id}[/cyan])")
        console.print(f"Description: {project.description or 'N/A'}")
        console.print(f"Status: {project.status}")
        
        # Show task stats for current project
        from tracline.core.task_service import TaskService
        
        with TaskService(config) as task_service:
            tasks = task_service.list_tasks(project_id=current_project_id)
            
            if tasks:
                # Count by status
                status_counts = {}
                for task in tasks:
                    status_counts[task.status] = status_counts.get(task.status, 0) + 1
                
                console.print(f"\n[bold]Tasks:[/bold] {len(tasks)} total")
                for status, count in status_counts.items():
                    console.print(f"  • {status}: {count}")


@click.command(name="change")
@click.argument("project_id")
@click.pass_context
def change_project(ctx, project_id):
    """Change the current project."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TeamService(config) as service:
        project = service.get_project(project_id)
        if not project:
            console.print(f"[red]Project '{project_id}' not found[/red]")
            return
        
        # Update config
        config.set_current_project(project_id)
        
        # Update environment variable for current session
        os.environ["TRACLINE_PROJECT"] = project_id
        
        console.print(f"[green]✓ Current project changed to:[/green] {project.name} ([cyan]{project.id}[/cyan])")
        console.print("To make this persist across sessions, add to your environment:")
        console.print(f"  export TRACLINE_PROJECT={project_id}")


def register_commands(cli, project_group):
    """Register additional project commands with the CLI."""
    project_group.add_command(show_current_project)
    project_group.add_command(change_project)