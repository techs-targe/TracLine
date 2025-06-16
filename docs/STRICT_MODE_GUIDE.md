# TracLine Strict Mode Guide

TracLine now supports strict mode enforcement to ensure quality and compliance in task management workflows. This guide explains how to configure and use the three strict mode features.

## Overview

Strict mode provides three enforcement mechanisms:

1. **Document Read Enforcement** - Requires confirmation that associated documents have been read when starting a task
2. **File Reference Enforcement** - Requires at least one file to be associated with a task before marking it done
3. **Log Entry Enforcement** - Requires at least one log entry before marking a task done

## Configuration

### Project-Level Settings

Configure strict mode per project using the `project settings` command:

```bash
# Enable all strict modes
tracline project settings PROJECT-ID --strict-doc-read --strict-file-ref --strict-log-entry

# Enable specific modes
tracline project settings PROJECT-ID --strict-file-ref

# Disable a mode
tracline project settings PROJECT-ID --no-strict-doc-read

# View current settings
tracline project settings PROJECT-ID --show
```

### Environment Variables

You can override database settings with environment variables:

#### Project-Specific Variables
```bash
# Format: TRACLINE_STRICT_<MODE>_<PROJECT_ID>
export TRACLINE_STRICT_DOC_READ_MY_PROJECT=true
export TRACLINE_STRICT_FILE_REF_MY_PROJECT=true
export TRACLINE_STRICT_LOG_ENTRY_MY_PROJECT=true
```

#### Global Variables
```bash
# Apply to all projects without specific settings
export TRACLINE_STRICT_DOC_READ=true
export TRACLINE_STRICT_FILE_REF=true
export TRACLINE_STRICT_LOG_ENTRY=true
```

**Note**: Project IDs in environment variables should be uppercase with hyphens replaced by underscores.

## Usage

### Document Read Enforcement

When enabled, the `next` command will:
1. Check if the task has associated documents (md, txt, pdf, doc files)
2. Display the list of documents
3. Generate a random 3-character confirmation code
4. Require the user to enter the code to confirm they've read the documents

Example:
```bash
$ tracline next --project DOCS-PROJECT

 Field       Value                           
 ID          DOC-001                        
 Title       Review API Documentation        
 Status      TODO                           

⚠️  Strict Document Read Mode Enabled
This task has associated documents that must be read:

 Document              
 api-guide.md         
 api-reference.pdf    

Please confirm you have read all documents by typing: X7B
Confirmation code: X7B
✓ Document read confirmation successful
```

### File Reference Enforcement

When enabled, the `done` command will:
1. Track the number of files when work begins (TODO → READY transition)
2. Ensure at least one NEW file is added during work
3. Prevent marking the task as done if no new files were added
4. Suggest commands to attach files

This enhanced mode prevents situations where design documents are already attached during planning, but no actual work output (code, tests, etc.) is added.

Example:
```bash
# Task already has design.md attached when work starts
$ tracline done TASK-001

❌ New File Reference Required
This task had 1 files when work started.
Current file count: 1
You must add at least one new file during the work before marking as done.
Use 'tracline attach <file>' or 'tracline trace add-file <file> <task_id>' to associate files.

# After adding implementation
$ tracline attach src/feature.py
$ tracline done TASK-001
✓ Task TASK-001 completed!
```

### Log Entry Enforcement

When enabled, the `done` command will:
1. Check if the task has at least one work log entry
2. Prevent marking the task as done if no logs exist
3. Suggest the log command

Example:
```bash
$ tracline done TASK-001

❌ Strict Log Entry Mode Enabled
This task must have at least one log entry before it can be marked as done.
Use 'tracline log <message>' to add a log entry.
```

## Database Schema

The strict mode settings are stored in the `project_settings` table:

```sql
-- PostgreSQL
CREATE TABLE project_settings (
    project_id VARCHAR(100) PRIMARY KEY,
    strict_doc_read BOOLEAN DEFAULT false,
    strict_file_ref BOOLEAN DEFAULT false,
    strict_log_entry BOOLEAN DEFAULT false,
    -- ... other settings ...
);

-- For enhanced file reference tracking
ALTER TABLE tasks ADD COLUMN work_started_file_count INTEGER;

-- SQLite
CREATE TABLE project_settings (
    project_id TEXT PRIMARY KEY,
    strict_doc_read BOOLEAN DEFAULT 0,
    strict_file_ref BOOLEAN DEFAULT 0,
    strict_log_entry BOOLEAN DEFAULT 0,
    -- ... other settings ...
);

-- For enhanced file reference tracking
ALTER TABLE tasks ADD COLUMN work_started_file_count INTEGER;
```

The `work_started_file_count` field tracks how many files were attached when work began (TODO → READY transition), enabling the enhanced file reference check.

## Migration

If you're upgrading from a previous version, run the schema update scripts:

```bash
# For basic strict mode features
python scripts/update_strict_mode_schema.py

# For enhanced file reference tracking (v2.1+)
python scripts/add_work_started_file_count.py
```

Or manually add the columns:
```sql
ALTER TABLE project_settings ADD COLUMN strict_doc_read BOOLEAN DEFAULT false;
ALTER TABLE project_settings ADD COLUMN strict_file_ref BOOLEAN DEFAULT false;
ALTER TABLE project_settings ADD COLUMN strict_log_entry BOOLEAN DEFAULT false;
```

## Best Practices

1. **Start with one mode** - Begin with file reference enforcement to ensure traceability
2. **Use environment variables for CI/CD** - Set global strict modes in your build environment
3. **Document requirements clearly** - When using document read enforcement, ensure documents are well-organized
4. **Regular reviews** - Periodically review which projects need strict mode enforcement

## Troubleshooting

### "Column does not exist" errors
Run the schema update script or recreate the project_settings table.

### Environment variables not working
- Ensure project IDs are uppercase with underscores instead of hyphens
- Check that boolean values are: true, 1, yes, or on (case-insensitive)

### Confirmation code not accepted
The code is case-sensitive and must be entered exactly as shown.

## Examples

### Project Setup with Strict Mode
```bash
# Create project
tracline project create QUALITY-PROJECT "High Quality Project"

# Enable all strict modes
tracline project settings QUALITY-PROJECT \
  --strict-doc-read \
  --strict-file-ref \
  --strict-log-entry

# Create task with documentation
tracline add QUAL-001 "Implement new feature" --project QUALITY-PROJECT
tracline trace add-file design-doc.md QUAL-001

# Work on task (will require doc confirmation)
tracline next --project QUALITY-PROJECT

# Add implementation file
tracline trace add-file src/feature.py QUAL-001

# Add work log
tracline log QUAL-001 "Implemented core functionality"

# Now can mark as done
tracline done QUAL-001
```

### CI/CD Integration
```bash
# In your CI/CD pipeline
export TRACLINE_STRICT_FILE_REF=true
export TRACLINE_STRICT_LOG_ENTRY=true

# All tasks will require files and logs before completion
```