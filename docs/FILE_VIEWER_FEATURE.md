# File Viewer Feature Documentation

## Overview

The TracLine file viewer feature allows users to view the contents of files associated with tasks directly from the web interface. This feature supports both absolute and relative file paths through project root configuration.

## Components

### 1. Web API Endpoint

**Endpoint**: `GET /api/files/view`

**Parameters**:
- `file_path` (required): Path to the file to view
- `project_id` (optional): Project ID for relative path resolution

**Security Features**:
- Path traversal prevention
- File size limit (10MB)
- Text file validation
- Access control through project root boundaries

### 2. Project Root Configuration

The project root feature allows projects to define a base directory for relative file paths.

**CLI Commands**:
```bash
# Set project root
tracline projectroot set PROJECT1 /path/to/project

# Get project root
tracline projectroot get PROJECT1

# Clear project root
tracline projectroot clear PROJECT1 --confirm

# List all project roots
tracline projectroot list
```

### 3. UI Components

#### File Viewer Modal
- Displays file content with syntax highlighting
- Shows file metadata (path, size, lines, type)
- Error handling for inaccessible files
- Loading states

#### Clickable File Links
- Task details: Files in "Related Files" section are clickable
- Traceability Matrix: File paths in File-Task Relationship modal are clickable
- Automatic project root resolution for relative paths

### 4. Database Schema

Added `project_root` column to `project_settings` table:
```sql
ALTER TABLE project_settings ADD COLUMN project_root TEXT DEFAULT '';
```

## Usage

### Setting Up Project Root

1. Configure project root for relative paths:
   ```bash
   tracline projectroot set MY-PROJECT /home/user/projects/myproject
   ```

2. Add files using relative paths:
   ```bash
   tracline trace add-file TASK-001 src/main.py
   ```

3. View files in web interface by clicking on file paths

### File Viewing

1. Click on any file path in:
   - Task details "Related Files" section
   - Traceability Matrix File-Task Relationship modal

2. File viewer modal opens showing:
   - File content with line numbers
   - File metadata
   - Scrollable content area

## Benefits

1. **Improved Workflow**: View file contents without leaving TracLine
2. **Context Awareness**: See files in the context of their associated tasks
3. **Portability**: Relative paths work across different environments
4. **Security**: Built-in security checks prevent unauthorized file access

## Implementation Details

### Path Resolution Logic

```python
if not os.path.isabs(file_path):
    if project_id and project_root:
        resolved_path = os.path.join(project_root, file_path)
    else:
        return error("Relative path requires project root")
else:
    resolved_path = file_path
```

### Security Checks

1. **Path Normalization**: Prevents directory traversal attacks
2. **File Size Limit**: 10MB maximum to prevent memory issues
3. **Text File Validation**: Only text files are viewable
4. **Project Root Boundary**: Files must be within project root for relative paths

## Future Enhancements

1. **Syntax Highlighting**: Add language-specific syntax highlighting
2. **File Editing**: Allow editing files directly from the viewer
3. **Binary File Support**: Display images and other binary files
4. **Search Functionality**: Search within viewed files
5. **Version History**: Show git history for files