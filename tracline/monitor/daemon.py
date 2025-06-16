"""File system monitoring daemon for TracLine."""

import os
import sys
import signal
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from .handler import FileChangeHandler
from ..core.config import Config
from ..db.factory import DatabaseFactory
import daemon
import lockfile
import json

logger = logging.getLogger(__name__)


class MonitorDaemon:
    """Daemon to monitor file system changes for TracLine projects."""
    
    def __init__(self, project_id, monitor_path, config_path=None):
        self.project_id = project_id
        self.monitor_path = Path(monitor_path).absolute()
        self.config = Config(config_path)
        self.observer = None
        self.handler = None
        self.running = False
        
        # Daemon configuration
        self.pidfile_path = Path.home() / '.tracline' / 'monitor' / f'{project_id}.pid'
        self.pidfile_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load project settings
        self.settings = self._load_project_settings()
        
    def _load_project_settings(self):
        """Load project-specific monitoring settings."""
        try:
            db = DatabaseFactory.create(self.config.config.database)
            db.connect()
            
            if self.config.config.database.type == "postgresql":
                query = "SELECT * FROM project_settings WHERE project_id = %s"
                params = [self.project_id]
            else:
                query = "SELECT * FROM project_settings WHERE project_id = ?"
                params = [self.project_id]
                
            cursor = db.execute_query(query, params)
            result = cursor.fetchone()
            
            db.disconnect()
            
            if result:
                if isinstance(result, dict):
                    return result
                else:
                    # Convert tuple to dict for SQLite
                    extensions = result[3]
                    if extensions and isinstance(extensions, str):
                        # Parse JSON string for SQLite
                        extensions = json.loads(extensions)
                    else:
                        extensions = ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs']
                    
                    return {
                        'monitor_enabled': result[1],
                        'monitor_path': result[2],
                        'monitor_extensions': extensions
                    }
            else:
                # Default settings
                return {
                    'monitor_enabled': True,
                    'monitor_path': str(self.monitor_path),
                    'monitor_extensions': ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs']
                }
                
        except Exception as e:
            logger.error(f"Failed to load project settings: {e}")
            return {
                'monitor_enabled': True,
                'monitor_path': str(self.monitor_path),
                'monitor_extensions': ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go', '.rs']
            }
    
    def start(self, as_daemon=True):
        """Start the monitoring daemon."""
        if as_daemon:
            self._start_daemon()
        else:
            self._run()
    
    def _start_daemon(self):
        """Start as a background daemon."""
        # Fork first child
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process - wait a bit then exit
                time.sleep(0.5)
                return
        except OSError as e:
            logger.error(f"Fork #1 failed: {e}")
            sys.exit(1)
            
        # Decouple from parent environment
        os.chdir(str(self.monitor_path))
        os.setsid()
        os.umask(0)
        
        # Fork second child
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #2 failed: {e}")
            sys.exit(1)
            
        # Now we're in the daemon process
        # Write PID file
        with open(self.pidfile_path, 'w') as f:
            f.write(str(os.getpid()))
            
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(f'/tmp/tracline-monitor-{self.project_id}.out', 'a+')
        se = open(f'/tmp/tracline-monitor-{self.project_id}.err', 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        
        # Configure logging to use our output files
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(so),
                logging.StreamHandler(se)
            ]
        )
        
        # Run the daemon
        try:
            self._run()
        except Exception as e:
            logger.error(f"Daemon error: {e}", exc_info=True)
            self._shutdown()
    
    def _run(self):
        """Run the monitoring loop."""
        # Force a flush to ensure logs are written
        print(f"Starting file monitor for project {self.project_id} at {self.monitor_path}", flush=True)
        logger.info(f"Starting file monitor for project {self.project_id} at {self.monitor_path}")
        
        # Create handler and observer
        self.handler = FileChangeHandler(
            self.project_id,
            self.config.config.database,
            self.settings.get('monitor_extensions')
        )
        
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.monitor_path), recursive=True)
        self.observer.start()
        
        self.running = True
        print(f"Monitor is now running for project {self.project_id}", flush=True)
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._shutdown()
        except Exception as e:
            print(f"Monitor error: {e}", flush=True)
            logger.error(f"Monitor error: {e}", exc_info=True)
            self._shutdown()
        
        self.observer.join()
        
    def _shutdown(self, signum=None, frame=None):
        """Shutdown the daemon gracefully."""
        logger.info(f"Shutting down file monitor for project {self.project_id}")
        self.running = False
        
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            
        # Clean up PID file
        if self.pidfile_path.exists():
            self.pidfile_path.unlink()
            
    def stop(self):
        """Stop the daemon by sending SIGTERM."""
        if not self.pidfile_path.exists():
            logger.warning(f"No monitor running for project {self.project_id}")
            return False
            
        try:
            with open(self.pidfile_path, 'r') as f:
                pid = int(f.read().strip())
                
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Stopped monitor for project {self.project_id} (PID: {pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop monitor: {e}")
            return False
            
    def status(self):
        """Check if daemon is running."""
        if not self.pidfile_path.exists():
            return False
            
        try:
            with open(self.pidfile_path, 'r') as f:
                pid = int(f.read().strip())
                
            # Check if process is running
            os.kill(pid, 0)
            return True
            
        except (OSError, ValueError):
            # Process not running, clean up stale PID file
            if self.pidfile_path.exists():
                self.pidfile_path.unlink()
            return False
            
    @classmethod
    def list_monitors(cls):
        """List all running monitors."""
        monitor_dir = Path.home() / '.tracline' / 'monitor'
        if not monitor_dir.exists():
            return []
            
        monitors = []
        for pidfile in monitor_dir.glob('*.pid'):
            project_id = pidfile.stem
            try:
                with open(pidfile, 'r') as f:
                    pid = int(f.read().strip())
                    
                # Check if process is running
                os.kill(pid, 0)
                monitors.append({
                    'project_id': project_id,
                    'pid': pid,
                    'status': 'running'
                })
            except (OSError, ValueError):
                # Process not running
                monitors.append({
                    'project_id': project_id,
                    'pid': None,
                    'status': 'stopped'
                })
                
        return monitors