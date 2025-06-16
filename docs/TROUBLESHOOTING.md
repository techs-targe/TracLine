# TracLine Troubleshooting Guide

This guide helps you resolve common issues with TracLine installation and usage.

## Installation Issues

### Docker Permission Denied

If you get "permission denied" errors with Docker:

```bash
# Add yourself to docker group
sudo usermod -aG docker $USER

# Apply changes (or logout/login)
newgrp docker
```

### Port Already in Use

If port 8000 is already in use:

```bash
# Check what's using port 8000
sudo lsof -i :8000

# Use a different port
cd ~/TracLine/web
uvicorn app:app --host 0.0.0.0 --port 8080
```

### TracLine Command Not Found

After installation, if `tracline` command is not found:

```bash
# Update your PATH
source ~/.bashrc

# Or open a new terminal
```

## Database Issues

### PostgreSQL Connection Failed

If PostgreSQL connection fails:

1. **Check Docker is running:**
   ```bash
   docker ps
   ```

2. **Check PostgreSQL container:**
   ```bash
   docker logs tracline-postgres
   ```

3. **Verify configuration:**
   ```bash
   cat ~/.tracline/tracline.yaml
   ```

### SQLite Database Locked

If you get "database is locked" errors with SQLite:

1. Close all TracLine processes
2. Check for stale lock files:
   ```bash
   ls -la ~/.tracline/*.db-journal
   ```
3. Remove stale locks if safe:
   ```bash
   rm ~/.tracline/*.db-journal
   ```

### SQLite "No Such Table" Error

If you see "no such table: projects" or similar errors:

**Solution:** Update to v2.0.1 or later:
```bash
cd ~/TracLine && git pull && pipx install . --force
```

This was fixed in v2.0.1 by improving database path resolution for user home directories (~/).

### SQLite UNIQUE Constraint Errors

If you see "UNIQUE constraint failed" errors when running with `--sample-data`:

**Solution:** This was fixed in v2.0.1. The system now properly detects and skips existing data. If you still see these errors:

1. **Force update to latest version:**
   ```bash
   cd ~/TracLine && git pull && pipx install . --force
   ```

2. **Or do a clean reinstall:**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall.sh | bash -s -- --remove-data
   curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu-sqlite.sh | bash -s -- --sample-data
   ```

## Web Interface Issues

### Page Not Loading

If the web interface doesn't load:

1. **Check the server is running:**
   ```bash
   ps aux | grep uvicorn
   ```

2. **Check logs:**
   ```bash
   # In the terminal where you started TracLine
   # Look for error messages
   ```

3. **Try direct API access:**
   ```bash
   curl http://localhost:8000/api/test
   ```

### File Associations Not Showing

If file associations don't appear in task details:

1. Ensure files are properly attached:
   ```bash
   tracline attach TASK-001 /path/to/file.txt
   ```

2. Check database connection:
   ```bash
   tracline dbcheck
   ```

## Common Issues

### Clean Reinstall

If you need a completely fresh installation:

```bash
# 1. Uninstall completely
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/uninstall.sh | bash -s -- --remove-data

# 2. Reinstall
# For PostgreSQL:
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu.sh | bash

# For SQLite:
curl -fsSL https://raw.githubusercontent.com/techs-targe/TracLine/main/scripts/install-ubuntu-sqlite.sh | bash
```

### Performance Issues

If TracLine is running slowly:

1. **For SQLite users:** Consider switching to PostgreSQL for better performance with large datasets

2. **Check database size:**
   ```bash
   tracline dbcheck
   ```

3. **Monitor resource usage:**
   ```bash
   docker stats  # For PostgreSQL users
   ```

## Getting Help

1. Check the [FAQ](FAQ.md)
2. Review [Installation Guide](../INSTALL.md)
3. Search [GitHub Issues](https://github.com/techs-targe/TracLine/issues)
4. Ask on [Discussions](https://github.com/techs-targe/TracLine/discussions)