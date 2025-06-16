# TracLine Database Configuration Guide

TracLine supports both PostgreSQL and SQLite databases. This guide explains how to configure databases and switch between different database types.

## Default Configuration

TracLine is configured to use **PostgreSQL** by default. The standard configuration is as follows:

```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  database: tracline
  user: postgres
  password: postgres  # Use environment variables in production
```

## How to Switch Database Types

### 1. Edit Configuration File (Recommended)

You can change the database type by editing the `tracline.yaml` configuration file.

**PostgreSQL Configuration Example**:
```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  database: tracline
  user: postgres
  password: postgres
```

**SQLite Configuration Example**:
```yaml
database:
  type: sqlite
  url: ~/.tracline/tracline.db  # Path to database file
```

### 2. Using Environment Variables

You can set environment variables to override configuration file settings:

```bash
# Specify database type
export TRACLINE_DB_TYPE=sqlite

# Specify SQLite path (if needed)
export TRACLINE_DB_URL=~/.tracline/custom.db

# Or specify PostgreSQL credentials
export TRACLINE_DB_HOST=localhost
export TRACLINE_DB_PORT=5432
export TRACLINE_DB_NAME=tracline
export TRACLINE_DB_USER=postgres
export TRACLINE_DB_PASSWORD=your_password
```

## Database Initialization

### PostgreSQL Database Setup

1. Ensure PostgreSQL is installed
2. Initialize the database with the following command:

```bash
python setup_postgres.py
```

Or use the web application startup script:

```bash
cd web
./start_postgres_app.sh
```

This script automatically configures PostgreSQL and initializes the database as needed.

### SQLite Database Setup

SQLite is automatically initialized. After editing the configuration file as shown below, simply start the application and the database file will be created automatically:

```yaml
database:
  type: sqlite
  url: ~/.tracline/tracline.db
```

## Data Migration Between Databases

To migrate data from SQLite to PostgreSQL, you can use the following script:

```bash
python sqlite_to_postgresql.py --source ~/.tracline/tracline.db
```

## Important Notes

1. **Consistent Database Usage**: Do not mix database types within the same application instance.

2. **Proper Connection Management**: Database connections are managed automatically, but for long-running scripts, consider explicitly calling `connect()` and `disconnect()`.

3. **Environment Variable Scope**: Environment variables are only effective within the shell session scope. Use configuration files for persistent changes.

4. **Password Security**: In production environments, do not write database passwords directly in configuration files. Use environment variables (`TRACLINE_DB_PASSWORD`) instead.