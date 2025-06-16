# File System Monitoring Guide

TracLine's file system monitoring feature provides real-time tracking of file changes in your project directories. This guide explains how to set up and use the monitoring system effectively.

## Overview

The monitoring system:
- Watches project directories for file changes
- Automatically updates file-task associations
- Logs file access history for auditing
- Tracks file reference counts
- Runs as a background daemon process

## Prerequisites

The monitoring feature requires:
- Python watchdog library (installed with TracLine)
- Write permissions to project directories
- Daemon support (Unix/Linux/macOS)

## Starting File Monitoring

### Basic Usage

```bash
# Start monitoring a project directory
tracline monitor start PROJECT1 /path/to/project

# Start as background daemon (recommended)
tracline monitor start PROJECT1 /path/to/project --daemon

# Monitor current directory
tracline monitor start PROJECT1 . --daemon
```

### Configuring File Extensions

By default, the monitor tracks common source code extensions. You can customize this:

```bash
# Monitor only Python and JavaScript files
tracline monitor start PROJECT1 /project -d -e .py -e .js

# Monitor all files (no extension filter)
tracline monitor start PROJECT1 /project -d

# Monitor specific extensions
tracline monitor start PROJECT1 /project -d \
  -e .py \
  -e .js \
  -e .ts \
  -e .java \
  -e .go
```

Default monitored extensions:
- `.py` - Python
- `.js` - JavaScript
- `.ts` - TypeScript
- `.java` - Java
- `.c` - C
- `.cpp` - C++
- `.h` - Header files
- `.go` - Go
- `.rs` - Rust

## Managing Monitors

### Check Monitor Status

```bash
# Show all running monitors
tracline monitor status

# Example output:
File System Monitors:
+------------+---------+-------+----------------------+--------------------+
| Project    | Status  | PID   | Path                 | Extensions         |
+============+=========+=======+======================+====================+
| PROJECT1   | running | 12345 | /path/to/project1    | .py, .js, .ts     |
| PROJECT2   | running | 12346 | /path/to/project2    | All               |
| PROJECT3   | stopped | -     | /path/to/project3    | .java, .xml       |
+------------+---------+-------+----------------------+--------------------+
```

### Stop Monitoring

```bash
# Stop monitoring for a project
tracline monitor stop PROJECT1
```

### View Monitor Logs

```bash
# Show monitor logs
tracline monitor logs PROJECT1

# Example output:
=== Monitor logs for PROJECT1 ===

--- Standard Output ---
Starting file monitor for project PROJECT1 at /home/user/project1
File modified: /home/user/project1/src/main.py
File created: /home/user/project1/tests/test_new.py
File deleted: /home/user/project1/temp.txt

--- Error Output ---
No errors
```

## File Access History

### View Recent File Activity

```bash
# Show last 50 file accesses (default)
tracline monitor history PROJECT1

# Show last 100 accesses
tracline monitor history PROJECT1 -n 100

# Example output:
Recent file activity for project PROJECT1:
+---------------------+--------+-------------------------+----------+
| Time                | Action | File                    | Task     |
+=====================+========+=========================+==========+
| 2024-01-17 14:30:15 | edit   | src/main.py            | TASK-001 |
| 2024-01-17 14:25:10 | create | tests/test_auth.py     | -        |
| 2024-01-17 14:20:05 | rename | src/old.py->new.py     | TASK-002 |
| 2024-01-17 14:15:00 | delete | temp/cache.tmp         | -        |
+---------------------+--------+-------------------------+----------+
```

### Access Types

The monitor tracks these file operations:
- `create` - New file created
- `edit` - File modified
- `delete` - File removed
- `rename` - File moved/renamed

## How Monitoring Works

### Event Detection

The monitor uses the watchdog library to detect file system events:

1. **File Created**: Logs creation, no automatic task association
2. **File Modified**: Updates reference count, logs modification
3. **File Deleted**: Marks associations as inactive, logs deletion
4. **File Moved**: Updates file paths in associations, logs rename

### Reference Count Updates

When a file is modified:
- The system counts all tasks referencing the file
- Updates the `reference_count` in file associations
- Provides metrics for identifying critical files

### Database Updates

All events are logged to:
- `file_access_log` table - Complete history
- `file_associations` table - Current associations
- `project_settings` table - Monitor configuration

## Project Settings

Monitoring configuration is stored per project:

```sql
-- Example project settings
project_id: PROJECT1
monitor_enabled: true
monitor_path: /path/to/project1
monitor_extensions: ['.py', '.js', '.ts']
```

## Integration with Traceability

Monitoring enhances traceability by:

### Automatic Association Updates

When files are modified, the system:
1. Detects the change
2. Updates reference counts
3. Logs the modification
4. Links to associated tasks

### Usage Example

```bash
# Start monitoring
tracline monitor start PROJECT1 . --daemon

# Create a task and associate files
tracline add "Implement new feature" -p PROJECT1
tracline trace add-file TASK-001 src/feature.py

# Edit the file (detected automatically)
vim src/feature.py

# Check updated references
tracline trace ls-trace src/feature.py
# Shows TASK-001 with updated timestamp

# View history
tracline monitor history PROJECT1
# Shows the edit event
```

## Best Practices

### 1. Project Setup

```bash
# Initialize project with monitoring
tracline project create PROJECT1
tracline monitor start PROJECT1 /project/path --daemon

# Configure appropriate extensions
tracline monitor start PROJECT1 . -d -e .py -e .yml -e .md
```

### 2. Resource Management

- Monitor only necessary file types
- Stop monitors when not needed
- Clean up old log entries periodically

### 3. Team Collaboration

For team projects:
- Run monitors on development servers
- Share monitor configuration
- Centralize log collection

### 4. Performance Considerations

- Large directories may impact performance
- Exclude build/output directories
- Monitor specific subdirectories if needed

```bash
# Monitor only source directory
tracline monitor start PROJECT1 /project/src --daemon

# Avoid monitoring node_modules, build, etc.
```

## Troubleshooting

### Monitor Won't Start

**Issue**: "Failed to start monitor"

**Solutions**:
- Check directory exists and is readable
- Ensure no other monitor is running for the project
- Verify daemon permissions

```bash
# Check if monitor is already running
tracline monitor status

# Check directory permissions
ls -la /path/to/project
```

### Monitor Stops Unexpectedly

**Issue**: Monitor shows as "stopped" in status

**Solutions**:
- Check logs for errors
- Verify disk space
- Check system resources

```bash
# View error logs
tracline monitor logs PROJECT1

# Check disk space
df -h

# Check process limits
ulimit -n
```

### Events Not Being Logged

**Issue**: File changes not appearing in history

**Solutions**:
- Verify file extensions are monitored
- Check database connectivity
- Ensure monitor is running

```bash
# Verify monitor configuration
tracline monitor status

# Test with a monitored extension
touch test.py
tracline monitor history PROJECT1 -n 5
```

### High CPU Usage

**Issue**: Monitor process consuming excessive CPU

**Solutions**:
- Reduce monitored extensions
- Exclude large directories
- Increase event processing delay

## Advanced Configuration

### Custom Watch Patterns

While the CLI uses extension-based filtering, you can create custom monitoring scripts:

```python
from tracline.monitor import MonitorDaemon

# Custom configuration
daemon = MonitorDaemon(
    project_id="PROJECT1",
    monitor_path="/project",
    config_path="custom_config.yaml"
)

# Start with custom settings
daemon.start(as_daemon=False)
```

### Integration with CI/CD

Include monitoring in your development pipeline:

```yaml
# Example: Start monitoring in CI environment
steps:
  - name: Start TracLine Monitor
    run: |
      tracline monitor start $PROJECT_ID $GITHUB_WORKSPACE --daemon
      
  - name: Run Tests
    run: pytest
    
  - name: Check File Coverage
    run: |
      # Verify test files are tracked
      tracline monitor history $PROJECT_ID -n 50
```

### Monitoring Metrics

Extract monitoring data for analysis:

```bash
# Export history as JSON
tracline monitor history PROJECT1 -n 1000 > file_activity.json

# Analyze with Python
python analyze_activity.py file_activity.json
```

## Security Considerations

### Access Control

- Monitors run with user permissions
- Cannot access files outside user scope
- Respects file system permissions

### Sensitive Files

- Exclude sensitive directories
- Don't monitor credentials or secrets
- Use extension filters appropriately

```bash
# Exclude sensitive files
tracline monitor start PROJECT1 /project -d \
  -e .py \
  -e .js \
  # Don't include .env, .key, etc.
```

### Audit Trail

All file access is logged with:
- Timestamp
- User/process information
- Action performed
- Associated task (if any)

## See Also

- [File Traceability Guide](TRACEABILITY.md) - Manual file tracking
- [GitHub Integration](GITHUB_INTEGRATION.md) - Source control integration
- [User Guide](USER_GUIDE.md) - General TracLine usage