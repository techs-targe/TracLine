# TracLine User Guide: Collaborative Development with Claude Code

This comprehensive guide will walk you through setting up TracLine for collaborative development using Claude Code, from installation to parallel development across multiple team members.

## Table of Contents

1. [Installation](#installation)
2. [Initial Setup](#initial-setup)
3. [Project Creation](#project-creation)
4. [Team Member Configuration](#team-member-configuration)
5. [Claude Code Development Setup](#claude-code-development-setup)
6. [Parallel Development Workflow](#parallel-development-workflow)
7. [Advanced Features](#advanced-features)
   - [File Traceability](#file-traceability)
   - [GitHub Integration](#github-integration)
   - [Project-Specific Settings](#project-specific-settings)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL (recommended) or SQLite
- Claude Code CLI tool
- Git

### Installation Options

TracLine can be installed in two ways: locally for a specific project or globally for system-wide use.

#### Option 1: Local Installation (Project-specific)

```bash
# Clone the repository
git clone git@github.com:techs-targe/TracLine.git
cd TracLine

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install TracLine
pip install -e .  # Editable installation for development
```

#### Option 2: Global Installation (System-wide)

```bash
# Clone the repository
git clone git@github.com:techs-targe/TracLine.git
cd TracLine

# Install globally in your Python environment
pip install .

# For global installation with sample configuration
cp CLAUDE.md.sample.globalinstall ~/.tracline/CLAUDE.md
```

**Global Installation Configuration:**

After global installation, set up your configuration:

```bash
# Create configuration directory
mkdir -p ~/.config/tracline

# Copy configuration file
cp tracline.yaml.example ~/.config/tracline/tracline.yaml

# Edit configuration with your database settings
nano ~/.config/tracline/tracline.yaml

# Set environment variable (optional)
echo 'export TRACLINE_CONFIG=~/.config/tracline/tracline.yaml' >> ~/.bashrc
source ~/.bashrc
```

**Verify Installation:**

```bash
# Check if tracline command is available
which tracline

# Display version
tracline --version

# Show help
tracline --help
```

### Step 2: Install Claude Code

Follow the installation instructions at [Claude Code Documentation](https://claude.ai/code).

```bash
# Verify installation
claude --version
```

## Initial Setup

### Step 1: Copy Development Guide Template

Before starting development, copy the development guide template and customize it for your environment:

```bash
# Copy the template
cp CLAUDE.md.sample CLAUDE.md

# Edit with your specific environment settings
nano CLAUDE.md
```

**Important Configuration Items in CLAUDE.md:**

1. **Project Paths**: Update paths to match your local environment
2. **Database Settings**: Configure your PostgreSQL or SQLite settings
3. **Team Member IDs**: Set up your specific team member identifiers
4. **Project Information**: Customize project details and requirements
5. **Development Guidelines**: Adjust coding standards and practices

This file serves as your team's development reference and should be customized for your specific TracLine installation.

### Step 2: Database Configuration

First, create the TracLine configuration directory:

```bash
# Create configuration directory
mkdir -p ~/.tracline
```

Then choose your preferred database backend and configure it:

#### Option A: PostgreSQL (Recommended)

```bash
# Copy PostgreSQL configuration
cp postgres_config.yaml tracline.yaml

# Edit configuration as needed
nano tracline.yaml
```

**Note**: PostgreSQL stores data in the PostgreSQL server database (`tracline` database by default).

#### Option B: SQLite (Simpler setup)

```bash
# Copy SQLite configuration
cp sqlite_config.yaml tracline.yaml
```

**Note**: SQLite will create the database file at `~/.tracline/tracline.db` automatically.

### Step 2: Initialize Database

```bash
# For PostgreSQL
python scripts/setup_postgres.py

# For SQLite (automatic initialization)
# Database will be created automatically on first run
```

### Step 3: Verify Installation

```bash
# Test TracLine CLI
tracline --help

# Start web interface (optional)
cd web
python run_postgres_app.py
```

Access the web interface at `http://localhost:8000` to verify everything is working.

## Project Creation

### Step 1: Create Your First Project

```bash
# Create a new project
tracline project create --id "MAIN-PROJECT" --name "Main Development Project" --description "Collaborative development project"

# Verify project creation
tracline project list
```

### Step 2: Initialize Project Structure

```bash
# Create basic project structure
tracline project init --project-id "MAIN-PROJECT"
```

## Team Member Configuration

### Step 1: Add Team Members

Create team members for your collaborative development:

```bash
# Add team leader
tracline member add --id "TECH-LEADER" --name "Tech Leader" --role "OWNER" --position "LEADER" --project-id "MAIN-PROJECT"

# Add developers
tracline member add --id "DEV1" --name "Developer 1" --role "ENGINEER" --position "MEMBER" --project-id "MAIN-PROJECT" --leader-id "TECH-LEADER"
tracline member add --id "DEV2" --name "Developer 2" --role "ENGINEER" --position "MEMBER" --project-id "MAIN-PROJECT" --leader-id "TECH-LEADER"

# Add AI team members
tracline member add --id "AI1" --name "AI Assistant 1" --role "ENGINEER" --position "MEMBER" --project-id "MAIN-PROJECT" --leader-id "TECH-LEADER"
tracline member add --id "AI2" --name "AI Assistant 2" --role "ENGINEER" --position "MEMBER" --project-id "MAIN-PROJECT" --leader-id "TECH-LEADER"

# Verify team setup
tracline member list --project-id "MAIN-PROJECT"
```

### Step 2: Manage Team Members

TracLine provides comprehensive team member management commands:

```bash
# Show member details
tracline member show DEV1

# Update member information
tracline member update DEV1 --name "Senior Developer 1" --role "SENIOR_ENGINEER"

# Change member position in hierarchy
tracline member change-position DEV1 SENIOR_MEMBER

# Change member's leader
tracline member change-leader DEV2 DEV1

# View team structure
tracline member team-structure

# Delete a member (with confirmation)
tracline member delete TEMP-MEMBER --confirm
```

### Step 3: Create Initial Tasks

```bash
# Create sample tasks for team members (using 'add' command)
tracline add "BACKEND-001" "Setup API endpoints" --assignee "DEV1" --project "MAIN-PROJECT"
tracline add "FRONTEND-001" "Create user interface" --assignee "DEV2" --project "MAIN-PROJECT"
tracline add "AI-001" "Implement automation" --assignee "AI1" --project "MAIN-PROJECT"
tracline add "ML-001" "Data analysis features" --assignee "AI2" --project "MAIN-PROJECT"

# Attach files to tasks
tracline attach BACKEND-001 docs/api_spec.md
tracline attach FRONTEND-001 designs/ui_mockup.png

# Add log entries
tracline log BACKEND-001 "Started API design phase" --level INFO
tracline log FRONTEND-001 "Reviewing UI requirements" --level INFO

# Create task relationships
tracline link BACKEND-001 FRONTEND-001 --type "blocks"
```

### Step 4: Task Management Commands

TracLine provides various commands for managing tasks:

```bash
# List tasks (multiple ways)
tracline list --project "MAIN-PROJECT"
tracline ls-tasks --project "MAIN-PROJECT"  # v1 compatibility alias

# Show task details with different options
tracline show BACKEND-001 --logs --files --relationships

# Update task properties
tracline update BACKEND-001 --status "DOING" --priority 5

# Assign task to different member
tracline assign BACKEND-001 "SENIOR-DEV"

# Mark task as complete directly (bypasses workflow)
tracline complete BACKEND-001

# List files attached to task
tracline ls-files BACKEND-001 --details

# List task relationships
tracline ls-relations BACKEND-001
```

## Claude Code Development Setup

### Step 1: Prepare Development Environment

Before launching Claude Code, ensure your development environment is properly configured:

#### A. Copy and Customize Development Guide

```bash
# For project-local TracLine installation
cp CLAUDE.md.sample CLAUDE.md

# For global TracLine installation (pip install tracline)
cp CLAUDE.md.sample.globalinstall CLAUDE.md

# Open and edit with your environment details
nano CLAUDE.md
```

**Choose the right template:**
- `CLAUDE.md.sample` - For TracLine installed within your project directory
- `CLAUDE.md.sample.globalinstall` - For TracLine installed globally via pip/pipx

**Key items to customize in CLAUDE.md:**

- **Project Root Path**: Set the absolute path to your project (not TracLine)
- **Database Configuration**: Match your `~/.tracline/config.yaml` settings
- **Member Information**: Define your team member IDs and roles
- **Development Standards**: Adjust coding guidelines for your team
- **Environment Variables**: Set any custom environment variables

#### B. Validate Configuration

```bash
# Verify TracLine CLI is working
tracline --help

# Test database connection
tracline project list

# Check web interface (optional)
cd web && python run_postgres_app.py &
curl http://localhost:8000
```

### Step 2: Understand the Scripts

TracLine provides pre-configured Claude Code launch scripts for different team members:

- `scripts/claude-code/launch-claude-dev1.sh` - For DEV1 (Backend focus)
- `scripts/claude-code/launch-claude-dev2.sh` - For DEV2 (Frontend focus)
- `scripts/claude-code/launch-claude-ai1.sh` - For AI1 (Automation focus)
- `scripts/claude-code/launch-claude-ai2.sh` - For AI2 (ML/Data focus)
- `scripts/claude-code/launch-claude-template.sh` - Template for custom roles

### Step 2: Configure Scripts for Your Environment

Edit the template script to match your setup:

```bash
# Edit the main configuration
nano scripts/claude-code/launch-claude-template.sh

# Update these variables:
# - TRACLINE_PROJECT_ID (set to your project ID)
# - GH_TOKEN (if using GitHub integration)
# - Any database connection overrides
```

### Step 3: Customize Member Scripts

Each member script can be customized for specific responsibilities:

```bash
# Example: Customize DEV1 script
nano scripts/claude-code/launch-claude-dev1.sh

# Modify:
# - DEV_FOCUS areas
# - DEV_RESPONSIBILITIES
# - Any member-specific environment variables
```

## Parallel Development Workflow

### Step 1: Team Setup

1. **Distribute Scripts**: Each team member should have access to their specific launch script
2. **Terminal Sessions**: Each member opens a separate terminal/console
3. **Project Sync**: Ensure all members have the latest project code

### Step 2: Launch Claude Code Sessions

Each team member runs their specific script:

```bash
# Developer 1 (Backend focus)
./scripts/claude-code/launch-claude-dev1.sh

# Developer 2 (Frontend focus) - in separate terminal
./scripts/claude-code/launch-claude-dev2.sh

# AI Assistant 1 (Automation) - in separate terminal
./scripts/claude-code/launch-claude-ai1.sh

# AI Assistant 2 (ML/Data) - in separate terminal
./scripts/claude-code/launch-claude-ai2.sh
```

### Step 3: Coordinated Development

Once all Claude Code sessions are running:

1. **Task Assignment**: Each member works on their assigned tasks
2. **Real-time Collaboration**: Use TracLine web interface for task tracking
3. **Code Coordination**: Use Git branches for parallel development
4. **Progress Tracking**: Update task status through CLI or web interface

### Step 4: Development Workflow Example

```bash
# DEV1 (Backend) workflow
tracline task show --id "BACKEND-001"  # Check task details
# ... develop backend features ...
tracline task update --id "BACKEND-001" --status "DOING"
# ... continue development ...
tracline task update --id "BACKEND-001" --status "DONE"

# DEV2 (Frontend) workflow
tracline task show --id "FRONTEND-001"
# ... develop frontend features ...
tracline task update --id "FRONTEND-001" --status "DOING"
# ... continue development ...
tracline task update --id "FRONTEND-001" --status "DONE"
```

## Advanced Features

### Configuration Management

TracLine provides commands for managing configuration:

```bash
# View current configuration
tracline config

# Migrate from TracLine v1
tracline migrate --from-v1 /path/to/old/tracline

# Migrate SQLite database to PostgreSQL
tracline migrate --to-postgresql
```

### Web Interface Features

The web interface includes several advanced features:

1. **File Viewer**: View file contents with syntax highlighting
   - Navigate to the Traceability Matrix
   - Click on any file path to view its contents
   - Use the copy button to copy code snippets

2. **Copy Buttons**: Easy copy functionality throughout the interface
   - Copy task IDs, file paths, and code snippets with one click
   - Syntax-highlighted code blocks with copy buttons

3. **Photo Upload**: Manage team member profile photos
   - Upload and crop profile images
   - Automatic resizing and optimization
   - Support for JPG, PNG formats

### File Traceability

TracLine provides powerful file traceability features to track relationships between files and tasks.

#### Tracking File References

```bash
# Associate files with tasks
tracline trace add-file TASK-001 src/main.py
tracline trace add-file TASK-001 tests/test_main.py

# Find tasks referencing a file
tracline trace ls-trace src/main.py

# View file reference statistics
tracline trace stats -p PROJECT1
```

#### Real-time File Monitoring

Enable automatic file tracking:

```bash
# Start monitoring project directory
tracline monitor start PROJECT1 /path/to/project --daemon

# Monitor specific file types
tracline monitor start PROJECT1 . -d -e .py -e .js -e .ts

# Check monitor status
tracline monitor status

# View file access history
tracline monitor history PROJECT1
```

See [File Traceability Guide](TRACEABILITY.md) and [File Monitoring Guide](MONITORING.md) for detailed information.

### GitHub Integration

Synchronize TracLine tasks with GitHub Issues:

#### Setup

```bash
# Configure GitHub integration
export GITHUB_TOKEN=ghp_your_token_here
tracline github setup PROJECT1 -r owner/repository

# Test connection
tracline github test PROJECT1
```

#### Synchronization

```bash
# Sync all issues from GitHub
tracline github sync PROJECT1 --all

# Sync specific issue
tracline github sync PROJECT1 --issue 123

# Push task to GitHub
tracline github sync PROJECT1 --task TASK-001

# Check integration status
tracline github status
```

#### Webhook Configuration

1. Get webhook URL: `https://your-server:8000/api/github/webhook/PROJECT1`
2. Add to GitHub repository settings
3. Select events: Issues, Issue comments, Push

See [GitHub Integration Guide](GITHUB_INTEGRATION.md) for complete setup instructions.

### Project-Specific Settings

Each project can have custom configurations:

```yaml
# Project settings stored in database
project_id: PROJECT1
monitor_enabled: true
monitor_path: /path/to/project
monitor_extensions: ['.py', '.js', '.ts']
github_enabled: true
github_repo: owner/repository
```

#### Strict Mode Enforcement

TracLine supports three types of strict mode enforcement to ensure quality and compliance:

##### 1. Document Read Confirmation

When enabled, requires team members to confirm they have read associated documents before marking tasks as done.

```bash
# Enable document read confirmation
tracline project settings PROJECT1 --strict-doc-read

# Workflow example
tracline next  # Shows task with document warning
# ⚠️  Document Read Warning
# This task has associated documents. Please read them before marking the task as done:
# • docs/api_spec.md
# • docs/implementation_guide.pdf

tracline done TASK-001
# ❌ Document Read Confirmation Required
# Please run: tracline done TASK-001 --confirm-read ABC123

tracline done TASK-001 --confirm-read ABC123
# ✓ Document read confirmed
# Task TASK-001 advanced: IN_PROGRESS → DONE
```

##### 2. File Reference Enforcement

When enabled, prevents marking tasks as done without associated files.

```bash
# Enable file reference enforcement
tracline project settings PROJECT1 --strict-file-ref

# Workflow example
tracline done TASK-001
# ❌ File Reference Required
# This task must have at least one associated file before it can be marked as done.
# Use 'tracline attach <file>' or 'tracline trace add-file <file> <task_id>' to associate files.

# Associate files
tracline trace add-file TASK-001 src/feature.py
tracline done TASK-001  # Now succeeds
```

##### 3. Log Entry Enforcement

When enabled, requires at least one log entry before marking tasks as done.

```bash
# Enable log entry enforcement  
tracline project settings PROJECT1 --strict-log-entry

# Workflow example
tracline done TASK-001
# ❌ Log Entry Required
# This task must have at least one log entry before it can be marked as done.
# Use 'tracline log <message>' to add a log entry.

# Add log entry
tracline log "Implemented feature with unit tests"
tracline done TASK-001  # Now succeeds
```

###### Managing Strict Mode Settings

```bash
# View current settings
tracline project settings PROJECT1

# Enable multiple strict modes
tracline project settings PROJECT1 --strict-doc-read --strict-file-ref --strict-log-entry

# Disable specific mode
tracline project settings PROJECT1 --no-strict-doc-read

# Environment variable overrides (useful for CI/CD)
export TRACLINE_STRICT_DOC_READ_PROJECT1=true
export TRACLINE_STRICT_FILE_REF_PROJECT1=true
export TRACLINE_STRICT_LOG_ENTRY_PROJECT1=true

# Global strict mode (applies to all projects)
export TRACLINE_STRICT_DOC_READ=true
export TRACLINE_STRICT_FILE_REF=true
export TRACLINE_STRICT_LOG_ENTRY=true
```

#### Project Root Directory Management

TracLine supports configuring project root directories to enable relative file paths in file associations:

```bash
# Set project root directory
tracline projectroot set PROJECT1 /path/to/projects/myproject

# Get current project root
tracline projectroot get PROJECT1

# Clear project root (require absolute paths)
tracline projectroot clear PROJECT1 --confirm

# List all projects with configured root directories
tracline projectroot list
```

##### Benefits of Project Root Configuration

1. **Relative Paths**: Use relative paths in file associations instead of absolute paths
2. **Portability**: Tasks remain valid across different environments
3. **Cleaner Display**: Shorter, more readable file paths in UI
4. **File Viewer**: Enables file viewing in the web interface

##### File Association with Project Root

```bash
# With project root set
tracline projectroot set PROJECT1 /path/to/projects/myproject
tracline trace add-file TASK-001 src/main.py  # Stored as relative path

# Without project root (absolute path required)
tracline trace add-file TASK-001 /path/to/projects/myproject/src/main.py
```

## Best Practices

### 1. Environment Isolation

- Each team member should use their dedicated script
- Keep member-specific configurations separate
- Use different Git branches for parallel development

### 2. Communication

- Use TracLine web interface for progress visibility
- Update task status regularly
- Use task comments for coordination

### 3. Code Management

```bash
# Recommended Git workflow
git checkout -b feature/member-name/task-id
# ... develop feature ...
git add .
git commit -m "feat: implement task TASK-ID"
git push origin feature/member-name/task-id
# ... create pull request ...
```

### 4. Task Coordination

- Assign tasks clearly to specific members
- Use task relationships for dependencies
- Regular status updates through TracLine

### 5. Development Standards

- Follow consistent coding standards
- Use TracLine's file association features
- Document changes in task logs

## Troubleshooting

### Common Issues

#### Claude Code Not Found

```bash
# Verify Claude Code installation
which claude
claude --version

# If not found, reinstall Claude Code
# Follow installation guide at https://claude.ai/code
```

#### TracLine CLI Issues

```bash
# Verify TracLine installation
which tracline
tracline --version

# Reinstall if needed
pip install -e .
```

#### Database Connection Issues

```bash
# Check database configuration
cat tracline.yaml

# Test database connection
python -c "from tracline.core.config import Config; print('Config loaded successfully')"
```

#### Permission Issues

```bash
# Make scripts executable
chmod +x scripts/claude-code/*.sh

# Check file permissions
ls -la scripts/claude-code/
```

### Environment Variables Debug

```bash
# Check environment in Claude Code session
echo $PROJECT_ROOT
echo $MEMBER_ID
echo $TRACLINE_PROJECT_ID

# Verify paths
echo $PATH
which tracline
```

### Web Interface Issues

```bash
# Start web interface with debug
cd web
python run_postgres_app.py --debug

# Check logs
tail -f web/logs/tracline.log
```

## Advanced Usage

### Custom Member Roles

Create custom launch scripts for specific roles:

```bash
# Copy template
cp scripts/claude-code/launch-claude-template.sh scripts/claude-code/launch-claude-designer.sh

# Customize for designer role
nano scripts/claude-code/launch-claude-designer.sh
```

### Integration with CI/CD

```bash
# Set up automated testing
export TRACLINE_TEST_MODE=true
./scripts/claude-code/launch-claude-dev1.sh

# Run tests in Claude Code environment
pytest tests/
```

### Multiple Projects

```bash
# Work with different projects
export TRACLINE_PROJECT_ID="PROJECT-A"
./scripts/claude-code/launch-claude-dev1.sh

# In another terminal
export TRACLINE_PROJECT_ID="PROJECT-B"
./scripts/claude-code/launch-claude-dev2.sh
```

---

## Quick Start Summary

1. **Install**: `pip install -e .`
2. **Setup Config Directory**: `mkdir -p ~/.tracline`
3. **Configure Database**: `cp sqlite_config.yaml tracline.yaml` (or postgres_config.yaml)
4. **Setup Development Guide**: `cp CLAUDE.md.sample CLAUDE.md` (edit with your settings)
5. **Create Project**: `tracline project create --id "MAIN-PROJECT" --name "My Project"`
6. **Add Members**: `tracline member add --id "DEV1" --name "Developer 1" ...`
7. **Launch Claude**: `./scripts/claude-code/launch-claude-dev1.sh`
8. **Start Developing**: Use Claude Code for parallel development!

For more detailed information, visit the [TracLine Documentation](README.md) or check the [Database Configuration Guide](database_configuration.md).

---

**Happy Collaborative Development with TracLine and Claude Code! 🚀**