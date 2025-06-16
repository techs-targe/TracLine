# TracLine Correct Command Usage Guide

## Core Task Management

### Creating Tasks
```bash
# Basic task creation
tracline add TASK-001 "Implement user authentication"

# With options
tracline add TASK-002 "API Documentation" -j PROJECT-ID -a john -p 3 -d "Write comprehensive API docs"
```

### Listing Tasks
```bash
# List all tasks for current user
tracline list

# Filter by project
tracline list -j PROJECT-ID

# Show all tasks including done
tracline list --show-done

# Filter by status
tracline list -s TODO
```

### Task Details
```bash
# Basic details
tracline show TASK-001

# With additional info
tracline show TASK-001 --logs --files --relationships
```

### Updating Tasks
```bash
# Update title
tracline update TASK-001 --title "Updated title here"

# Update status
tracline update TASK-001 --status READY

# Update multiple fields
tracline update TASK-001 --assignee jane --priority 5
```

## Workflow Commands

### Getting Next Task
```bash
# Next task for current user/project
tracline next

# Next task for specific project
tracline next -j PROJECT-ID
```

### Completing Tasks
```bash
# Mark as done (respects workflow)
tracline done TASK-001

# Complete directly
tracline complete TASK-001

# With document confirmation
tracline done TASK-001 --confirm-read ABC
```

## File Management

### Attaching Files
```bash
# Basic attachment
tracline attach TASK-001 /path/to/file.pdf

# With description
tracline attach TASK-001 /path/to/file.pdf --description "Design document"
```

### File Traceability
```bash
# Add file to task
tracline trace add-file /absolute/path/to/file.py TASK-001

# List tasks referencing a file
tracline trace ls-trace /absolute/path/to/file.py

# Show statistics
tracline trace stats
```

## Project Management

### Creating Projects
```bash
# Create new project
tracline project create PROJECT-001 "Web Platform Redesign"

# Update project
tracline project update PROJECT-001 --name "Updated Project Name"
```

### Project Settings
```bash
# Enable strict modes
tracline project settings PROJECT-001 --strict-file-ref --strict-doc-read

# Show current settings
tracline project settings PROJECT-001 --show
```

### Project Root
```bash
# Set project root directory
tracline projectroot set PROJECT-001 /path/to/project

# Get project root
tracline projectroot get PROJECT-001

# List all project roots
tracline projectroot list
```

## Team Management

### Managing Members
```bash
# List all members
tracline member list

# Add new member
tracline member add MEMBER-001 "John Doe"

# Update member
tracline member update MEMBER-001 --position LEADER --role MANAGER

# Show team structure
tracline member team-structure LEADER-ID
```

## Relationships

### Creating Links
```bash
# Basic relationship
tracline link PARENT-001 CHILD-001

# With type
tracline link TASK-001 TASK-002 --type blocks
```

### Viewing Relations
```bash
# For specific task
tracline ls-relations TASK-001

# Filter by type
tracline ls-relations TASK-001 --type blocks
```

## Logging

### Adding Log Entries
```bash
# Basic log
tracline log TASK-001 "Completed initial research"

# With level
tracline log TASK-001 "Found critical bug" --level ERROR
```

## Monitoring

### File System Monitoring
```bash
# Start monitoring
tracline monitor start PROJECT-001 /path/to/watch

# Check status
tracline monitor status

# Stop monitoring
tracline monitor stop PROJECT-001

# View history
tracline monitor history PROJECT-001
```

## GitHub Integration

### Setup and Management
```bash
# Check status
tracline github status

# Setup for project
tracline github setup PROJECT-001

# Test connection
tracline github test PROJECT-001

# Sync with GitHub
tracline github sync PROJECT-001
```

## Database Management

### Initialization
```bash
# First time setup
tracline init

# Force reinitialize
tracline init --force
```

### Migration
```bash
# From SQLite to PostgreSQL
tracline migrate --to-postgresql

# From v1 database
tracline migrate --from-v1 /path/to/v1.db
```

## Notes

1. **Quotes**: Use double quotes for multi-word arguments in bash
2. **IDs**: Task and Project IDs should follow your naming convention
3. **Paths**: File paths for trace commands must be absolute
4. **Enum Values**: Status and position values must match defined enums
5. **Current Context**: Many commands use current project/user from config