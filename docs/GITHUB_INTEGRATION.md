# GitHub Integration Guide

> **⚠️ EXPERIMENTAL FEATURE NOTICE**
> 
> GitHub Integration is currently an experimental feature under active research and development. While basic functionality is available, the feature is not yet production-ready and may undergo significant changes. We recommend using it only in test environments at this time.
>
> Full implementation with stable API and comprehensive features is planned for future releases. We welcome your feedback and contributions to help shape this feature.

TracLine provides seamless integration with GitHub, enabling bidirectional synchronization between TracLine tasks and GitHub Issues. This guide covers setup, usage, and best practices for GitHub integration.

## Overview

GitHub integration features:
- Bidirectional sync between tasks and issues
- Automatic status updates
- Comment synchronization
- Webhook support for real-time updates
- Project-specific configuration
- Secure token management

## Prerequisites

Before setting up GitHub integration:

1. **GitHub Personal Access Token**
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with these scopes:
     - `repo` (Full control of private repositories)
     - `write:issues` (Write access to issues)
     - `read:org` (Read org and team membership)

2. **Repository Access**
   - Ensure you have write access to the target repository
   - Repository must have Issues enabled

3. **TracLine Setup**
   - TracLine installed and configured
   - Project created in TracLine

## Initial Setup

### 1. Configure GitHub Integration

```bash
# Set token via environment variable (recommended)
export GITHUB_TOKEN=ghp_your_token_here
tracline github setup PROJECT1 -r owner/repository

# Or provide token directly
tracline github setup PROJECT1 -r owner/repository -t ghp_your_token_here

# Example
export GITHUB_TOKEN=ghp_abcdef123456
tracline github setup WEBPROJECT -r mycompany/webapp
```

### 2. Test Connection

```bash
# Verify GitHub connection
tracline github test PROJECT1

# Expected output:
Testing GitHub connection for project PROJECT1...
✅ Successfully connected to repository: mycompany/webapp
   Description: Web application for task management
   Stars: 42
   Open Issues: 15

Recent open issues:
   #123: Fix login page styling
   #122: Add user profile feature
   #121: Database migration error
```

### 3. Check Integration Status

```bash
# View all projects' GitHub status
tracline github status

# Output:
GitHub Integration Status:
+------------+--------------+-----------------+-------------------+
| Project ID | Project Name | GitHub Enabled  | Repository        |
+============+==============+=================+===================+
| PROJECT1   | Web App      | ✅              | mycompany/webapp  |
| PROJECT2   | Mobile App   | ❌              | -                 |
| PROJECT3   | Backend API  | ✅              | mycompany/api     |
+------------+--------------+-----------------+-------------------+
```

## Synchronization

### Sync All Issues

Import all issues from GitHub to TracLine:

```bash
# Sync all issues (open and closed)
tracline github sync PROJECT1 --all

# Output:
Syncing all issues for project PROJECT1...
✅ Synced 47 issues
```

### Sync Specific Issue

```bash
# Sync a single issue
tracline github sync PROJECT1 --issue 123

# Output:
Syncing issue #123...
✅ Synced issue #123 to task GH-PROJECT1-123
```

### Sync Task to GitHub

Create or update a GitHub issue from a TracLine task:

```bash
# Sync TracLine task to GitHub
tracline github sync PROJECT1 --task TASK-001

# Output:
Syncing task TASK-001 to GitHub...
✅ Synced task TASK-001 to issue #124
```

## Task-Issue Mapping

### Automatic ID Generation

When syncing from GitHub, tasks are created with IDs in format:
- `GH-{PROJECT_ID}-{ISSUE_NUMBER}`
- Example: `GH-PROJECT1-123`

### Status Mapping

| GitHub Issue State | GitHub Labels | TracLine Status |
|-------------------|---------------|-----------------|
| Open | - | TODO |
| Open | ready, to do | READY |
| Open | in progress, doing | DOING |
| Closed | - | DONE |

### Field Mapping

| GitHub Field | TracLine Field |
|--------------|----------------|
| Title | Title |
| Body | Description |
| Assignee | Assignee (by username match) |
| Labels | Tags (future feature) |
| Created at | Created at |
| Updated at | Updated at |

## Webhook Configuration

For real-time synchronization, configure GitHub webhooks:

### 1. Get Webhook URL

Your webhook URL format:
```
https://your-server.com:8000/api/github/webhook/PROJECT1
```

### 2. Configure in GitHub

1. Go to your repository → Settings → Webhooks
2. Click "Add webhook"
3. Configure:
   - **Payload URL**: Your webhook URL
   - **Content type**: `application/json`
   - **Secret**: (optional) Set a webhook secret
   - **Events**: Select individual events:
     - Issues
     - Issue comments
     - Pull requests (optional)
     - Pushes (optional)

### 3. Set Webhook Secret (Optional)

```bash
# Add webhook secret to TracLine
# This would require updating the database schema
```

### 4. Webhook Events Handled

- **Issues**: Created, edited, closed, reopened
- **Issue comments**: Created, edited, deleted
- **Push**: Extracts task references from commits
- **Pull requests**: Future implementation

## Working with Synced Tasks

### Viewing Synced Tasks

```bash
# List all GitHub-synced tasks
tracline list -p PROJECT1 | grep "GH-"

# Show specific synced task
tracline show GH-PROJECT1-123
```

### Updating Synced Tasks

Changes to synced tasks can be pushed back to GitHub:

```bash
# Update task status
tracline update GH-PROJECT1-123 --status DOING

# Sync changes to GitHub
tracline github sync PROJECT1 --task GH-PROJECT1-123
```

### Automatic Updates via Webhook

With webhooks configured:
1. GitHub issue updated → TracLine task updated automatically
2. Comments added to issue → Logged in TracLine
3. Issue closed → Task marked as DONE

## Team Member Mapping

For proper assignee synchronization:

### Current Behavior
- Matches by username (case-insensitive)
- Falls back to unassigned if no match

### Future Enhancement
Add GitHub username to member profiles:
```bash
# Future feature
tracline member update john --github-username johndoe
```

## Best Practices

### 1. Token Security

```bash
# Use environment variables
export GITHUB_TOKEN=ghp_xxx

# Add to .bashrc or .zshrc
echo 'export GITHUB_TOKEN=ghp_xxx' >> ~/.bashrc

# Never commit tokens
echo 'GITHUB_TOKEN' >> .gitignore
```

### 2. Selective Synchronization

- Don't sync all issues if you have many
- Use labels to filter relevant issues
- Sync incrementally

### 3. Workflow Integration

```bash
# Daily sync routine
#!/bin/bash
# sync_github.sh

PROJECTS="PROJECT1 PROJECT2 PROJECT3"

for project in $PROJECTS; do
  echo "Syncing $project..."
  tracline github sync $project --all
done
```

### 4. Commit Message References

Reference TracLine tasks in commits:
```bash
git commit -m "Fix authentication bug #TASK-001"
git commit -m "Implement feature GH-PROJECT1-123"
```

These will be detected by push webhooks.

## Troubleshooting

### Connection Issues

**Error**: "Failed to connect to GitHub repository"

**Solutions**:
```bash
# Check token permissions
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user

# Verify repository access
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo

# Test with tracline
tracline github test PROJECT1
```

### Sync Failures

**Error**: "Failed to sync issue #123"

**Common causes**:
- Invalid token
- Insufficient permissions
- API rate limits
- Network issues

**Debug steps**:
```bash
# Check GitHub API status
curl https://api.github.com/status

# View detailed error logs
tail -f tracline.log
```

### Webhook Issues

**Problem**: Webhooks not triggering updates

**Debugging**:
1. Check webhook delivery in GitHub settings
2. Verify webhook URL is accessible
3. Check TracLine logs
4. Test with curl:

```bash
# Test webhook endpoint
curl -X POST https://your-server:8000/api/github/webhook/PROJECT1 \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: ping" \
  -d '{"zen": "Design for failure."}'
```

### Rate Limiting

GitHub API has rate limits:
- Authenticated: 5,000 requests/hour
- Unauthenticated: 60 requests/hour

Monitor your usage:
```bash
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit
```

## Advanced Usage

### Bulk Operations

```python
# Script for bulk synchronization
import subprocess
import json

# Get all open issues
issues = json.loads(subprocess.check_output([
    "gh", "issue", "list", "--json", "number,title", "--limit", "100"
]))

for issue in issues:
    print(f"Syncing issue #{issue['number']}: {issue['title']}")
    subprocess.run([
        "tracline", "github", "sync", "PROJECT1", 
        "--issue", str(issue['number'])
    ])
```

### Custom Label Mapping

Create custom status mappings based on labels:
```python
# Future enhancement example
LABEL_TO_STATUS = {
    'bug': ('TODO', 3),  # Status, Priority
    'enhancement': ('READY', 2),
    'in-review': ('TESTING', 1),
}
```

### Integration with CI/CD

```yaml
# GitHub Actions example
name: Sync TracLine
on:
  issues:
    types: [opened, edited, closed]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Sync to TracLine
        run: |
          tracline github sync ${{ secrets.PROJECT_ID }} \
            --issue ${{ github.event.issue.number }}
        env:
          GITHUB_TOKEN: ${{ secrets.TRACLINE_TOKEN }}
```

## Disabling Integration

To disable GitHub integration:

```bash
# Disable for a project
tracline github setup PROJECT1 -r owner/repo --disable

# This will:
# - Stop webhook processing
# - Preserve existing synced tasks
# - Remove stored tokens
```

## Security Considerations

1. **Token Storage**
   - Tokens are encrypted in database
   - Use environment variables when possible
   - Rotate tokens regularly

2. **Webhook Security**
   - Use webhook secrets
   - Validate signatures
   - Use HTTPS only

3. **Access Control**
   - Limit token scopes
   - Use fine-grained tokens
   - Monitor token usage

## Future Enhancements

Planned features:
- Pull request integration
- Milestone synchronization
- Project board integration
- Custom field mapping
- Two-way comment sync
- Attachment synchronization

## See Also

- [User Guide](USER_GUIDE.md) - General TracLine usage
- [File Monitoring](MONITORING.md) - Automatic file tracking
- [API Documentation](../README.md#api-endpoints) - REST API reference