# Project-Specific Task Management in TracLine

TracLine now fully supports project-specific task management, allowing you to organize your tasks by project and easily switch between different projects. This document explains how to use these new features.

## Key Concepts

- **Current Project**: TracLine maintains a "current project" setting that affects task operations
- **TRACLINE_PROJECT**: Environment variable to set the current project
- **Project-Specific Tasks**: Tasks can be associated with specific projects
- **Project Management Commands**: Commands to view, list, and switch between projects

## Setting and Viewing the Current Project

### View Current Project

```bash
# Show current project details
tracline project current

# Direct access without subcommand
tracline project-current
```

### Change Current Project

```bash
# Change to a different project
tracline project change my-project-id
```

This sets the current project for the session and updates your configuration file. To make this change persistent across sessions, set the environment variable:

```bash
export TRACLINE_PROJECT=my-project-id
```

### Listing Available Projects

```bash
# List all projects
tracline project list

# Filter by status or owner
tracline project list --status ACTIVE
tracline project list --owner john
```

## Working with Project-Specific Tasks

### Creating Tasks in a Project

When you create a task, it will automatically be associated with the current project:

```bash
# Creates task in the current project
tracline add TASK-123 "Implement login feature"

# Explicitly specify project
tracline add TASK-123 "Implement login feature" --project web-app
```

### Listing Tasks by Project

```bash
# List tasks for current project
tracline list

# List tasks for specific project
tracline list --project web-app
```

### Getting Next Task for a Project

```bash
# Get next task for current project
tracline next

# Get next task for specific project
tracline next --project web-app
```

## Project Management

### Creating a New Project

```bash
tracline project create project-id "Project Name" --description "Project description"
```

After creating a project, you'll be asked if you want to set it as the current project.

### Viewing Project Details

```bash
tracline project show project-id
```

### Managing Project Members

```bash
# Add members to a project
tracline project add-members project-id member1 member2

# Remove members
tracline project remove-members project-id member1

# List project members
tracline project members project-id
```

## Best Practices

1. **Set Current Project First**: Before starting work, set your current project with `tracline project change`

2. **Create Project-Specific Tasks**: Always associate tasks with projects for better organization

3. **Use Environment Variables**: In your `.bashrc` or `.zshrc`, set:
   ```bash
   export TRACLINE_PROJECT=default-project
   export TRACLINE_ASSIGNEE=your-username
   ```

4. **Project-Based Workflows**: Create different terminal sessions for different projects

## Tips for Multi-Project Teams

- Use consistent project IDs across the team
- Create a standard project structure with similar task types across projects
- Consider using project-specific tags to further organize tasks
- Set up periodic project reviews with `tracline project current` to see project status

## Configuration

In your `tracline.yaml` file, you can set a default project:

```yaml
defaults:
  project: default-project
  assignee: your-username
  priority: 3
```

This default will be used if no project is specified in commands or environment variables.