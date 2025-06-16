# PostgreSQL Configuration for TaskShell Web Interface

This document explains how to set up the TaskShell web interface with PostgreSQL.

## Prerequisites

- PostgreSQL server installed and running
- Python 3.7 or higher
- psycopg2-binary package (`pip install psycopg2-binary`)

## Setup Steps

### 1. Install Required Packages

```bash
pip install psycopg2-binary fastapi uvicorn jinja2
```

### 2. Configure PostgreSQL

1. Create a database and user for TaskShell:

```sql
CREATE DATABASE tracline;
CREATE USER tracline WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE tracline TO tracline;
```

2. Or use the provided setup script:

```bash
# Navigate to the TaskShell root directory
cd /path/to/TracLine
python setup_postgres.py
```

### 3. Update TaskShell Configuration

Edit `tracline.yaml` to use PostgreSQL:

```yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  database: tracline
  user: postgres  # Change to your PostgreSQL username
  password: postgres  # Change to your PostgreSQL password
  # For production, use environment variable: 
  # export TASKSHELL_DB_PASSWORD=your_secure_password
```

### 4. Start the Web Interface

```bash
cd web
python app.py
```

The web interface will be available at http://localhost:8001

## Troubleshooting

### Connection Issues

If you encounter database connection issues:

1. Verify the PostgreSQL service is running:
   ```bash
   sudo systemctl status postgresql
   ```

2. Check the connection parameters in `tracline.yaml`

3. Ensure the database and user exist:
   ```bash
   psql -U postgres -c "\l" | grep tracline
   psql -U postgres -c "\du" | grep tracline
   ```

### Import Error for psycopg2

If you see an error about missing psycopg2:

```bash
pip install psycopg2-binary
```

## Using with Docker

If you're using Docker, you can connect to a PostgreSQL container:

```yaml
database:
  type: postgresql
  host: postgres  # Use the service name in docker-compose
  port: 5432
  database: tracline
  user: postgres
  password: postgres
```

And in your docker-compose.yml:

```yaml
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: tracline
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  tracline:
    build: .
    depends_on:
      - postgres
    environment:
      - TASKSHELL_DB_PASSWORD=postgres

volumes:
  postgres_data:
```