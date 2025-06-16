"""Database health check command."""
import click
from tabulate import tabulate
from tracline.core.config import Config
from tracline.db.factory import DatabaseFactory
import logging

logger = logging.getLogger(__name__)

@click.command('dbcheck')
@click.pass_context
def dbcheck_command(ctx):
    """Check database health and fix common issues."""
    config = ctx.obj['config']
    
    click.echo("Checking database health...")
    
    try:
        # Create database instance
        db = DatabaseFactory.create(config.config.database)
        db.connect()
        
        click.echo(f"✓ Connected to {config.config.database.type} database")
        
        # Check if it's PostgreSQL
        if hasattr(db, 'db_type') and db.db_type == 'postgresql':
            check_postgresql_health(db)
        else:
            check_sqlite_health(db)
            
        db.disconnect()
        click.echo("\n✓ Database health check complete")
        
    except Exception as e:
        click.echo(f"✗ Database health check failed: {e}", err=True)
        raise click.ClickException(str(e))

def check_postgresql_health(db):
    """Check PostgreSQL specific health items."""
    click.echo("\nChecking PostgreSQL schema...")
    
    issues = []
    fixed = []
    
    # Check file_associations columns
    cursor = db.cursor
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'file_associations'
        ORDER BY ordinal_position
    """)
    
    columns = [row['column_name'] for row in cursor.fetchall()]
    required_columns = ['file_type', 'description', 'relative_path', 'created_by', 
                       'last_modified', 'file_size', 'reference_count']
    
    missing_columns = [col for col in required_columns if col not in columns]
    
    if missing_columns:
        click.echo(f"\n⚠ Missing columns in file_associations: {', '.join(missing_columns)}")
        if click.confirm("Would you like to fix these issues?"):
            # Trigger the auto-fix
            if hasattr(db, '_ensure_file_associations_columns'):
                db._ensure_file_associations_columns()
                fixed.append("Added missing columns to file_associations")
            else:
                issues.append("Auto-fix not available - please update TracLine")
    else:
        click.echo("✓ All required columns exist in file_associations")
    
    # Check for other common issues
    check_table_sizes(db)
    check_indices(db)
    
    # Summary
    if issues:
        click.echo("\n⚠ Issues found:")
        for issue in issues:
            click.echo(f"  - {issue}")
    
    if fixed:
        click.echo("\n✓ Fixed:")
        for fix in fixed:
            click.echo(f"  - {fix}")

def check_sqlite_health(db):
    """Check SQLite specific health items."""
    click.echo("\nChecking SQLite database...")
    
    # Check database file size
    import os
    if hasattr(db, 'db_path'):
        if os.path.exists(db.db_path):
            size = os.path.getsize(db.db_path)
            size_mb = size / (1024 * 1024)
            click.echo(f"✓ Database size: {size_mb:.1f} MB")
            
            if size_mb > 100:
                click.echo("⚠ Database is large - consider PostgreSQL for better performance")
    
    # Check table sizes
    check_table_sizes(db)

def check_table_sizes(db):
    """Check table row counts."""
    click.echo("\nTable sizes:")
    
    tables = ['tasks', 'file_associations', 'log_entries', 'members', 'projects']
    table_data = []
    
    for table in tables:
        try:
            if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                db.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            else:
                db.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            
            count = db.cursor.fetchone()
            if isinstance(count, dict):
                count = count.get('count', 0)
            else:
                count = count[0] if count else 0
                
            table_data.append([table, count])
        except Exception as e:
            table_data.append([table, f"Error: {e}"])
    
    click.echo(tabulate(table_data, headers=['Table', 'Row Count'], tablefmt='simple'))

def check_indices(db):
    """Check if important indices exist."""
    if hasattr(db, 'db_type') and db.db_type == 'postgresql':
        click.echo("\nChecking indices...")
        
        cursor = db.cursor
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        
        indices = [row['indexname'] for row in cursor.fetchall()]
        
        important_indices = [
            'idx_tasks_status',
            'idx_tasks_assignee',
            'idx_tasks_project_id'
        ]
        
        missing_indices = [idx for idx in important_indices if idx not in indices]
        
        if missing_indices:
            click.echo(f"⚠ Missing indices: {', '.join(missing_indices)}")
            click.echo("  Consider adding indices for better performance")
        else:
            click.echo("✓ All important indices exist")