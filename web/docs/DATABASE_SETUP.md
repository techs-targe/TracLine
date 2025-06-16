# Database Setup Guide

This guide explains how to set up the database for the TracLine Web Interface.

## SQLite Setup

The default database type is SQLite. To set up the SQLite database with test data:

```bash
# Run the fix script first to ensure schema is correct
python fix_sqlite_schema.py

# Then run the direct setup script to create test data
python direct_db_setup.py
```

This will create a SQLite database in `~/.tracline/tracline.db` with sample data including:
- 9 team members in a hierarchical structure
- 25+ tasks of various statuses
- File associations and task relationships
- A test project

## PostgreSQL Setup

If you're using PostgreSQL, you can set up the test data with:

```bash
# Make sure the script is executable
chmod +x run_postgres_test_data.sh

# Run the script
./run_postgres_test_data.sh
```

This will:
- Connect to the PostgreSQL database specified in your config
- Create the same test data as the SQLite setup

## Configuration

The database configuration is controlled by the config file (default: `~/.tracline/tracline.yaml`).

To switch between database types, modify the `database` section:

### SQLite Configuration
```yaml
database:
  type: sqlite
  file: ~/.tracline/tracline.db
```

### PostgreSQL Configuration
```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  user: username
  password: password
  database: tracline
```

## Fixing Database Query Errors

If you see SQL errors like:
```
psycopg2.errors.SyntaxError: syntax error at end of input
LINE 6:         
                ^
```

This is usually due to a mismatch between the database type and the parameter placeholders in SQL queries:
- SQLite uses `?` for parameters 
- PostgreSQL uses `$1`, `$2`, etc.

The application should automatically detect the database type and use the appropriate placeholders, but if you encounter errors, run the appropriate setup script for your database type.

## Troubleshooting

### Missing Tables or Columns
If you see errors about missing tables or columns, run the appropriate setup script:
- For SQLite: `python fix_sqlite_schema.py`
- For PostgreSQL: Create tables using the ORM model methods 

### No Test Data
If the application shows no data, run one of the test data scripts:
- For SQLite: `python direct_db_setup.py`
- For PostgreSQL: `./run_postgres_test_data.sh`