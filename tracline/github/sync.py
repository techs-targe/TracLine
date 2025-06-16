"""GitHub Issues synchronization for TracLine."""

import logging
from datetime import datetime
from github import Github, GithubException
from ..core.config import Config
from ..db.factory import DatabaseFactory
from ..models.task import Task, TaskStatus
from ..models.member import Member

logger = logging.getLogger(__name__)


class GitHubSync:
    """Synchronize TracLine tasks with GitHub Issues."""
    
    def __init__(self, project_id, github_token=None, repo_name=None):
        self.project_id = project_id
        self.config = Config()
        self.db = DatabaseFactory.create(self.config.config.database)
        
        # Load project settings
        self.settings = self._load_project_settings()
        
        # GitHub configuration
        self.github_token = github_token or self.settings.get('github_token')
        self.repo_name = repo_name or self.settings.get('github_repo')
        
        if not self.github_token:
            raise ValueError("GitHub token is required for synchronization")
        
        if not self.repo_name:
            raise ValueError("GitHub repository name is required")
            
        # Initialize GitHub client
        self.github = Github(self.github_token)
        self.repo = None
        
    def _load_project_settings(self):
        """Load project-specific GitHub settings."""
        try:
            self.db.connect()
            
            if self.config.config.database.type == "postgresql":
                query = """
                SELECT github_enabled, github_repo, github_token, webhook_url
                FROM project_settings
                WHERE project_id = %s
                """
                params = [self.project_id]
            else:
                query = """
                SELECT github_enabled, github_repo, github_token, webhook_url
                FROM project_settings
                WHERE project_id = ?
                """
                params = [self.project_id]
                
            cursor = self.db.execute_query(query, params)
            result = cursor.fetchone()
            
            if result:
                if isinstance(result, dict):
                    return result
                else:
                    return {
                        'github_enabled': result[0],
                        'github_repo': result[1],
                        'github_token': result[2],
                        'webhook_url': result[3]
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to load GitHub settings: {e}")
            return {}
        finally:
            self.db.disconnect()
            
    def connect(self):
        """Connect to GitHub repository."""
        try:
            self.repo = self.github.get_repo(self.repo_name)
            logger.info(f"Connected to GitHub repository: {self.repo_name}")
            return True
        except GithubException as e:
            logger.error(f"Failed to connect to GitHub repository: {e}")
            return False
            
    def sync_issue_to_task(self, issue):
        """Sync a GitHub issue to TracLine task."""
        try:
            self.db.connect()
            
            # Generate task ID from issue number
            task_id = f"GH-{self.project_id}-{issue.number}"
            
            # Map GitHub issue state to TracLine status
            if issue.state == 'open':
                if any(label.name.lower() in ['in progress', 'doing'] for label in issue.labels):
                    status = TaskStatus.DOING
                elif any(label.name.lower() in ['ready', 'to do'] for label in issue.labels):
                    status = TaskStatus.READY
                else:
                    status = TaskStatus.TODO
            else:  # closed
                status = TaskStatus.DONE
                
            # Map assignee
            assignee = None
            if issue.assignee:
                # Try to find member by GitHub username
                assignee = self._find_member_by_github(issue.assignee.login)
                
            # Check if task exists
            existing_task = self.db.get_task(task_id)
            
            if existing_task:
                # Update existing task
                updates = {
                    'title': issue.title,
                    'description': issue.body or '',
                    'status': status.value,
                    'assignee': assignee,
                    'updated_at': issue.updated_at
                }
                
                self.db.update_task(task_id, **updates)
                logger.info(f"Updated task {task_id} from issue #{issue.number}")
                
            else:
                # Create new task
                task = Task(
                    id=task_id,
                    title=issue.title,
                    description=issue.body or '',
                    status=status,
                    assignee=assignee,
                    priority=self._get_priority_from_labels(issue.labels),
                    project_id=self.project_id,
                    created_at=issue.created_at,
                    updated_at=issue.updated_at
                )
                
                self.db.create_task(task)
                logger.info(f"Created task {task_id} from issue #{issue.number}")
                
            # Sync labels as tags
            self._sync_labels_to_tags(task_id, issue.labels)
            
            # Add GitHub URL as metadata
            self._add_github_metadata(task_id, issue.html_url)
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to sync issue #{issue.number}: {e}")
            return None
            
        finally:
            self.db.disconnect()
            
    def sync_task_to_issue(self, task_id):
        """Sync a TracLine task to GitHub issue."""
        try:
            self.db.connect()
            
            task = self.db.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return None
                
            # Check if this is already a GitHub-synced task
            if task_id.startswith('GH-'):
                # Extract issue number
                issue_number = int(task_id.split('-')[-1])
                issue = self.repo.get_issue(issue_number)
                
                # Update existing issue
                issue.edit(
                    title=task.title,
                    body=task.description,
                    state='closed' if task.status == TaskStatus.DONE else 'open'
                )
                
                # Update labels based on status
                self._update_issue_labels(issue, task.status)
                
                # Update assignee
                if task.assignee:
                    github_user = self._get_github_user(task.assignee)
                    if github_user:
                        issue.edit(assignees=[github_user])
                        
                logger.info(f"Updated issue #{issue_number} from task {task_id}")
                return issue.number
                
            else:
                # Create new issue
                issue = self.repo.create_issue(
                    title=task.title,
                    body=f"{task.description}\n\n---\n_Synced from TracLine task: {task_id}_"
                )
                
                # Set labels based on status
                self._update_issue_labels(issue, task.status)
                
                # Set assignee
                if task.assignee:
                    github_user = self._get_github_user(task.assignee)
                    if github_user:
                        issue.edit(assignees=[github_user])
                        
                # Update task ID to include issue number
                new_task_id = f"GH-{self.project_id}-{issue.number}"
                # Note: This would require updating all references to the task
                
                logger.info(f"Created issue #{issue.number} from task {task_id}")
                return issue.number
                
        except GithubException as e:
            logger.error(f"Failed to sync task {task_id} to GitHub: {e}")
            return None
            
        finally:
            self.db.disconnect()
            
    def sync_all_issues(self):
        """Sync all issues from GitHub to TracLine."""
        if not self.repo:
            if not self.connect():
                return []
                
        synced_tasks = []
        
        try:
            # Get all issues (including closed ones)
            issues = self.repo.get_issues(state='all')
            
            for issue in issues:
                # Skip pull requests
                if issue.pull_request:
                    continue
                    
                task_id = self.sync_issue_to_task(issue)
                if task_id:
                    synced_tasks.append(task_id)
                    
            logger.info(f"Synced {len(synced_tasks)} issues from GitHub")
            return synced_tasks
            
        except GithubException as e:
            logger.error(f"Failed to sync issues: {e}")
            return synced_tasks
            
    def _find_member_by_github(self, github_username):
        """Find TracLine member by GitHub username."""
        # This would require adding a github_username field to members table
        # For now, try to match by name
        try:
            members = self.db.list_members()
            for member in members:
                if member.name.lower() == github_username.lower():
                    return member.id
            return None
        except:
            return None
            
    def _get_github_user(self, member_id):
        """Get GitHub username for a TracLine member."""
        # This would require storing GitHub username in member profile
        # For now, return None
        return None
        
    def _get_priority_from_labels(self, labels):
        """Extract priority from GitHub labels."""
        for label in labels:
            if 'priority' in label.name.lower():
                if 'high' in label.name.lower():
                    return 1
                elif 'medium' in label.name.lower():
                    return 2
                elif 'low' in label.name.lower():
                    return 3
        return 2  # Default priority
        
    def _update_issue_labels(self, issue, status):
        """Update GitHub issue labels based on task status."""
        # Remove existing status labels
        status_labels = ['todo', 'ready', 'doing', 'in progress', 'done', 'closed']
        current_labels = [l.name for l in issue.labels if l.name.lower() not in status_labels]
        
        # Add new status label
        if status == TaskStatus.TODO:
            current_labels.append('todo')
        elif status == TaskStatus.READY:
            current_labels.append('ready')
        elif status == TaskStatus.DOING:
            current_labels.append('in progress')
        elif status == TaskStatus.DONE:
            current_labels.append('done')
            
        issue.set_labels(*current_labels)
        
    def _sync_labels_to_tags(self, task_id, labels):
        """Sync GitHub labels as task tags."""
        # This would require implementing a tags system in TracLine
        pass
        
    def _add_github_metadata(self, task_id, issue_url):
        """Add GitHub metadata to task."""
        # Store GitHub URL as task metadata
        # This would require adding a metadata field to tasks table
        pass