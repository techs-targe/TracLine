"""Database migration command for TracLine."""

import click
import sqlite3
from pathlib import Path
from tracline.core import Config
from tracline.db import DatabaseFactory
from tracline.models import Task, TaskStatus


@click.command()
@click.option('--from-v1', type=click.Path(exists=True), 
              help='Path to TracLine v1 SQLite database')
@click.option('--dry-run', is_flag=True, 
              help='Show what would be migrated without making changes')
@click.pass_context
def migrate(ctx, from_v1, dry_run):
    """Migrate database from TracLine v1 or between database types."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    
    if from_v1:
        # Migrate from v1 SQLite database
        console.print(f"[bold]Migrating from TracLine v1:[/bold] {from_v1}\n")
        
        try:
            # Connect to v1 database
            v1_conn = sqlite3.connect(from_v1)
            v1_conn.row_factory = sqlite3.Row
            v1_cursor = v1_conn.cursor()
            
            # Count tasks
            v1_cursor.execute("SELECT COUNT(*) FROM tasks")
            task_count = v1_cursor.fetchone()[0]
            console.print(f"Found {task_count} tasks to migrate")
            
            if dry_run:
                console.print("\n[yellow]DRY RUN - No changes will be made[/yellow]\n")
            
            # Get all tasks from v1
            v1_cursor.execute("SELECT * FROM tasks ORDER BY order_num")
            v1_tasks = v1_cursor.fetchall()
            
            if not dry_run:
                # Initialize v2 database
                db = DatabaseFactory.create(config.get_database_config())
                db.connect()
                db.initialize_schema()
                
                # Create TaskService for v2
                from tracline.core import TaskService
                service = TaskService(config, db)
            
            # Migrate tasks
            migrated = 0
            for v1_task in v1_tasks:
                task_data = dict(v1_task)
                
                # Map v1 fields to v2
                v2_task = Task(
                    id=task_data['task_id'],
                    title=task_data['title'],
                    description=task_data.get('description'),
                    status=task_data['status'],
                    assignee=task_data.get('assignee'),
                    created_at=task_data.get('created_at', '2024-01-01T00:00:00'),
                    updated_at=task_data.get('updated_at', '2024-01-01T00:00:00'),
                    order_num=task_data.get('order_num', 0)
                )
                
                if dry_run:
                    console.print(f"Would migrate: {v2_task.id} - {v2_task.title}")
                else:
                    service.db.create_task(v2_task)
                    console.print(f"Migrated: {v2_task.id} - {v2_task.title}")
                
                migrated += 1
            
            # Migrate relationships if they exist
            try:
                v1_cursor.execute("SELECT * FROM task_relationships")
                relationships = v1_cursor.fetchall()
                
                if relationships:
                    console.print(f"\nFound {len(relationships)} relationships to migrate")
                    
                    for rel in relationships:
                        if dry_run:
                            console.print(f"Would migrate relationship: {rel['parent_id']} -> {rel['child_id']}")
                        else:
                            service.link_tasks(
                                rel['parent_id'],
                                rel['child_id'],
                                rel.get('relationship_type', 'parent-child')
                            )
                            console.print(f"Migrated relationship: {rel['parent_id']} -> {rel['child_id']}")
            except sqlite3.OperationalError:
                # Table doesn't exist in v1
                pass
            
            # Close connections
            v1_conn.close()
            if not dry_run:
                db.disconnect()
            
            console.print(f"\n[green]✓ Migration complete! Migrated {migrated} tasks[/green]")
            
        except Exception as e:
            console.print(f"[red]Migration failed: {e}[/red]")
            import traceback
            traceback.print_exc()
    
    else:
        # Future: Implement migrations between different database types
        console.print("[bold]Database Migration Options:[/bold]\n")
        console.print("Currently supported:")
        console.print("  --from-v1    Migrate from TracLine v1 SQLite database\n")
        console.print("Example:")
        console.print("  tracline migrate --from-v1 /path/to/old/taskman.db")
        console.print("  tracline migrate --from-v1 /path/to/old/taskman.db --dry-run")