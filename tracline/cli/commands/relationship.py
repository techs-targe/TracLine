"""Relationship management commands for TracLine."""

import click
from rich.table import Table
from tracline.core import Config, TaskService
from tracline.models import RelationshipType

@click.command()
@click.argument('parent_id')
@click.argument('child_id')
@click.option(
    '--type', '-t',
    type=click.Choice([
        'parent-child',
        'blocks',
        'related',
        'duplicate',
        'requirement-design',
        'design-implementation',
        'implementation-test'
    ]),
    default='parent-child',
    help='Type of relationship'
)
@click.pass_context
def link(ctx, parent_id, child_id, type):
    """Create a relationship between two tasks."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    with TaskService(config) as service:
        # Verify both tasks exist
        parent = service.get_task(parent_id)
        if not parent:
            console.print(f"[red]Parent task {parent_id} not found[/red]")
            return
            
        child = service.get_task(child_id)
        if not child:
            console.print(f"[red]Child task {child_id} not found[/red]")
            return
        
        try:
            # Convert type string to enum
            rel_type = RelationshipType(type)
            
            relationship = service.link_tasks(parent_id, child_id, rel_type)
            console.print(
                f"[green]✓ Relationship created: "
                f"{parent_id} → {child_id} ({type})[/green]"
            )
            
            # Show task titles for context
            console.print(f"  Parent: {parent.title}")
            console.print(f"  Child: {child.title}")
            
        except ValueError:
            console.print(f"[red]Invalid relationship type: {type}[/red]")
        except Exception as e:
            console.print(f"[red]Error creating relationship: {e}[/red]")

@click.command()
@click.argument('task_id', required=False)
@click.option('--type', '-t', help='Filter by relationship type')
@click.pass_context
def list_relationships(ctx, task_id, type):
    """List task relationships."""
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
