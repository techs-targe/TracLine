# TracLine Web Features

This document describes the web interface features for TracLine, including project settings management and enhanced traceability matrix.

## Project Settings

The project settings feature allows you to configure strict mode requirements for your projects through the web interface.

### Strict Mode Settings

Navigate to the **Settings** tab in the web interface to configure the following strict mode options:

1. **Strict Document Read**: When enabled, requires users to read all associated documents before marking a task as DONE. Users will see a warning when using the `next` command and must enter a confirmation code when using the `done` command.

2. **Strict File Reference**: When enabled, requires tasks to have at least one file association before they can be marked as DONE.

3. **Strict Log Entry**: When enabled, requires tasks to have at least one log entry before they can be marked as DONE.

### API Endpoints

- `GET /api/projects/{project_id}/settings` - Get project settings
- `PUT /api/projects/{project_id}/settings` - Update project settings
- `GET /api/projects/{project_id}/settings/strict-mode` - Get only strict mode settings

## Enhanced Traceability Matrix

The enhanced traceability matrix provides advanced filtering and analysis capabilities for tracking file-task relationships.

### Features

1. **Filtering Options**:
   - Filter by file extension (e.g., .py, .js, .yaml)
   - Filter by file name containing specific text
   - Filter by task name containing specific text
   - Toggle reference count display

2. **Statistics Display**:
   - Total number of tasks
   - Total number of files
   - Total file-task associations
   - Average files per task
   - Most referenced files (top 10)

3. **Reference Counts**:
   - Shows how many times each file is referenced across all tasks
   - Visual indicators with color coding:
     - Green (1-2 references): Low dependency
     - Orange (3-5 references): Medium dependency
     - Red (6+ references): High dependency - critical files
   - Reference count displayed as a badge under each filename

4. **Interactive Matrix Cells**:
   - Click on any ● (relation marker) to see detailed information
   - Shows all tasks that reference the selected file
   - Highlights the current task in the list
   - Each task in the popup is clickable for more details

### API Endpoints

- `GET /api/traceability-matrix/enhanced` - Get enhanced matrix with filtering
  - Query parameters:
    - `project_id`: Filter by project
    - `file_extension`: Filter by file extension
    - `file_name_contains`: Filter files containing text
    - `task_name_contains`: Filter tasks containing text
    - `include_reference_counts`: Include reference counts (default: true)

- `GET /api/traceability-matrix/file-extensions` - Get all unique file extensions
  - Query parameters:
    - `project_id`: Filter by project

- `GET /api/traceability-matrix/file-stats` - Get detailed file statistics
  - Query parameters:
    - `project_id`: Filter by project

## Testing

To test the web features:

```bash
# Start the web server
python web/app.py

# In another terminal, run the test script
python web/test_web_features.py

# Create sample data for matrix visualization
python web/create_matrix_test_data.py
```

The test script will verify:
- Project settings can be retrieved and updated
- Strict mode settings are properly saved
- Enhanced traceability matrix works with filters
- File statistics and extensions are correctly calculated

## Usage Example

1. **Configure Strict Mode**:
   - Navigate to Settings tab
   - Select your project
   - Enable desired strict mode options
   - Click "Save Settings"

2. **Use Enhanced Traceability Matrix**:
   - Navigate to Traceability Matrix tab
   - Apply filters as needed:
     - Select file extension to focus on specific file types
     - Enter partial file/task names to filter
   - View reference counts to identify critical files
   - Check statistics for project overview

## Integration with CLI

The strict mode settings configured in the web interface are immediately effective in the CLI:

- When `strict_doc_read` is enabled:
  - `tracline next <task_id>` will show document warnings
  - `tracline done <task_id>` will require confirmation code

- When `strict_file_ref` is enabled:
  - Tasks without file associations cannot be marked as DONE

- When `strict_log_entry` is enabled:
  - Tasks without log entries cannot be marked as DONE

Environment variables can override these settings:
- `TRACLINE_STRICT_DOC_READ=true/false`
- `TRACLINE_STRICT_FILE_REF=true/false`
- `TRACLINE_STRICT_LOG_ENTRY=true/false`