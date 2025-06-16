"""GitHub webhook handler for TracLine."""

import hmac
import hashlib
import json
import logging
from datetime import datetime
from ..core.config import Config
from ..db.factory import DatabaseFactory
from .sync import GitHubSync

logger = logging.getLogger(__name__)


class GitHubWebhook:
    """Handle GitHub webhook events."""
    
    def __init__(self, project_id, secret=None):
        self.project_id = project_id
        self.secret = secret
        self.config = Config()
        self.sync = GitHubSync(project_id)
        
    def verify_signature(self, payload_body, signature_header):
        """Verify GitHub webhook signature."""
        if not self.secret:
            return True  # No secret configured, skip verification
            
        if not signature_header:
            return False
            
        hash_object = hmac.new(
            self.secret.encode('utf-8'),
            msg=payload_body,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        
        return hmac.compare_digest(expected_signature, signature_header)
        
    def handle_event(self, event_type, payload):
        """Handle GitHub webhook event."""
        logger.info(f"Handling GitHub {event_type} event for project {self.project_id}")
        
        handlers = {
            'issues': self._handle_issues_event,
            'issue_comment': self._handle_issue_comment_event,
            'push': self._handle_push_event,
            'pull_request': self._handle_pull_request_event,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return handler(payload)
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {'status': 'ignored', 'message': f'Event type {event_type} not handled'}
            
    def _handle_issues_event(self, payload):
        """Handle issues events (opened, edited, closed, etc.)."""
        action = payload.get('action')
        issue = payload.get('issue')
        
        if not issue:
            return {'status': 'error', 'message': 'No issue data in payload'}
            
        logger.info(f"Issue {action}: #{issue['number']} - {issue['title']}")
        
        # Sync issue to TracLine
        if self.sync.connect():
            # Convert payload issue to GitHub issue object format
            from types import SimpleNamespace
            
            # Create a simple issue object with required attributes
            issue_obj = SimpleNamespace(
                number=issue['number'],
                title=issue['title'],
                body=issue.get('body', ''),
                state=issue['state'],
                html_url=issue['html_url'],
                created_at=datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00')),
                labels=[SimpleNamespace(name=label['name']) for label in issue.get('labels', [])],
                assignee=SimpleNamespace(login=issue['assignee']['login']) if issue.get('assignee') else None
            )
            
            task_id = self.sync.sync_issue_to_task(issue_obj)
            
            if task_id:
                return {'status': 'success', 'task_id': task_id}
            else:
                return {'status': 'error', 'message': 'Failed to sync issue'}
        else:
            return {'status': 'error', 'message': 'Failed to connect to GitHub'}
            
    def _handle_issue_comment_event(self, payload):
        """Handle issue comment events."""
        action = payload.get('action')
        issue = payload.get('issue')
        comment = payload.get('comment')
        
        if not issue or not comment:
            return {'status': 'error', 'message': 'Missing issue or comment data'}
            
        logger.info(f"Issue comment {action} on #{issue['number']}")
        
        # Add comment as task log entry
        task_id = f"GH-{self.project_id}-{issue['number']}"
        
        db = DatabaseFactory.create(self.config.config.database)
        try:
            db.connect()
            
            # Check if task exists
            task = db.get_task(task_id)
            if task:
                # Add log entry
                if self.config.config.database.type == "postgresql":
                    query = """
                    INSERT INTO log_entries (task_id, description, created_at, created_by)
                    VALUES (%s, %s, %s, %s)
                    """
                    params = [
                        task_id,
                        f"GitHub comment: {comment['body']}",
                        datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00')),
                        comment['user']['login']
                    ]
                else:
                    query = """
                    INSERT INTO log_entries (task_id, description, created_at, created_by)
                    VALUES (?, ?, ?, ?)
                    """
                    params = [
                        task_id,
                        f"GitHub comment: {comment['body']}",
                        datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00')),
                        comment['user']['login']
                    ]
                    
                db.execute_query(query, params)
                db.conn.commit()
                
                return {'status': 'success', 'message': 'Comment logged'}
            else:
                return {'status': 'ignored', 'message': 'Task not found'}
                
        finally:
            db.disconnect()
            
    def _handle_push_event(self, payload):
        """Handle push events."""
        ref = payload.get('ref', '')
        commits = payload.get('commits', [])
        
        logger.info(f"Push event on {ref} with {len(commits)} commits")
        
        # Extract task references from commit messages
        task_refs = []
        for commit in commits:
            message = commit.get('message', '')
            # Look for task references like #TASK-001 or GH-PROJECT-123
            import re
            refs = re.findall(r'#?(TASK-\d+|GH-\w+-\d+)', message, re.IGNORECASE)
            task_refs.extend(refs)
            
        if task_refs:
            # Add commit references to tasks
            db = DatabaseFactory.create(self.config.config.database)
            try:
                db.connect()
                
                for task_id in set(task_refs):
                    task = db.get_task(task_id)
                    if task:
                        # Add log entry about the commit
                        if self.config.config.database.type == "postgresql":
                            query = """
                            INSERT INTO log_entries (task_id, description, created_at)
                            VALUES (%s, %s, %s)
                            """
                            params = [
                                task_id,
                                f"Referenced in commit: {commits[0]['id'][:7]}",
                                datetime.now()
                            ]
                        else:
                            query = """
                            INSERT INTO log_entries (task_id, description, created_at)
                            VALUES (?, ?, ?)
                            """
                            params = [
                                task_id,
                                f"Referenced in commit: {commits[0]['id'][:7]}",
                                datetime.now()
                            ]
                            
                        db.execute_query(query, params)
                        
                db.conn.commit()
                
            finally:
                db.disconnect()
                
        return {'status': 'success', 'tasks_referenced': list(set(task_refs))}
        
    def _handle_pull_request_event(self, payload):
        """Handle pull request events."""
        action = payload.get('action')
        pr = payload.get('pull_request')
        
        if not pr:
            return {'status': 'error', 'message': 'No pull request data'}
            
        logger.info(f"Pull request {action}: #{pr['number']} - {pr['title']}")
        
        # Could create a task for PR reviews
        # For now, just log it
        return {'status': 'ignored', 'message': 'Pull request events not yet implemented'}