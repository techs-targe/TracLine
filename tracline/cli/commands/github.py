"""GitHub integration commands for TracLine."""

import click
import os
from datetime import datetime
from ...core.config import Config
from ...db.factory import DatabaseFactory
from ...github.sync import GitHubSync
from tabulate import tabulate


@click.group()
def github():
    """Manage GitHub integration."""
    pass


@github.command()
@click.argument('project_id')
@click.option('--repo', '-r', required=True, help='GitHub repository (owner/repo)')
@click.option('--token', '-t', envvar='GITHUB_TOKEN', help='GitHub personal access token')
@click.option('--enable/--disable', default=True, help='Enable or disable GitHub integration')
def setup(project_id, repo, token, enable):
    """Setup GitHub integration for a project.
    
    Example:
        tracline github setup PROJECT1 -r owner/repo -t ghp_xxxx
        export GITHUB_TOKEN=ghp_xxxx && tracline github setup PROJECT1 -r owner/repo
    """
    if enable and not token:
        click.echo("Error: GitHub token is required. Use -t option or set GITHUB_TOKEN environment variable", err=True)
        return
        
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        # Update project settings
        if config.config.database.type == "postgresql":
            query = """
            INSERT INTO project_settings (project_id, github_enabled, github_repo, github_token)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (project_id) DO UPDATE
            SET github_enabled = EXCLUDED.github_enabled,
                github_repo = EXCLUDED.github_repo,
                github_token = EXCLUDED.github_token,
                updated_at = NOW()
            """
            params = [project_id, enable, repo if enable else None, token if enable else None]
        else:
            query = """
            INSERT OR REPLACE INTO project_settings 
            (project_id, github_enabled, github_repo, github_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            params = [project_id, enable, repo if enable else None, token if enable else None, datetime.now().isoformat(), datetime.now().isoformat()]
            
        db.execute_query(query, params)
        db.conn.commit()
        
        if enable:
            click.echo(f"✅ GitHub integration enabled for project {project_id}")
            click.echo(f"Repository: {repo}")
            
            # Test connection
            sync = GitHubSync(project_id, token, repo)
            if sync.connect():
                click.echo("✅ Successfully connected to GitHub repository")
            else:
                click.echo("⚠️  Warning: Failed to connect to repository. Check token and repo name.", err=True)
        else:
            click.echo(f"GitHub integration disabled for project {project_id}")
            
    finally:
        db.disconnect()


@github.command()
@click.argument('project_id')
@click.option('--all', 'sync_all', is_flag=True, help='Sync all issues')
@click.option('--issue', '-i', type=int, help='Sync specific issue number')
@click.option('--task', '-t', help='Sync specific task to GitHub')
def sync(project_id, sync_all, issue, task):
    """Sync tasks with GitHub issues.
    
    Example:
        tracline github sync PROJECT1 --all
        tracline github sync PROJECT1 --issue 123
        tracline github sync PROJECT1 --task TASK-001
    """
    try:
        sync_client = GitHubSync(project_id)
        
        if not sync_client.connect():
            click.echo("Failed to connect to GitHub repository", err=True)
            return
            
        if sync_all:
            click.echo(f"Syncing all issues for project {project_id}...")
            synced_tasks = sync_client.sync_all_issues()
            click.echo(f"✅ Synced {len(synced_tasks)} issues")
            
        elif issue:
            click.echo(f"Syncing issue #{issue}...")
            repo = sync_client.repo
            gh_issue = repo.get_issue(issue)
            task_id = sync_client.sync_issue_to_task(gh_issue)
            if task_id:
                click.echo(f"✅ Synced issue #{issue} to task {task_id}")
            else:
                click.echo(f"Failed to sync issue #{issue}", err=True)
                
        elif task:
            click.echo(f"Syncing task {task} to GitHub...")
            issue_number = sync_client.sync_task_to_issue(task)
            if issue_number:
                click.echo(f"✅ Synced task {task} to issue #{issue_number}")
            else:
                click.echo(f"Failed to sync task {task}", err=True)
                
        else:
            click.echo("Please specify --all, --issue, or --task", err=True)
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@github.command()
def status():
    """Show GitHub integration status for all projects."""
    config = Config()
    db = DatabaseFactory.create(config.config.database)
    
    try:
        db.connect()
        
        if config.config.database.type == "postgresql":
            query = """
            SELECT p.id, p.name, ps.github_enabled, ps.github_repo
            FROM projects p
            LEFT JOIN project_settings ps ON p.id = ps.project_id
            ORDER BY p.name
            """
        else:
            query = """
            SELECT p.id, p.name, ps.github_enabled, ps.github_repo
            FROM projects p
            LEFT JOIN project_settings ps ON p.id = ps.project_id
            ORDER BY p.name
            """
            
        cursor = db.execute_query(query)
        rows = cursor.fetchall()
        
        if not rows:
            click.echo("No projects found")
            return
            
        status_data = []
        for row in rows:
            if isinstance(row, dict):
                status_data.append({
                    'Project ID': row['id'],
                    'Project Name': row['name'],
                    'GitHub Enabled': '✅' if row.get('github_enabled') else '❌',
                    'Repository': row.get('github_repo') or '-'
                })
            else:
                status_data.append({
                    'Project ID': row[0],
                    'Project Name': row[1],
                    'GitHub Enabled': '✅' if row[2] else '❌',
                    'Repository': row[3] or '-'
                })
                
        click.echo("\nGitHub Integration Status:")
        click.echo(tabulate(status_data, headers='keys', tablefmt='grid'))
        
    finally:
        db.disconnect()


@github.command()
@click.argument('project_id')
def test(project_id):
    """Test GitHub connection for a project."""
    try:
        sync_client = GitHubSync(project_id)
        
        click.echo(f"Testing GitHub connection for project {project_id}...")
        
        if sync_client.connect():
            repo = sync_client.repo
            click.echo(f"✅ Successfully connected to repository: {repo.full_name}")
            click.echo(f"   Description: {repo.description}")
            click.echo(f"   Stars: {repo.stargazers_count}")
            click.echo(f"   Open Issues: {repo.open_issues_count}")
            
            # Get recent issues
            issues = list(repo.get_issues(state='open')[:5])
            if issues:
                click.echo("\nRecent open issues:")
                for issue in issues:
                    click.echo(f"   #{issue.number}: {issue.title}")
        else:
            click.echo("❌ Failed to connect to GitHub repository", err=True)
            raise click.ClickException("Failed to connect to GitHub repository")
            
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise click.ClickException(str(e))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))