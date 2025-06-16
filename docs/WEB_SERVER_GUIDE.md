# TracLine Web Server Guide

## Overview

TracLine includes a web interface that can be run independently of the CLI tools. This guide covers various ways to run the web server.

## Installation Options

### 1. Full Installation with PostgreSQL
```bash
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu.sh | bash
```

### 2. SQLite Installation (No Docker)
```bash
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu-sqlite.sh | bash
```

## Running the Web Server

### Method 1: Using tracline-start (Recommended)

This starts both the database and web server:

```bash
tracline-start
```

- With PostgreSQL: Starts Docker PostgreSQL + web server
- With SQLite: Just starts the web server

### Method 2: Web Server Only (SQLite)

If you installed the SQLite version:

```bash
tracline-web
```

This starts only the web interface without any database management.

### Method 3: Manual Start (Advanced)

#### PostgreSQL Version
```bash
# Ensure database is running
cd ~/TracLine
docker-compose up -d postgres

# Start web server
cd web
~/.local/share/pipx/venvs/tracline/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```

#### SQLite Version
```bash
cd ~/TracLine/web
export TRACLINE_CONFIG=~/.tracline/tracline.yaml
~/.local/share/pipx/venvs/tracline/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```

### Method 4: Development Mode

For development with auto-reload:

```bash
cd ~/TracLine/web
~/.local/share/pipx/venvs/tracline/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

### Web Server Settings

The web server configuration is in `tracline.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8000
```

### Environment Variables

You can override settings with environment variables:

```bash
export WEB_HOST=127.0.0.1
export WEB_PORT=8080
tracline-start
```

## Web Interface Features

The web interface provides:

- **Dashboard**: Overview of tasks and team
- **Task Management**: Create, update, and track tasks
- **Team View**: Hierarchical team visualization
- **Traceability Matrix**: File-task relationships
- **Settings**: View and update configuration

## Accessing the Interface

Once started, access TracLine at:
- Default: http://localhost:8000
- Network: http://YOUR_IP:8000

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
sudo lsof -i :8000

# Use a different port
cd ~/TracLine/web
~/.local/share/pipx/venvs/tracline/bin/uvicorn app:app --host 0.0.0.0 --port 8080
```

### Database Connection Issues

#### PostgreSQL
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# View logs
docker-compose logs postgres
```

#### SQLite
```bash
# Check database file exists
ls -la ~/.tracline/tracline.db

# Check permissions
chmod 644 ~/.tracline/tracline.db
```

### Web Server Won't Start

1. Check TracLine is installed:
   ```bash
   tracline --version
   ```

2. Verify web directory exists:
   ```bash
   ls ~/TracLine/web
   ```

3. Check uvicorn is installed:
   ```bash
   ~/.local/share/pipx/venvs/tracline/bin/uvicorn --version
   ```

## Production Deployment

For production use, consider:

1. **Reverse Proxy**: Use Nginx or Apache
2. **Process Manager**: Use systemd or supervisor
3. **HTTPS**: Configure SSL certificates
4. **Firewall**: Restrict access as needed

Example systemd service is created during installation at:
```
~/.local/bin/tracline.service
```

## API Access

The web server also provides REST API endpoints:

- `/api/tasks` - Task management
- `/api/projects` - Project management
- `/api/members` - Team members
- `/api/database-info` - System information

See API documentation at http://localhost:8000/docs when the server is running.