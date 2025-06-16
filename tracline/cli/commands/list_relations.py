"""List relationships command for TracLine."""

import click
from rich.table import Table
from tracline.core import Config, TaskService

@click.command(name='ls-relations')
@click.argument('task_id', required=False)
@click.option('--type', '-t', help='Filter by relationship type')
@click.pass_context
def list_relations(ctx, task_id, type):
    """List task relationships (v1 compatible)."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Get relationships
        relationships = service.db.get_relationships(
            task_id=task_id,
            relationship_type=type
        )
        
        if not relationships:
            console.print("[yellow]No relationships found[/yellow]")
            return
        
        # Group by task if a specific task was requested
        if task_id:
            title = f"Relationships for {task_id}"
        else:
            title = f"All Relationships ({len(relationships)} found)"
        
        table = Table(title=title)
        table.add_column("Parent", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Child", style="green")
        table.add_column("Created", style="dim")
        
        for rel in relationships:
            table.add_row(
                rel.parent_id,
                rel.relationship_type,
                rel.child_id,
                rel.created_at.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)
