# Claude Code Parallel Development User Guide

This guide explains how to use TracLine with Claude Code for parallel AI-driven development, enabling multiple AI developers to work simultaneously on different parts of your project.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Process Overview](#development-process-overview)
3. [The Power of Multi-Agent Systems](#the-power-of-multi-agent-systems)
4. [Initial Setup](#initial-setup)
5. [Preparing Requirements and Design Documents](#preparing-requirements-and-design-documents)
6. [Configuring TracLine for AI Development](#configuring-tracline-for-ai-development)
7. [Setting Up AI Developers](#setting-up-ai-developers)
8. [Parallel Development Workflow](#parallel-development-workflow)
9. [Natural Language Commands](#natural-language-commands)
10. [Monitoring Progress](#monitoring-progress)
11. [Best Practices](#best-practices)
12. [Troubleshooting](#troubleshooting)

## Prerequisites

- **Claude Code**: Installed and configured on your system
- **TracLine**: Installed (global installation recommended)
- **Python**: 3.8 or higher
- **Database**: PostgreSQL (recommended) or SQLite
- **Git**: For version control

## Development Process Overview

The AI-driven parallel development process follows these steps:

1. **Requirements Definition**: Create requirements documents with requirement IDs for traceability
2. **Design**: Create detailed design documents linked to requirement IDs
3. **Task Decomposition**: Break down designs into manageable tasks
4. **AI Assignment**: Assign tasks to multiple AI developers
5. **Parallel Execution**: Run multiple Claude Code instances simultaneously
6. **Progress Monitoring**: Track progress via CLI and web interface

## The Power of Multi-Agent Systems

Based on Anthropic's research on multi-agent systems ([Building a Multi-Agent Research System](https://www.anthropic.com/engineering/built-multi-agent-research-system)), running multiple development agents in parallel provides significant advantages over single-agent approaches.

### Key Performance Insights

**Performance Improvements:**
- Leader + sub-agents parallel processing achieves **90.2% performance improvement**
- Token usage increases 15x compared to single agents, but remains economically viable for high-value tasks
- Prompt engineering prevents runaway behaviors like "generate 50 sub-agents"

**Critical Observations:**
- Just like human society, AI collectives demonstrate dramatically superior intelligence compared to individuals
- The uncomfortable truth: "More tokens solve more problems" - computational resources directly correlate with capability
- Debugging becomes nightmarish - tracing non-deterministic systems opens new dimensions of complexity

### Business Value and Practical Benefits

**Market Applications:**
- Complex research tasks compressed from days to minutes
- High-value task optimization (business opportunity discovery, technical bug resolution)
- MCP (Model Context Protocol) enables seamless external tool integration

### Why Multi-Agent Systems Excel

**In Simple Terms:**
- Multiple specialized AIs working in parallel vastly outperform a single AI doing everything
- AI teams mirror human research teams: leaders delegate, specialists execute in parallel
- Battle-tested insights openly shared (prompts are open-sourced)

The core principle: **Running multiple development agents in parallel is fundamentally superior to sequential single-agent approaches**. This guide implements these research findings, enabling you to leverage multiple Claude Code instances as specialized AI developers working simultaneously on your project.

## Initial Setup

### 1. Install TracLine

```bash
# Clone repository
git clone git@github.com:techs-targe/TracLine.git
cd TracLine

# Global installation (recommended)
pip install .

# Initialize database
tracline init
```

### 2. Configure CLAUDE.md

```bash
# Copy template
cp CLAUDE.md.sample.globalinstall CLAUDE.md

# Edit CLAUDE.md to match your project structure
nano CLAUDE.md
```

Key configurations in CLAUDE.md:
- Project structure paths
- Document locations
- Task workflow preferences

## Preparing Requirements and Design Documents

### Requirements Document Structure

Create `./docs/requirements/requirements.md`:

```markdown
# Project Requirements

## REQ-001: User Authentication
- Users must be able to register with email
- Support OAuth integration
- Password reset functionality

## REQ-002: Data Management
- CRUD operations for user data
- Data validation
- Export functionality
```

### Design Document Structure

Create `./docs/design/design.md`:

```markdown
# Detailed Design

## DES-001: Authentication Module (REQ-001)
### DES-001.1: Registration Component
- Input validation
- Email verification
- Database schema

### DES-001.2: OAuth Integration
- Provider configuration
- Token management

## DES-002: Data Module (REQ-002)
### DES-002.1: CRUD Operations
- REST API endpoints
- Database models
```

## Configuring TracLine for AI Development

### 1. Create Project

```bash
tracline project create "PROJECT-001" "AI Development Project"
```

### 2. Configure Project Settings

```bash
# Enable strict mode for quality assurance
tracline project settings PROJECT-001 --strict-file-ref
tracline project settings PROJECT-001 --strict-log-entry
```

### 3. Create AI Developer Members

```bash
# Create AI developers
tracline member add "AI-BACKEND" "AI Backend Developer" --role ENGINEER
tracline member add "AI-FRONTEND" "AI Frontend Developer" --role ENGINEER
tracline member add "AI-DATABASE" "AI Database Developer" --role ENGINEER
tracline member add "AI-TESTING" "AI Testing Developer" --role QA

# Add members to project
tracline project add-members PROJECT-001 AI-BACKEND AI-FRONTEND AI-DATABASE AI-TESTING
```

## Setting Up AI Developers

### 1. Create Launch Scripts

For each AI developer, copy and customize the launch template:

```bash
cd scripts/claude-code

# Copy template for each AI developer
cp launch-claude-template.sh launch-claude-backend.sh
cp launch-claude-template.sh launch-claude-frontend.sh
cp launch-claude-template.sh launch-claude-database.sh
cp launch-claude-template.sh launch-claude-testing.sh
```

### 2. Configure Each Script

Edit each script to set unique identities:

**launch-claude-backend.sh:**
```bash
export TASK_ASSIGNEE="AI-BACKEND"
export MEMBER_ID="AI-BACKEND"
export MEMBER_ROLE="ENGINEER"
export TRACLINE_PROJECT_ID="PROJECT-001"
```

**launch-claude-frontend.sh:**
```bash
export TASK_ASSIGNEE="AI-FRONTEND"
export MEMBER_ID="AI-FRONTEND"
export MEMBER_ROLE="ENGINEER"
export TRACLINE_PROJECT_ID="PROJECT-001"
```

### 3. Make Scripts Executable

```bash
chmod +x launch-claude-*.sh
```

## Parallel Development Workflow

### 1. Task Creation from Design Documents

Launch Claude Code and instruct it to create tasks:

```bash
# In Claude Code session
> Please analyze the design document and create TracLine tasks for each design section.
> Use the design IDs (DES-XXX) as task IDs and link them to requirements.
```

Example natural language instruction:
```
Create TracLine tasks from ./docs/design/design.md:
- One task per DES-XXX.X section
- Set appropriate priorities
- Assign to relevant AI developers based on component type
```

### 2. Link Requirements to Tasks

```bash
# In Claude Code session
> Link all authentication tasks to REQ-001
> Link all data management tasks to REQ-002
```

### 3. Launch Parallel AI Developers

Open multiple terminal windows and launch each AI developer:

**Terminal 1 - Backend Developer:**
```bash
cd /path/to/project
./scripts/claude-code/launch-claude-backend.sh
```

**Terminal 2 - Frontend Developer:**
```bash
cd /path/to/project
./scripts/claude-code/launch-claude-frontend.sh
```

**Terminal 3 - Database Developer:**
```bash
cd /path/to/project
./scripts/claude-code/launch-claude-database.sh
```

### 4. Start Development

In each Claude Code session, simply type:
```
next
```

The AI will:
1. Fetch the next assigned task
2. Review linked requirements and design documents
3. Implement the solution
4. Create/update files
5. Log progress
6. Attach created files to the task

Continue with:
```
done
next
```

## Natural Language Commands

Claude Code understands these natural language instructions:

### Project Setup
- "Create TracLine project PROJECT-001 named 'E-commerce Platform'"
- "Add AI-BACKEND as a backend developer to the project"
- "Enable strict mode for quality assurance"

### Task Management
- "Create tasks from the design document"
- "Show me all pending tasks"
- "Assign all database tasks to AI-DATABASE"
- "Link task DES-001.1 to requirement REQ-001"

### Development Flow
- "Start working on the next task" → `next`
- "I've completed this task" → `done`
- "Show current task details" → `show CURRENT-TASK-ID`
- "Add implementation notes" → `log TASK-ID "message"`

### Progress Tracking
- "Show project progress"
- "List all tasks assigned to me"
- "Show completed tasks today"

## Monitoring Progress

### 1. Web Interface

Start the web server:
```bash
cd TracLine/web
python run_app.py --port 8000
```

Access at http://localhost:8000 to view:
- Task board with swim lanes
- Team member assignments
- Progress charts
- Traceability matrix

### 2. Command Line Monitoring

```bash
# Project overview
tracline project show PROJECT-001

# Task summary by assignee
tracline list --assignee AI-BACKEND --status DOING
tracline list --assignee AI-FRONTEND --status TESTING

# Progress report
tracline list --project PROJECT-001 --summary
```

### 3. Real-time Monitoring

Use file monitoring to track AI-generated files:
```bash
tracline monitor start --project PROJECT-001 --interval 30
```

## Best Practices

### 1. Task Decomposition
- Keep tasks focused on single design elements
- Use consistent ID patterns (DES-XXX.Y)
- Maintain 1:1 or N:1 task-to-requirement mapping

### 2. AI Developer Specialization
- Assign AI developers to specific domains
- Use descriptive names (AI-BACKEND, AI-AUTH, etc.)
- Consider creating specialized CLAUDE.md for each role

### 3. Quality Assurance
- Enable strict mode for production projects
- Review AI-generated code regularly
- Use AI-TESTING for automated test creation

### 4. Workspace Management
- Use isolated workspaces for parallel development
- Configure `.gitignore` for AI workspaces
- Implement code review process before merging

### 5. Documentation
- Keep requirements and design documents updated
- Use TracLine's file attachment for deliverables
- Maintain traceability throughout development

## Troubleshooting

### Common Issues

**1. Claude Code Not Finding Tasks**
```bash
# Verify assignment
tracline list --assignee AI-BACKEND

# Check project membership
tracline project members PROJECT-001
```

**2. Task State Issues**
```bash
# Reset task to TODO
tracline update TASK-ID --status TODO

# Force completion
tracline complete TASK-ID
```

**3. Multiple AI Conflicts**
- Use isolated workspaces
- Implement file locking via task assignment
- Coordinate through task dependencies

**4. Configuration Issues**
```bash
# Verify TracLine installation
tracline config --show

# Check member exists
tracline member show AI-BACKEND

# Validate project
tracline project show PROJECT-001
```

### Debug Mode

Enable debug output in launch scripts:
```bash
export TRACLINE_DEBUG="true"
```

### Log Files

Check TracLine logs:
```bash
# View recent logs
tracline list --logs --limit 50

# Task-specific logs
tracline show TASK-ID --logs
```

## Advanced Configuration

### Custom AI Behaviors

Modify CLAUDE.md for specific behaviors:
```markdown
## Development Guidelines
- Always create unit tests for new functions
- Use TypeScript for all frontend code
- Follow PEP 8 for Python code
- Add JSDoc comments for all public APIs
```

### Task Templates

Create task templates for consistent structure:
```bash
# In Claude Code
> Create authentication tasks using this template:
> - Title: "Implement [Component]"
> - Description: "Implement [Component] as per DES-XXX"
> - Priority: 3 for features, 5 for security-related
> - Add labels: "backend", "authentication"
```

### Continuous Integration

Integrate with CI/CD:
```yaml
# .github/workflows/ai-development.yml
on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours

jobs:
  ai-development:
    runs-on: ubuntu-latest
    steps:
      - name: Run AI Developer
        run: |
          ./scripts/claude-code/launch-claude-backend.sh --non-interactive
          tracline next --limit 5
```

## Conclusion

TracLine with Claude Code enables efficient parallel AI development by:
- Providing structured task management
- Enabling natural language interactions
- Supporting multiple AI developers simultaneously
- Maintaining full traceability
- Integrating with existing development workflows

Start with a small pilot project to familiarize your team with the workflow, then scale up to larger projects as you refine your process.