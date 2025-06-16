# File Traceability Guide

TracLine provides powerful file traceability features that allow you to track relationships between files and tasks. This guide covers how to use these features effectively.

## Overview

File traceability in TracLine helps you:
- Track which tasks reference specific source files
- Monitor file changes and automatically update associations
- Generate traceability matrices for compliance and documentation
- Understand code dependencies and impact analysis

## File-Task Associations

### Manual Association

Associate files with tasks using the CLI:

```bash
# Add a file to a task
tracline trace add-file TASK-001 src/main.py

# Remove a file from a task
tracline trace remove-file TASK-001 src/main.py
```

### Automatic Association

When file system monitoring is enabled, TracLine automatically tracks file modifications and updates associations.

## Searching File References

### Using ls-trace Command

The `ls-trace` command is your primary tool for finding tasks that reference specific files:

```bash
# Basic usage - find all tasks referencing a file
tracline trace ls-trace src/hello.c

# Output formats
tracline trace ls-trace src/main.py --format table  # Default table view
tracline trace ls-trace src/main.py --format list   # Simple list
tracline trace ls-trace src/main.py --format json   # JSON output

# Filter by project
tracline trace ls-trace src/api.js -p PROJECT1

# Filter by task status
tracline trace ls-trace test.py --status TODO
tracline trace ls-trace test.py --status DOING

# Combine filters
tracline trace ls-trace src/main.py -p PROJECT1 --status READY
```

### Example Output

```
Tasks referencing 'src/main.py':
Found 3 task(s)

+----------+---------------------------+--------+----------+----------+---------+-------------+
| ID       | Title                     | Status | Assignee | Priority | Project | Associated  |
+==========+===========================+========+==========+==========+=========+=============+
| TASK-001 | Implement authentication  | DOING  | john     | 1        | PROJ1   | 2024-01-15  |
| TASK-005 | Fix login bug            | TODO   | -        | 2        | PROJ1   | 2024-01-16  |
| TASK-012 | Add unit tests           | READY  | alice    | 3        | PROJ1   | 2024-01-17  |
+----------+---------------------------+--------+----------+----------+---------+-------------+
```

## File Reference Statistics

### View Top Referenced Files

```bash
# Show top 10 most referenced files
tracline trace stats

# Show top 20 files for a specific project
tracline trace stats -p PROJECT1 -t 20
```

### Example Statistics Output

```
Top 10 referenced files:
Project: PROJECT1

+---+------------------------+-------+-----------+----------+
| # | File                   | Tasks | Assignees | Projects |
+===+========================+=======+===========+==========+
| 1 | src/main.py           | 15    | 5         | 2        |
| 2 | src/api/auth.js       | 12    | 3         | 1        |
| 3 | tests/test_auth.py    | 8     | 2         | 1        |
| 4 | docs/API.md           | 7     | 4         | 2        |
| 5 | src/database.py       | 6     | 2         | 1        |
+---+------------------------+-------+-----------+----------+
```

## Web API Usage

### Get Tasks for a File

```bash
# Get tasks referencing a specific file
curl "http://localhost:8000/api/trace/src/main.py"

# With filters
curl "http://localhost:8000/api/trace/src/main.py?project_id=PROJECT1&status=TODO"
```

### Response Format

```json
{
  "file_path": "src/main.py",
  "stats": {
    "task_count": 3,
    "assignee_count": 2,
    "project_count": 1
  },
  "tasks": [
    {
      "task_id": "TASK-001",
      "title": "Implement authentication",
      "status": "DOING",
      "assignee": "john",
      "priority": 1,
      "project_id": "PROJECT1",
      "created_at": "2024-01-15T10:00:00",
      "updated_at": "2024-01-16T14:30:00",
      "associated_at": "2024-01-15T11:00:00"
    }
  ]
}
```

### Get File Statistics

```bash
# Get top referenced files
curl "http://localhost:8000/api/trace/stats?top=10"

# For specific project
curl "http://localhost:8000/api/trace/stats?project_id=PROJECT1&top=5"
```

## Traceability Matrix

The traceability matrix provides a visual representation of file-task relationships:

```bash
# Access via web interface
http://localhost:8000

# Navigate to the Matrix tab
```

The matrix shows:
- Rows: Tasks
- Columns: Files
- Cells: Checkmarks indicating associations

## Reference Counting

TracLine automatically maintains reference counts for files:

- **Initial Count**: Set when a file is first associated with a task
- **Auto-update**: Updated when file monitoring detects changes
- **Manual Update**: Updated when associations are added/removed

Reference counts help identify:
- Critical files (high reference count)
- Orphaned files (zero references)
- Task coverage for files

## Best Practices

### 1. Regular Association Updates

```bash
# Review file associations periodically
tracline trace stats -p PROJECT1

# Clean up obsolete associations
tracline trace remove-file TASK-001 deleted_file.py
```

### 2. Use Monitoring for Accuracy

Enable file system monitoring to keep associations current:

```bash
# Start monitoring for automatic tracking
tracline monitor start PROJECT1 /path/to/project --daemon
```

### 3. Project Organization

- Associate files at the start of task work
- Update associations when scope changes
- Review associations before task completion

### 4. Integration with Development Workflow

```bash
# Before starting work on a task
tracline show TASK-001  # Review current associations
tracline trace add-file TASK-001 new_feature.py

# After completing work
tracline trace ls-trace new_feature.py  # Verify associations
tracline done TASK-001
```

## Troubleshooting

### File Not Found Warning

If you see "⚠️ Warning: File does not exist", it means:
- The file has been deleted or moved
- The path is incorrect (relative vs absolute)
- The file hasn't been created yet

### No Tasks Found

If `ls-trace` returns no results:
- Check the file path (use absolute paths for consistency)
- Verify the project filter
- Ensure tasks have been properly associated

### Database Synchronization

For teams, ensure all members are working with the same database:
- Use PostgreSQL for multi-user environments
- Configure proper database permissions
- Regular backups of association data

## Advanced Usage

### Scripting and Automation

```bash
# Export traceability data
tracline trace ls-trace src/main.py --format json > trace_report.json

# Find all files for a task
tracline ls-files TASK-001

# Bulk association from file list
for file in $(find src -name "*.py"); do
  tracline trace add-file TASK-001 "$file"
done
```

### Integration with CI/CD

Include traceability checks in your pipeline:

```yaml
# Example GitHub Actions workflow
- name: Check File Coverage
  run: |
    # Ensure all source files are tracked
    for file in $(find src -name "*.py"); do
      if ! tracline trace ls-trace "$file" | grep -q "Found"; then
        echo "Warning: $file has no task associations"
      fi
    done
```

## See Also

- [File System Monitoring](MONITORING.md) - Automatic file tracking
- [User Guide](USER_GUIDE.md) - General TracLine usage
- [API Documentation](../README.md#api-endpoints) - REST API reference