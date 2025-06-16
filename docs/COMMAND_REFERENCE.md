# TracLine Command Reference

## Quick Start

```bash
tracline init                  # Initialize database
tracline next                  # Get next task
tracline done                  # Advance task state
tracline list                  # List tasks
```

## Task Management

```bash
# CRUD
tracline add "TASK-001" "Task title" [--description "Desc"] [--priority 1-5]
tracline show TASK-001 [--logs|--files|--doc|--json]
tracline update TASK-001 [--status STATUS] [--priority 1-5] [--title "New"]
tracline delete TASK-001 [--force]

# Listing
tracline list [--all] [--assignee "Name"] [--status TODO|READY|DOING|TESTING|DONE]
tracline ls-tasks [--project "PROJECT-ID"] [--show-done]

# Workflow
tracline next [--assignee "Name"] [--project "PROJECT-ID"]
tracline done [TASK-ID] [--confirm-read CODE] [--status STATUS]
tracline assign TASK-001 "Assignee Name"
tracline complete TASK-001  # Mark as DONE immediately
```

## File & Log Management

```bash
# Files
tracline attach TASK-001 ./path/to/file [--description "File description"]
tracline ls-files TASK-001 [--details] [--json]
tracline trace add-file ./file.txt TASK-001
tracline trace ls-trace ./file.txt  # Show which tasks reference this file

# Logs
tracline log TASK-001 "Work completed" [--level INFO|WARNING|ERROR]
```

## Project Management

```bash
# CRUD
tracline project create "PROJECT-ID" "Project Name" [--description "Desc"]
tracline project show PROJECT-ID [--json]
tracline project update PROJECT-ID [--name "New"] [--status ACTIVE|INACTIVE]
tracline project delete PROJECT-ID --force
tracline project list [--owner "OWNER-ID"] [--status ACTIVE]

# Settings (Strict Mode)
tracline project settings PROJECT-ID --strict-file-ref   # Require files
tracline project settings PROJECT-ID --strict-log-entry  # Require logs
tracline project settings PROJECT-ID --show              # View settings

# Members
tracline project add-members PROJECT-ID MEMBER-001 MEMBER-002
tracline project remove-members PROJECT-ID MEMBER-001
tracline project members PROJECT-ID [--json]

# Current Project
tracline project-current                    # Show current project
tracline project change PROJECT-ID          # Change current project
```

## Member Management

```bash
# CRUD
tracline member add "MEMBER-001" "John Doe" --role ENGINEER --position MEMBER
tracline member show MEMBER-001 [--details] [--json]
tracline member update MEMBER-001 [--name "New"] [--role PM] [--position LEADER]
tracline member delete MEMBER-001 --force
tracline member list [--role ENGINEER] [--position LEADER] [--json]

# Team Structure
tracline member change-position MEMBER-001 LEADER
tracline member change-leader MEMBER-001 LEADER-001  # Set leader
tracline member change-leader MEMBER-001             # Remove leader
tracline member team-structure LEADER-001 [--json]

# Roles: ENGINEER, DESIGNER, PM, QA, ARCHITECT, ANALYST, OTHER
# Positions: MEMBER, SUB_LEADER, LEADER
```

## Relationships

```bash
tracline link PARENT-001 CHILD-001 [--type "blocks|depends-on|relates-to"]
tracline ls-relations [TASK-001] [--type TYPE] [--json]
```

## Advanced Features

### Traceability Matrix
```bash
tracline trace matrix --project PROJECT-ID [--format json|html]
tracline trace matrix --task TASK-001
tracline trace matrix --file ./src/main.py
```

### GitHub Integration
```bash
tracline github sync [PROJECT-ID] [--task TASK-001]
tracline github webhook --port 8080
tracline github status
```

### File Monitoring
```bash
tracline monitor start [--interval 60] [--project PROJECT-ID]
tracline monitor stop
tracline monitor status
```

### Migration & System
```bash
# Database
tracline init [--force] [--sample-data]
tracline migrate --from-v1 ./old_taskman.db
tracline migrate --to-postgresql

# Configuration
tracline config [--show]
tracline config --set database.type postgresql
tracline config --get defaults.assignee
tracline projectroot set PROJECT-ID ./path/to/project
tracline projectroot get PROJECT-ID
```

## Environment Variables

```bash
export TASK_ASSIGNEE="Your Name"              # Default assignee
export TRACLINE_CONFIG="./tracline.yaml"      # Config file path
export TRACLINE_DB_PASSWORD="password"        # PostgreSQL password
export GH_TOKEN="github_personal_token"       # GitHub integration
export TRACLINE_DISABLE_STRICT_MODE="true"    # Disable strict mode
```

## Status Flow

```
TODO → READY → DOING → TESTING → DONE
         ↓                ↓
      PENDING         CANCELED
```

## Strict Mode

When enabled via project settings:
- `--strict-file-ref`: Requires new file attachments before marking DONE
- `--strict-log-entry`: Requires log entries before marking DONE
- `--strict-doc-read`: Requires document read confirmation

## Web Interface

Start the web server:
```bash
cd web
python run_app.py [--port 8000] [--host 0.0.0.0]
```

Access at http://localhost:8000

## Tips

1. Use `tracline next` → work → `tracline done` workflow
2. Always associate files and logs with tasks
3. Use projects to organize work
4. Set TASK_ASSIGNEE for personalized task queue
5. Enable strict mode for quality enforcement