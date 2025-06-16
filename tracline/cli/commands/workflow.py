"""Workflow commands (next, done) for TracLine."""

import click
import random
import string
import os
from rich import print
from rich.table import Table
from rich.panel import Panel
from tracline.core import Config, SessionManager, TaskService
from tracline.models import TaskStatus


def show_task_documents_warning(config, console, task):
    """Show associated documents and warning for a task."""
    if not task.project_id:
        return
    
    from tracline.db import get_database
    
    # Debug output
    import os
    if os.getenv('DEBUG_STRICT'):
        console.print(f"[dim]DEBUG: Checking strict mode for project {task.project_id}[/dim]")
    
    try:
        with get_database(config) as db:
            # Check environment variables first
            env_settings = config.get_project_strict_settings(task.project_id)
            strict_doc_read = env_settings.get('strict_doc_read')
            
            if os.getenv('DEBUG_STRICT'):
                console.print(f"[dim]DEBUG: Env settings: {env_settings}[/dim]")
            
            # If not set in env, check database
            if strict_doc_read is None:
                cursor = db.execute_query(
                    "SELECT strict_doc_read FROM project_settings WHERE project_id = ?",
                    [task.project_id]
                )
                result = cursor.fetchone()
                if result:
                    # Handle different row types
                    try:
                        if hasattr(result, 'get'):
                            strict_doc_read = result.get('strict_doc_read', False)
                        elif hasattr(result, '__getitem__'):
                            strict_doc_read = result['strict_doc_read']
                        else:
                            strict_doc_read = False
                    except (KeyError, TypeError):
                        strict_doc_read = False
                else:
                    strict_doc_read = False
            
            if os.getenv('DEBUG_STRICT'):
                console.print(f"[dim]DEBUG: strict_doc_read = {strict_doc_read}[/dim]")
            
            if not strict_doc_read:
                return
                
            # Check if task has associated documents
            docs = []
            
            # Try file_associations table
            if os.getenv('DEBUG_STRICT'):
                console.print(f"[dim]DEBUG: Querying file_associations for task_id = {task.id}[/dim]")
            
            cursor = db.execute_query(
                """SELECT file_path FROM file_associations 
                WHERE task_id = ? AND 
                (file_path LIKE '%.doc' OR file_path LIKE '%.md' OR 
                 file_path LIKE '%.txt' OR file_path LIKE '%.pdf' OR 
                 file_path LIKE '%.docx')""",
                [task.id]
            )
            result = cursor.fetchall()
            if os.getenv('DEBUG_STRICT'):
                console.print(f"[dim]DEBUG: Found {len(result)} files in file_associations[/dim]")
            docs.extend(result)
            
            # Check task_files table for documents (if it exists)
            try:
                cursor = db.execute_query(
                    """SELECT file_path FROM task_files 
                    WHERE task_id = ? AND 
                    (file_path LIKE ? OR file_path LIKE ? OR 
                     file_path LIKE ? OR file_path LIKE ? OR
                     file_path LIKE ?)""",
                    [task.id, '%.doc', '%.md', '%.txt', '%.pdf', '%.docx']
                )
                docs.extend(cursor.fetchall())
            except:
                # task_files table might not exist in all databases
                pass
            
            if os.getenv('DEBUG_STRICT'):
                console.print(f"[dim]DEBUG: Found {len(docs)} documents[/dim]")
            
            if docs:
                console.print("\n[bold yellow]⚠️  Document Read Warning[/bold yellow]")
                console.print("[yellow]This task has associated documents. Please read them before marking the task as done:[/yellow]\n")
                
                # Display document list
                doc_table = Table(box=None)
                doc_table.add_column("Document", style="cyan")
                for doc in docs:
                    doc_table.add_row(doc['file_path'])
                console.print(doc_table)
                
                console.print("\n[dim]Note: You will need to confirm document reading when marking this task as done.[/dim]")
    except Exception as e:
        # Silently ignore errors during warning display
        pass


def check_strict_requirements_for_done(config, console, task_id, confirm_read):
    """Check all strict mode requirements before marking task as done."""
    from tracline.db import get_database
    
    # Check if strict mode is globally disabled
    import os
    if os.getenv('TRACLINE_DISABLE_STRICT_MODE', '').lower() in ('true', '1', 'yes', 'on'):
        return True, None
    
    with get_database(config) as db:
        # Get task project (handle different column names for SQLite vs PostgreSQL)
        if hasattr(db, 'db_type') and db.db_type == 'sqlite':
            id_column = 'task_id'
        else:
            id_column = 'id'
            
        cursor = db.execute_query(
            f"SELECT project_id FROM tasks WHERE {id_column} = ?",
            [task_id]
        )
        task_result = cursor.fetchone()
        
        if not task_result:
            return True, None  # No task found
            
        # Handle different row types (dict vs sqlite3.Row)
        if hasattr(task_result, 'get'):
            project_id = task_result.get('project_id')
        else:
            # SQLite Row object
            project_id = task_result['project_id'] if 'project_id' in task_result.keys() else None
            
        if not project_id:
            return True, None  # No project, no strict mode
        
        # Check environment variables first
        env_settings = config.get_project_strict_settings(project_id)
        
        # Get project settings from database
        cursor = db.execute_query(
            "SELECT strict_doc_read, strict_file_ref, strict_log_entry FROM project_settings WHERE project_id = ?",
            [project_id]
        )
        db_result = cursor.fetchone()
        
        # Convert database result to dict for easier access
        if db_result:
            if hasattr(db_result, 'get'):
                db_settings = db_result
            else:
                # Convert SQLite Row to dict
                db_settings = {}
                for key in db_result.keys():
                    db_settings[key] = db_result[key]
        else:
            db_settings = {}
        
        # Merge settings (env vars take precedence)
        strict_doc_read = env_settings.get('strict_doc_read')
        if strict_doc_read is None:
            strict_doc_read = db_settings.get('strict_doc_read', False)
            
        strict_file_ref = env_settings.get('strict_file_ref')
        if strict_file_ref is None:
            strict_file_ref = db_settings.get('strict_file_ref', False)
            
        strict_log_entry = env_settings.get('strict_log_entry')
        if strict_log_entry is None:
            strict_log_entry = db_settings.get('strict_log_entry', False)
        
        # Debug logging
        if os.getenv('DEBUG_STRICT'):
            console.print(f"[dim]DEBUG: project_id={project_id}[/dim]")
            console.print(f"[dim]DEBUG: env_settings={env_settings}[/dim]")
            console.print(f"[dim]DEBUG: db_settings={db_settings}[/dim]")
            console.print(f"[dim]DEBUG: strict_doc_read={strict_doc_read}, strict_file_ref={strict_file_ref}, strict_log_entry={strict_log_entry}[/dim]")
        
        # Check document read requirement
        if strict_doc_read:
            # Check if task has associated documents
            docs = []
            
            # Try file_associations table
            try:
                cursor = db.execute_query(
                    """SELECT file_path FROM file_associations 
                    WHERE task_id = ? AND 
                    (file_path LIKE '%.doc' OR file_path LIKE '%.md' OR 
                     file_path LIKE '%.txt' OR file_path LIKE '%.pdf' OR 
                     file_path LIKE '%.docx')""",
                    [task_id]
                )
                docs.extend(cursor.fetchall())
            except:
                pass
            
            # Check task_files table for documents (if it exists)
            try:
                cursor = db.execute_query(
                    """SELECT file_path FROM task_files 
                    WHERE task_id = ? AND 
                    (file_path LIKE ? OR file_path LIKE ? OR 
                     file_path LIKE ? OR file_path LIKE ? OR
                     file_path LIKE ?)""",
                    [task_id, '%.doc', '%.md', '%.txt', '%.pdf', '%.docx']
                )
                docs.extend(cursor.fetchall())
            except:
                # task_files table might not exist
                pass
            
            if docs:
                # Generate deterministic code based on task_id
                # Use hash of task_id to ensure same code every time
                import hashlib
                hash_obj = hashlib.md5(task_id.encode())
                hash_hex = hash_obj.hexdigest()
                # Take first 3 chars and convert to uppercase
                deterministic_code = ''.join([c.upper() if c.isalpha() else c for c in hash_hex[:3]])
                
                if not confirm_read:
                    console.print("\n[bold red]❌ Document Read Confirmation Required[/bold red]")
                    console.print("[yellow]This task has associated documents that must be confirmed as read.[/yellow]")
                    console.print(f"\n[bold]Please run: [cyan]tracline done {task_id} --confirm-read {deterministic_code}[/cyan][/bold]")
                    console.print("\n[dim]Associated documents:[/dim]")
                    for doc in docs[:5]:  # Show first 5 docs
                        if isinstance(doc, dict):
                            console.print(f"  • {doc['file_path']}")
                        else:
                            console.print(f"  • {doc[0]}")  # Handle tuple result
                    if len(docs) > 5:
                        console.print(f"  ... and {len(docs)-5} more")
                    return False, deterministic_code
                elif confirm_read != deterministic_code:
                    console.print(f"\n[bold red]❌ Invalid confirmation code[/bold red]")
                    console.print(f"[yellow]Expected: {deterministic_code}, Got: {confirm_read}[/yellow]")
                    return False, deterministic_code
                else:
                    console.print("[green]✓ Document read confirmed[/green]")
        
        # Check file reference requirement
        if strict_file_ref:
            # First, get the task's work_started_file_count
            if hasattr(db, 'db_type') and db.db_type == 'sqlite':
                id_column = 'task_id'
            else:
                id_column = 'id'
                
            cursor = db.execute_query(
                f"SELECT work_started_file_count FROM tasks WHERE {id_column} = ?",
                [task_id]
            )
            work_result = cursor.fetchone()
            
            if work_result:
                if hasattr(work_result, 'get'):
                    work_started_count = work_result.get('work_started_file_count')
                else:
                    work_started_count = work_result[0] if work_result else None
            else:
                work_started_count = None
            
            # Check both file_associations and task_files tables for current count
            cursor = db.execute_query(
                "SELECT COUNT(*) as count FROM file_associations WHERE task_id = ?",
                [task_id]
            )
            count_result = cursor.fetchone()
            file_assoc_count = count_result['count'] if count_result else 0
            
            # Check task_files table if it exists
            task_files_count = 0
            try:
                cursor = db.execute_query(
                    "SELECT COUNT(*) as count FROM task_files WHERE task_id = ?",
                    [task_id]
                )
                count_result = cursor.fetchone()
                task_files_count = count_result['count'] if count_result else 0
            except:
                # task_files table might not exist in SQLite
                pass
            
            total_file_count = file_assoc_count + task_files_count
            
            # If work_started_file_count is set, check if new files were added
            if work_started_count is not None:
                if total_file_count <= work_started_count:
                    console.print("\n[bold red]❌ New File Reference Required[/bold red]")
                    console.print(f"[red]This task had {work_started_count} files when work started.[/red]")
                    console.print(f"[red]Current file count: {total_file_count}[/red]")
                    console.print("[yellow]You must add at least one new file during the work before marking as done.[/yellow]")
                    console.print("[yellow]Use 'tracline attach <file>' or 'tracline trace add-file <file> <task_id>' to associate files.[/yellow]")
                    return False, None
            else:
                # Fallback to original behavior if work_started_file_count is not set
                if total_file_count == 0:
                    console.print("\n[bold red]❌ File Reference Required[/bold red]")
                    console.print("[red]This task must have at least one associated file before it can be marked as done.[/red]")
                    console.print("[yellow]Use 'tracline attach <file>' or 'tracline trace add-file <file> <task_id>' to associate files.[/yellow]")
                    return False, None
        
        # Check log entry requirement
        if strict_log_entry:
            # First, find the most recent status change to TODO, READY, or from DONE
            # This handles cases where task was reset to an earlier state
            if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                time_column = 'created_at'
                placeholder = '%s'
                # Escape % for LIKE patterns in PostgreSQL
                cursor = db.execute_query(
                    f"""SELECT {time_column} FROM log_entries 
                    WHERE task_id = {placeholder} AND entry_type = 'status_changed' 
                    AND (message LIKE '%%→ TODO%%' OR message LIKE '%%→ READY%%' 
                         OR message LIKE '%%DONE →%%')
                    ORDER BY {time_column} DESC LIMIT 1""",
                    [task_id]
                )
            else:
                time_column = 'timestamp'
                cursor = db.execute_query(
                    f"""SELECT {time_column} FROM log_entries 
                    WHERE task_id = ? AND entry_type = 'status_changed' 
                    AND (message LIKE '%→ TODO%' OR message LIKE '%→ READY%' 
                         OR message LIKE '%DONE →%')
                    ORDER BY {time_column} DESC LIMIT 1""",
                    [task_id]
                )
            last_reset = cursor.fetchone()
            
            # If task was reset, only count logs after that time
            if last_reset:
                if hasattr(last_reset, 'get'):
                    reset_time = last_reset.get(time_column)
                else:
                    reset_time = last_reset[0] if last_reset else None
                
                if reset_time:
                    if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                        cursor = db.execute_query(
                            f"""SELECT COUNT(*) as count FROM log_entries 
                            WHERE task_id = %s AND entry_type IN ('work', 'user_action') 
                            AND {time_column} > %s""",
                            [task_id, reset_time]
                        )
                    else:
                        cursor = db.execute_query(
                            f"""SELECT COUNT(*) as count FROM log_entries 
                            WHERE task_id = ? AND entry_type IN ('work', 'user_action') 
                            AND {time_column} > ?""",
                            [task_id, reset_time]
                        )
                else:
                    # Fallback to checking all logs
                    if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                        cursor = db.execute_query(
                            "SELECT COUNT(*) as count FROM log_entries WHERE task_id = %s AND entry_type IN ('work', 'user_action')",
                            [task_id]
                        )
                    else:
                        cursor = db.execute_query(
                            "SELECT COUNT(*) as count FROM log_entries WHERE task_id = ? AND entry_type IN ('work', 'user_action')",
                            [task_id]
                        )
            else:
                # No reset found, check all logs
                if hasattr(db, 'db_type') and db.db_type == 'postgresql':
                    cursor = db.execute_query(
                        "SELECT COUNT(*) as count FROM log_entries WHERE task_id = %s AND entry_type IN ('work', 'user_action')",
                        [task_id]
                    )
                else:
                    cursor = db.execute_query(
                        "SELECT COUNT(*) as count FROM log_entries WHERE task_id = ? AND entry_type IN ('work', 'user_action')",
                        [task_id]
                    )
            
            count_result = cursor.fetchone()
            
            # Debug logging
            if os.getenv('DEBUG_STRICT'):
                console.print(f"[dim]DEBUG: strict_log_entry={strict_log_entry}, count_result={count_result}[/dim]")
                if last_reset:
                    console.print(f"[dim]DEBUG: Task was reset, checking logs after {reset_time}[/dim]")
            
            # Handle different database result formats
            if count_result:
                if hasattr(count_result, 'get'):
                    log_count = count_result.get('count', 0)
                elif hasattr(count_result, '__getitem__'):
                    # SQLite returns tuple
                    log_count = count_result[0] if count_result else 0
                else:
                    log_count = 0
            else:
                log_count = 0
            
            if log_count == 0:
                console.print("\n[bold red]❌ Log Entry Required[/bold red]")
                console.print("[red]This task must have at least one log entry before it can be marked as done.[/red]")
                if last_reset:
                    console.print("[yellow]Note: Task was previously completed and reset. You need a new log entry.[/yellow]")
                console.print("[yellow]Use 'tracline log <task_id> <message>' to add a log entry.[/yellow]")
                return False, None
        
        return True, None


@click.command(name="next")
@click.option('--assignee', default=None, help='Assignee to filter by')
@click.option('--project', help='Project to filter by')
@click.option('--all', is_flag=True, help='Show tasks for all assignees')
@click.pass_context
def next_task(ctx, assignee, project, all):
    """Get next task from the queue (Iterator pattern)."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    session = SessionManager()
    
    # Determine assignee
    if not all and not assignee:
        assignee = config.get_default_assignee()
        
    # Determine project
    if not project:
        project = config.get_current_project()
        if project:
            console.print(f"[dim]Using current project: {project}[/dim]")
    
    # Get task service
    with TaskService(config) as service:
        # Get next incomplete task
        try:
            task = service.get_next_task(assignee=assignee, project_id=project)
            
            if task:
                # Display task info
                table = Table(title=f"Next Task", box=None)
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="white")
                
                table.add_row("ID", task.id)
                table.add_row("Title", task.title)
                table.add_row("Description", task.description or "")
                table.add_row("Status", task.status)
                table.add_row("Assignee", task.assignee or "Unassigned")
                table.add_row("Project", task.project_id or "None")
                table.add_row("Priority", str(task.priority))
                
                if task.tags:
                    if isinstance(task.tags, list):
                        table.add_row("Tags", ", ".join(task.tags))
                    else:
                        table.add_row("Tags", str(task.tags))
                
                if task.due_date:
                    table.add_row("Due Date", task.due_date.strftime("%Y-%m-%d"))
                
                console.print(table)
                
                # Show document warning if strict mode is enabled
                show_task_documents_warning(config, console, task)
                
                # Store as current task for the session
                session.set_current_task(task.id)
            else:
                console.print("[yellow]No incomplete tasks found.[/yellow]")
        except Exception as e:
            import traceback
            console.print(f"[red]Error retrieving next task: {str(e)}[/red]")
            traceback.print_exc()
            console.print("[yellow]Creating sample task instead...[/yellow]")
            
            # Create a sample task as fallback
            try:
                task = service.create_task(
                    id="FALLBACK-001",
                    title="Fallback Task",
                    description="This task was created as a fallback when next failed",
                    assignee=assignee or "Unknown"
                )
                
                # Display task info
                table = Table(title=f"Fallback Task", box=None)
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="white")
                
                table.add_row("ID", task.id)
                table.add_row("Title", task.title)
                table.add_row("Description", task.description or "")
                table.add_row("Status", task.status)
                table.add_row("Assignee", task.assignee or "Unassigned")
                
                console.print(table)
                
                # Show document warning if strict mode is enabled
                show_task_documents_warning(config, console, task)
                
                # Store as current task for the session
                session.set_current_task(task.id)
            except Exception as inner_e:
                console.print(f"[red]Failed to create fallback task: {str(inner_e)}[/red]")


@click.command(name="done")
@click.argument('task_id', required=False)
@click.option('--confirm-read', default=None, help='Confirmation code for document read')
@click.pass_context
def done(ctx, task_id, confirm_read):
    """Mark task as done (advance to next state)."""
    config = ctx.obj['config']
    console = ctx.obj['console']
    session = SessionManager()
    
    # Get task service
    with TaskService(config) as service:
        # If no task_id provided, use current task or get next task
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
            # Get current task state to check if advancing to DONE
            task = service.get_task(task_id)
            if task:
                # Get next state
                next_state = config.get_next_state(task.status)
                
                # Check strict mode requirements only when advancing to DONE
                if next_state == TaskStatus.DONE.value:
                    passed, expected_code = check_strict_requirements_for_done(config, console, task_id, confirm_read)
                    if not passed:
                        return
            
            # Advance task to next state
            result = service.advance_task(task_id)
            
            if result["success"]:
                old_state = result["old_state"]
                new_state = result["new_state"]
                
                # Success message
                console.print(
                    f"[green]Task {task_id} advanced: {old_state} → {new_state}[/green]"
                )
                
                # Special message for completion
                if new_state == TaskStatus.DONE:
                    console.print(f"[bold green]✓ Task {task_id} completed![/bold green]")
                
                # Clear current task from session if it was completed
                if new_state in [TaskStatus.DONE, TaskStatus.CANCELED]:
                    session.clear_current_task()
            else:
                console.print(f"[red]Error: {result['error']}[/red]")
        except Exception as e:
            console.print(f"[red]Error advancing task: {str(e)}[/red]")
            # Debug: print full traceback
            import traceback
            if os.getenv('TRACLINE_DEBUG'):
                traceback.print_exc()


class TaskServiceContext:
    """Context manager for task service."""
    def __init__(self, config: Config):
        self.config = config
        self.service = None
    
    def __enter__(self):
        self.service = TaskService(self.config)
        return self.service
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.service:
            self.service.close_connection()


# TaskService already has __enter__ and __exit__ methods defined