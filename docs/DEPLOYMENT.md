# TracLine Deployment Guide

## Clean Deployment from Scratch

This guide provides step-by-step instructions for deploying TracLine in a fresh environment.

### Prerequisites

- Python 3.8 or higher
- Git
- Docker (optional, for PostgreSQL setup)

### Step-by-Step Deployment

#### 1. Clone the Repository

```bash
git clone git@github.com:techs-targe/TracLine.git
cd TracLine
```

#### 2. Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

#### 4. Database Setup

Choose one of the following options:

##### Option A: SQLite (Simplest)

```bash
# Copy SQLite configuration
cp sqlite_config.yaml tracline.yaml

# Initialize database
tracline init
```

##### Option B: PostgreSQL with Docker (Recommended)

```bash
# Start PostgreSQL container
docker-compose up -d

# Wait for database to be ready
sleep 5

# Setup PostgreSQL schema
python scripts/setup_postgres.py

# Copy PostgreSQL configuration
cp postgres_config.yaml tracline.yaml

# Initialize TracLine
tracline init
```

##### Option C: Existing PostgreSQL

```bash
# Edit postgres_config.yaml with your credentials
nano postgres_config.yaml

# Copy configuration
cp postgres_config.yaml tracline.yaml

# Setup database (if not exists)
python scripts/manage_db.py reset
python scripts/setup_postgres.py

# Initialize TracLine
tracline init
```

#### 5. Verify Installation

```bash
# Test CLI commands
tracline task add "Test task" --assignee "Test User"
tracline task list
```

#### 6. Start Web Interface

```bash
cd web

# For PostgreSQL
python run_postgres_app.py

# For SQLite
python run_app.py
```

#### 7. Access the Application

Open your browser and navigate to: http://localhost:8000

### Server Management

#### Starting the Server

After a system restart, follow these steps to start TracLine:

##### 1. Start Database (if using Docker)
```bash
# Start PostgreSQL container
docker start tracline-postgres
# Or using docker-compose
docker-compose up -d

# Verify it's running
docker ps | grep postgres
```

##### 2. Start TracLine Web Server

**Foreground Mode (for debugging)**:
```bash
cd ~/TracLine/web
python run_postgres_app.py
```

**Background Mode (recommended)**:
```bash
# Using nohup
cd ~/TracLine/web
nohup python run_postgres_app.py > ~/tracline.log 2>&1 &

# Check the log
tail -f ~/tracline.log
```

**Using screen (persistent session)**:
```bash
# Create a new screen session
screen -S tracline

# Start the server
cd ~/TracLine/web
python run_postgres_app.py

# Detach from screen: Ctrl+A, then D
# Reattach later: screen -r tracline
```

##### 3. Verify Server is Running
```bash
# Check if process is running
ps aux | grep run_postgres_app

# Check if port is listening
netstat -tlnp | grep 8000

# Test API endpoint
curl http://localhost:8000/api/projects
```

#### Stopping the Server

```bash
# Find and kill the process
pkill -f "run_postgres_app.py"

# Or kill by port
fuser -k 8000/tcp

# If using screen
screen -r tracline
# Then Ctrl+C to stop
```

#### Automatic Startup on Boot

To automatically start TracLine when the system boots:

##### Using systemd (Recommended)

1. Create the service file:
```bash
sudo nano /etc/systemd/system/tracline.service
```

2. Add the following content:
```ini
[Unit]
Description=TracLine Web Application
After=network.target docker.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/TracLine/web
ExecStartPre=/usr/bin/docker start tracline-postgres
ExecStart=/path/to/TracLine/venv/bin/python run_postgres_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tracline
sudo systemctl start tracline

# Check status
sudo systemctl status tracline

# View logs
sudo journalctl -u tracline -f
```

##### Using a Startup Script

Create a startup script:
```bash
nano ~/start-tracline.sh
```

Add:
```bash
#!/bin/bash
# Start TracLine services

# Start PostgreSQL if using Docker
docker start tracline-postgres 2>/dev/null

# Wait for database
sleep 5

# Start TracLine
cd /path/to/TracLine/web
source ../venv/bin/activate
nohup python run_postgres_app.py > ~/tracline.log 2>&1 &

echo "TracLine started. Check logs at ~/tracline.log"
```

Make it executable:
```bash
chmod +x ~/start-tracline.sh
```

Add to crontab for automatic startup:
```bash
crontab -e
# Add this line:
@reboot /path/to/start-tracline.sh
```

### Troubleshooting

#### PostgreSQL Connection Issues

If you encounter connection errors:

```bash
# Check if PostgreSQL is running (Docker)
docker ps | grep tracline-postgres

# Restart PostgreSQL container
docker-compose restart

# Check logs
docker-compose logs postgres
```

#### Database Reset

To completely reset the database:

```bash
# For PostgreSQL with Docker
docker-compose down -v
docker-compose up -d

# For existing PostgreSQL
python scripts/manage_db.py reset

# Reinitialize
python scripts/setup_postgres.py
tracline init
```

#### Port Conflicts

If port 8000 is already in use:

```bash
# Find process using port 8000
lsof -ti :8000

# Kill the process
kill -9 $(lsof -ti :8000)

# Or use a different port
cd web
python run_app.py --port 8080
```

### Production Deployment

For production environments, consider:

1. **Environment Variables**: Use `.env` file for sensitive configuration
2. **Database Backups**: Set up regular PostgreSQL backups
3. **Process Manager**: Use systemd or supervisor for the web server
4. **Reverse Proxy**: Configure Nginx or Apache for SSL/TLS
5. **Monitoring**: Set up logging and monitoring

Example production setup with systemd:

```ini
# /etc/systemd/system/tracline.service
[Unit]
Description=TracLine Web Application
After=network.target postgresql.service

[Service]
Type=simple
User=tracline
WorkingDirectory=/opt/tracline/web
Environment="PATH=/opt/tracline/venv/bin"
ExecStart=/opt/tracline/venv/bin/python run_postgres_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Deployment (Alternative)

For a fully containerized deployment, create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8000

CMD ["python", "web/run_postgres_app.py"]
```

Build and run:

```bash
docker build -t tracline .
docker run -d -p 8000:8000 --env-file .env tracline
```