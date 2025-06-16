# TracLine Installation Guide

## Quick Install (Recommended)

### Ubuntu/Debian
```bash
# Basic installation
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu.sh | bash

# Installation with sample data (auto-loaded on first run)
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu.sh | bash -s -- --sample-data
```

> **Note:** If you encounter issues with the installer, GitHub may be serving a cached version. Wait 5 minutes and try again, or clone the repository and run the installer locally:
> ```bash
> git clone https://github.com/techs-targe/TracLine.git
> cd TracLine
> bash scripts/install-ubuntu.sh  # or add --sample-data
> ```

**⚠️ Important: What this installer will do to your system:**
- Install TracLine globally in `~/.local/bin` using pipx (isolated from system Python)
- Run PostgreSQL in a Docker container on **port 5432**
- Install Docker if not present (requires sudo)
- Add your user to the docker group
- Create TracLine data directory at `~/.tracline`
- Install convenience commands: `tracline-start` and `tracline-stop`

**Note:** If you already have PostgreSQL running on port 5432, please use the manual installation method below to configure a different port.

### macOS
```bash
# Coming soon - use manual install for now
```

### Windows
Use [WSL2](https://docs.microsoft.com/windows/wsl/install) with Ubuntu, then run the Ubuntu installer above.

## What Gets Installed

The installer will:
- ✅ Install Python packages via pipx (PEP 668 compliant)
- ✅ Install and configure Docker
- ✅ Create convenient commands (`tracline-start`, `tracline-stop`)
- ✅ Set up PostgreSQL database
- ✅ Configure everything automatically

## Post-Installation

After installation completes:

1. **Update PATH** (REQUIRED):
   ```bash
   source ~/.bashrc  # or open a new terminal
   ```

2. **Docker group access**:
   ```bash
   newgrp docker  # or logout and login
   ```

3. **Start TracLine**:
   ```bash
   # Start normally (preserves existing data)
   tracline-start
   
   # Start with sample data (only if database doesn't exist)
   tracline-start --sample-data
   
   # Force clean installation (WARNING: deletes all data)
   tracline-start --force-clean
   ```

4. **Access**: http://localhost:8000

### Important: Database Preservation

- **First run**: Creates a new database (use `--sample-data` for demo data)
- **Subsequent runs**: Preserves your existing database and data
- **Force clean**: Use `--force-clean` ONLY when you want to delete everything and start fresh

## SQLite Installation (No Docker Required)

For a simpler setup without Docker:

```bash
# Basic SQLite installation
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu-sqlite.sh | bash

# SQLite installation with sample data
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu-sqlite.sh | bash -s -- --sample-data
```

> **v2.0.1 Update:** Fixed critical SQLite initialization issues. If you experienced "no such table" errors or UNIQUE constraint failures, please reinstall using the commands above.

> **Note:** If the installer fails, try cloning and running locally:
> ```bash
> git clone https://github.com/techs-targe/TracLine.git
> cd TracLine
> bash scripts/install-ubuntu-sqlite.sh  # or add --sample-data
> ```

This provides:
- SQLite database (no PostgreSQL/Docker needed)
- `tracline-start` - Start full application
- `tracline-web` - Start just the web server
- All other TracLine features

## Running Just the Web Server

After installation, you can run only the web interface:

### With PostgreSQL Installation
```bash
# Ensure PostgreSQL is running
docker-compose up -d postgres

# Run just the web server
cd ~/TracLine/web
~/.local/share/pipx/venvs/tracline/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```

### With SQLite Installation
```bash
# Simply run the web command
tracline-web
```

This is useful for:
- Development environments
- When you manage the database separately
- Testing the web interface only

## Uninstall

### Universal Uninstaller (Works for Both PostgreSQL and SQLite)
```bash
# Basic uninstall (removes app but keeps data)
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall.sh | bash

# Complete uninstall (removes app and all data)
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall.sh | bash -s -- --remove-data
```

The universal uninstaller:
- Automatically detects your installation type (PostgreSQL or SQLite)
- Stops all TracLine services
- Removes the TracLine application
- Removes all convenience commands (tracline-start, tracline-stop, tracline-web)
- Optionally removes data and configuration
- For PostgreSQL: Removes Docker volumes
- For SQLite: Removes the SQLite database file
- Creates backups of shell configuration files

### Alternative: SQLite-Specific Uninstaller
If you prefer, there's also a SQLite-specific uninstaller:
```bash
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall-sqlite.sh | bash
```

However, the universal uninstaller (uninstall.sh) is recommended as it handles both installation types.

---

# Manual Installation

If you prefer to install manually or need custom configuration, follow the instructions below.

## Table of Contents

- [Prerequisites](#prerequisites)
- [PostgreSQL Setup (Recommended)](#postgresql-setup-recommended)
- [Alternative Installations](#alternative-installations)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## Prerequisites

### Required Software
- **Python 3.8+** - Programming language runtime
- **Docker & Docker Compose** - For PostgreSQL database
- **Git** - Version control

### System Preparation

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3-venv docker.io docker-compose git

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and log back in for group changes to take effect
```

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install python@3.8 docker docker-compose git
```

#### Windows
- Install [Python 3.8+](https://www.python.org/downloads/)
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Install [Git for Windows](https://git-scm.com/download/win)

## PostgreSQL Setup (Recommended)

This is the recommended installation method using PostgreSQL with Docker.

### 1. Clone and Setup TracLine

```bash
# Clone repository
git clone git@github.com:techs-targe/TracLine.git
cd TracLine

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env if needed (default values work for local development)
nano .env  # or use your preferred editor
```

### 3. Start PostgreSQL and Initialize Database

```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 5

# Initialize database schema
python scripts/setup_postgres.py

# Copy PostgreSQL configuration
cp postgres_config.yaml tracline.yaml
```

### 4. Launch TracLine

```bash
# Start the web interface
cd web
python run_app.py
```

Access TracLine at http://localhost:8000

### 5. Quick Verification

```bash
# In a new terminal, verify the installation
tracline --version
tracline project create "TEST" "Test Project"
tracline project list
```

## Alternative Installations

### SQLite Installation (For Testing Only)

For quick testing without Docker:

```bash
# After step 1 above, use SQLite configuration
cp sqlite_config.yaml tracline.yaml

# Initialize SQLite database
tracline init

# Start web interface
cd web
python run_app.py
```

### Global Installation with pipx (PEP 668 Compliant)

For system-wide installation without virtual environment:

```bash
# Install pipx if not already installed
sudo apt install pipx  # Ubuntu/Debian
# or
brew install pipx  # macOS

# Install TracLine globally
pipx install git+ssh://git@github.com/techs-targe/TracLine.git

# Create configuration directory
mkdir -p ~/.config/tracline
wget -O ~/.config/tracline/tracline.yaml https://raw.githubusercontent.com/techs-targe/TracLine/main/postgres_config.yaml
```

### Production Deployment

For production environments, see [Deployment Guide](docs/DEPLOYMENT.md).

## Configuration

### Environment Variables (.env)

The `.env` file controls database and application settings:

```bash
# Database Configuration
DB_NAME=tracline
DB_USER=postgres
DB_PASS=postgres
DB_HOST=localhost
DB_PORT=5432

# TracLine Configuration
TRACLINE_CONFIG_PATH=~/.tracline
TRACLINE_UPLOAD_DIR=~/.tracline/uploads
```

### Application Configuration (tracline.yaml)

The main configuration file supports both PostgreSQL and SQLite:

```yaml
# PostgreSQL Configuration (Recommended)
database:
  type: postgresql
  host: localhost
  port: 5432
  name: tracline
  user: postgres
  password: postgres

# Application Settings
app:
  upload_dir: ~/.tracline/uploads
  log_level: INFO
```

## Troubleshooting

### Common Issues and Solutions

#### 1. python3-venv Not Found
```bash
# Ubuntu/Debian
sudo apt install python3.X-venv  # Replace X with your Python version

# Example for Python 3.8
sudo apt install python3.8-venv
```

#### 2. PostgreSQL Authentication Failed

If you see "fe_sendauth: no password supplied" or authentication errors:

**Quick fix:**
```bash
# Create default PostgreSQL configuration
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/fix-postgres-config.sh | bash
```

**Manual fix:**
```bash
# Check if config exists
ls -la ~/.tracline/tracline.yaml

# If missing, create it
mkdir -p ~/.tracline
cp ~/TracLine/postgres_config.yaml ~/.tracline/tracline.yaml

# Or download directly
wget -O ~/.tracline/tracline.yaml https://raw.githubusercontent.com/techs-targe/TracLine/main/postgres_config.yaml
```

**Common causes:**
- Configuration file not created during installation
- Wrong database type in configuration
- Missing password in configuration

#### 3. Docker Permission Denied

If you see `PermissionError: [Errno 13] Permission denied` when running `tracline-start`:

```bash
# Quick diagnosis and fix
bash ~/TracLine/scripts/fix-docker-permissions.sh

# Manual fix options:

# Option 1: Quick fix (opens new shell)
newgrp docker

# Option 2: Proper fix (recommended)
# Logout and login again

# Option 3: Alternative
su - $USER  # Enter your password

# Verify it works
docker info
```

Common causes:
- Just installed Docker but haven't logged out/in
- Not in the docker group
- Docker daemon not running

#### 4. PostgreSQL Connection Failed
```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# View PostgreSQL logs
docker-compose logs postgres

# Test connection manually
docker exec -it tracline-postgres psql -U postgres -d tracline
```

#### 5. Port Already in Use
```bash
# Check what's using port 5432 (PostgreSQL)
sudo lsof -i :5432

# Check what's using port 8000 (Web interface)
sudo lsof -i :8000

# Change ports in .env file if needed
DB_PORT=5433  # Alternative PostgreSQL port
WEB_PORT=8001  # Alternative web port
```

#### 6. Database Initialization Failed
```bash
# Reset and reinitialize
docker-compose down -v  # Warning: This deletes all data
docker-compose up -d postgres
sleep 5
python scripts/setup_postgres.py
```

#### 7. PEP 668 Error (externally-managed-environment)

This error occurs on Ubuntu 24.04 and newer systems:

```bash
# Solution 1: Use pipx (recommended)
pipx install .

# Solution 2: Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install .

# Solution 3: Force install (not recommended)
pip install . --break-system-packages
```

#### 8. Uvicorn Not Found Error

If you see "uvicorn not found" when running `tracline-start`:

**For PostgreSQL installations:**
```bash
# Quick fix script
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/fix-uvicorn.sh | bash
```

**For SQLite installations:**
```bash
# SQLite-specific fix
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/quick-fix-sqlite-uvicorn.sh | bash
```

**Manual fix (if scripts don't work):**
```bash
# Reinstall uvicorn in pipx environment
pipx inject tracline uvicorn[standard] --force

# Test if it works
~/.local/share/pipx/venvs/tracline/bin/python -m uvicorn --version
```

#### 9. TracLine Directory Not Found

If you see "TracLine directory not found at ~/TracLine" after a successful installation:

```bash
# Quick diagnosis (shorter command)
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/diag.sh | bash

# This will show:
# - Where TracLine directories exist on your system
# - Which commands are available
# - Current pipx installations
```

Common causes and fixes:

1. **Directory was deleted or moved**
   ```bash
   cd ~ && git clone https://github.com/techs-targe/TracLine.git
   ```

2. **Installation used wrong directory**
   Check the diagnosis output for TracLine locations

3. **Permission issues**
   ```bash
   ls -la ~/TracLine
   # Should show your user as owner
   ```

#### 10. Commands Not Found After Installation

If `tracline` or `tracline-start` commands are not found:

```bash
# Option 1: Source your shell configuration
source ~/.bashrc  # For bash
source ~/.zshrc   # For zsh

# Option 2: Run the post-install setup script
bash ~/TracLine/scripts/post-install-setup.sh

# Option 3: Manually add to PATH
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Option 4: Open a new terminal
# Simply close current terminal and open a new one
```

Verify installation:
```bash
# Check if tracline is installed
pipx list | grep tracline

# Check PATH
echo $PATH | grep -o '.local/bin'

# Find where tracline is installed
find ~/.local -name tracline -type f 2>/dev/null
```

#### 11. Database Schema Issues (Web Interface Errors)

If you see errors like "column project_root does not exist" or file associations not showing:

**Quick fix:**
```bash
# Run comprehensive database fix
cd ~/TracLine
python scripts/fix_database_issues.py
```

If you see "column description does not exist" errors:
```bash
# Fix file associations schema
cd ~/TracLine
python scripts/fix_file_associations_column.py
```

**What this fixes:**
- Renames `project_root_path` to `project_root` column
- Adds missing `monitor_interval` column
- Adds missing `description` column to file_associations
- Verifies file_associations table exists
- Optionally adds test file associations

**Manual fixes:**
```bash
# Fix just the column name issue
cd ~/TracLine
python scripts/fix_project_root_column.py

# Add file associations via CLI
tracline attach TASK-001 src/main.py
tracline attach TASK-001 README.md
```

#### 12. Shell Script Syntax Errors in tracline-start

If you see errors like:
- `/home/user/.local/bin/tracline-start: line 102: [: : integer expression expected`
- `/home/user/.local/bin/tracline-start: line 98: syntax error near unexpected token '2'`

**Quick fix:**
```bash
# Fix all script issues automatically
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/fix-heredoc-escaping.sh | bash
```

**Manual fix:**
```bash
# Remove and recreate the script
rm ~/.local/bin/tracline-start
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu.sh | bash
```

**Why this happens:**
- Unquoted heredoc delimiters cause shell expansion issues with redirections like `2>&1`
- Some shells don't properly expand `{1..30}` in certain contexts

#### 13. Tasks/Projects Not Showing in Web Interface

If the web interface shows no tasks or gets 404 errors for projects:

**Debug the database:**
```bash
cd ~/TracLine
python scripts/debug_projects.py
```

**Common issues:**
1. **Project ID mismatch**: Web expects `TEST-PROJECT` but you created `TEST-PROJ`
   ```bash
   # Create the expected project
   cd ~/TracLine
   python scripts/create_test_project.py
   ```

2. **No default project**: 
   ```bash
   # Create a project via CLI
   tracline project create "TEST-PROJECT" "Test Project"
   
   # Switch to it
   tracline project change TEST-PROJECT
   ```

3. **Empty database**:
   ```bash
   # Initialize with sample data
   tracline init
   ```

### Getting Help

1. Check the [FAQ](docs/FAQ.md)
2. Review [Common Issues](docs/TROUBLESHOOTING.md)
3. Search [GitHub Issues](https://github.com/techs-targe/TracLine/issues)
4. Ask on [Discussions](https://github.com/techs-targe/TracLine/discussions)

## Claude Code Integration

TracLine provides seamless integration with Claude Code for AI-driven development. This section covers the additional setup required for Claude Code integration.

### Prerequisites for Claude Code

1. **Install Claude Code CLI**
   - Download from [Claude Code website](https://claude.ai/download)
   - Follow platform-specific installation instructions
   - Verify installation: `claude --version`

2. **TracLine Installation**
   - Complete one of the installation methods above
   - Ensure `tracline` command is available in your PATH

### Claude Code Setup

1. **Copy Development Guide Template**
   
   Choose the appropriate template based on your TracLine installation:
   
   ```bash
   # For project-local TracLine installation
   cp CLAUDE.md.sample CLAUDE.md
   
   # For global TracLine installation (pip install tracline)
   cp CLAUDE.md.sample.globalinstall CLAUDE.md
   ```

2. **Customize CLAUDE.md**
   
   Edit the file to match your environment:
   ```bash
   nano CLAUDE.md  # or your preferred editor
   ```
   
   Key items to configure:
   - Project paths (use relative paths)
   - Database configuration
   - Team member IDs
   - Development standards

3. **Launch Scripts**
   
   TracLine includes pre-configured launch scripts for different team members:
   
   ```bash
   # Make scripts executable
   chmod +x scripts/claude-code/*.sh
   
   # Launch for specific team member
   ./scripts/claude-code/launch-claude-dev1.sh
   ```

### Quick Start for Claude Code

```bash
# 1. Install TracLine globally
pip install .

# 2. Setup configuration
mkdir -p ~/.tracline
cp postgres_config.yaml ~/.tracline/tracline.yaml

# 3. Initialize database
tracline init

# 4. Create project and team
tracline project create "MAIN" "Main Project"
tracline member add "AI-DEV-1" "AI Developer 1" --role ENGINEER
tracline project add-members MAIN AI-DEV-1

# 5. Setup Claude Code
cp CLAUDE.md.sample.globalinstall CLAUDE.md
# Edit CLAUDE.md with your settings

# 6. Launch Claude Code
./scripts/claude-code/launch-claude-template.sh
```

### Parallel AI Development

To run multiple AI developers simultaneously:

1. **Create Multiple Team Members**
   ```bash
   tracline member add "AI-BACKEND" "AI Backend Dev" --role ENGINEER
   tracline member add "AI-FRONTEND" "AI Frontend Dev" --role ENGINEER
   tracline member add "AI-TESTING" "AI Test Engineer" --role QA
   ```

2. **Create Custom Launch Scripts**
   ```bash
   cd scripts/claude-code
   cp launch-claude-template.sh launch-claude-backend.sh
   cp launch-claude-template.sh launch-claude-frontend.sh
   
   # Edit each script to set unique TASK_ASSIGNEE
   ```

3. **Launch Multiple Sessions**
   
   Open separate terminals for each AI developer:
   ```bash
   # Terminal 1
   ./scripts/claude-code/launch-claude-backend.sh
   
   # Terminal 2
   ./scripts/claude-code/launch-claude-frontend.sh
   
   # Terminal 3
   ./scripts/claude-code/launch-claude-testing.sh
   ```

### Natural Language Commands

Once Claude Code is running with TracLine context, you can use natural language commands:

- "Show me my next task" → `tracline next`
- "Create a task for implementing user authentication" → Creates and assigns task
- "Mark the current task as complete" → `tracline done`
- "Show project progress" → Lists tasks and status

### Verification

Test Claude Code integration:

```bash
# In Claude Code session
> Show me the current TracLine configuration

# Should display configuration from CLAUDE.md

> List all pending tasks assigned to me

# Should show tasks for the configured TASK_ASSIGNEE
```

For detailed Claude Code workflow, see the [Claude Code User Guide](docs/CLAUDE_CODE_USER_GUIDE.md).

## Next Steps

After successful installation:

1. **Create Your First Project**
   ```bash
   tracline project create "MYPROJECT" "My First Project"
   ```

2. **Add Team Members**
   ```bash
   tracline member add "john" "John Doe" --role ENGINEER
   tracline project add-members MYPROJECT john
   ```

3. **Create Tasks**
   ```bash
   tracline add "TASK-001" "Setup development environment" --project MYPROJECT
   ```

4. **Explore the Web Interface**
   - Visit http://localhost:8000
   - Navigate through Team, Tasks, and Traceability Matrix views

5. **Read the Documentation**
   - [User Guide](docs/USER_GUIDE.md) - Comprehensive usage guide
   - [Command Reference](docs/COMMAND_REFERENCE.md) - All CLI commands
   - [Claude Code User Guide](docs/CLAUDE_CODE_USER_GUIDE.md) - AI development workflow

For development with Claude Code, see the [Claude Code User Guide](docs/CLAUDE_CODE_USER_GUIDE.md) for detailed parallel AI development workflow.