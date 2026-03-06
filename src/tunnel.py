"""SSH Tunnel implementation."""

import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Optional

import psutil

from .config import TunnelConfig
from .logger import get_logger


class TunnelStatus(Enum):
    """Status of an SSH tunnel."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class SSHTunnel:
    """Manages a single SSH tunnel connection."""
    
    def __init__(self, config: TunnelConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.status = TunnelStatus.STOPPED
        self.retry_count = 0
        self.logger = get_logger()
        self.pid_file = Path(f"logs/{config.name}.pid")
    
    def start(self) -> bool:
        """Start the SSH tunnel."""
        if self.is_running():
            self.logger.warning(f"Tunnel '{self.config.name}' is already running")
            return True
        
        self.status = TunnelStatus.STARTING
        self.logger.info(f"Starting tunnel '{self.config.name}'...")
        
        ssh_command = self._build_ssh_command()
        
        try:
            self.process = subprocess.Popen(
                ssh_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0
            )
            
            time.sleep(2)
            
            if self.process.poll() is None:
                self.status = TunnelStatus.RUNNING
                self.retry_count = 0
                self._save_pid()
                self.logger.info(
                    f"Tunnel '{self.config.name}' started successfully "
                    f"(localhost:{self.config.local_port} -> "
                    f"{self.config.remote_host}:{self.config.remote_port})"
                )
                return True
            else:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                self.logger.error(f"Tunnel '{self.config.name}' failed to start: {stderr}")
                self.status = TunnelStatus.FAILED
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting tunnel '{self.config.name}': {e}")
            self.status = TunnelStatus.FAILED
            return False
    
    def stop(self) -> bool:
        """Stop the SSH tunnel."""
        if not self.is_running():
            self.logger.warning(f"Tunnel '{self.config.name}' is not running")
            return True
        
        self.logger.info(f"Stopping tunnel '{self.config.name}'...")
        
        try:
            # If using remote_command, kill remote processes first
            if self.config.remote_command:
                self._cleanup_remote_kubectl_processes()
            
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Force killing tunnel '{self.config.name}'")
                    self.process.kill()
                    self.process.wait()
                
                self.process = None
            
            self._cleanup_pid()
            self.status = TunnelStatus.STOPPED
            self.logger.info(f"Tunnel '{self.config.name}' stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping tunnel '{self.config.name}': {e}")
            return False
    
    def restart(self) -> bool:
        """Restart the SSH tunnel."""
        self.logger.info(f"Restarting tunnel '{self.config.name}'...")
        self.stop()
        time.sleep(1)
        return self.start()
    
    def is_running(self) -> bool:
        """Check if the tunnel is currently running."""
        if self.process is None:
            return False
        
        if self.process.poll() is not None:
            self.status = TunnelStatus.STOPPED
            return False
        
        return True
    
    def healthcheck(self) -> bool:
        """Perform a health check on the tunnel."""
        if not self.is_running():
            if self.config.auto_reconnect and self.retry_count < self.config.max_retries:
                self.logger.warning(
                    f"Tunnel '{self.config.name}' is down. "
                    f"Attempting reconnection ({self.retry_count + 1}/{self.config.max_retries})..."
                )
                self.status = TunnelStatus.RECONNECTING
                self.retry_count += 1
                time.sleep(self.config.retry_delay)
                return self.start()
            elif self.retry_count >= self.config.max_retries:
                self.logger.error(
                    f"Tunnel '{self.config.name}' failed after {self.config.max_retries} retries"
                )
                self.status = TunnelStatus.FAILED
                return False
        
        return True
    
    def get_info(self) -> dict:
        """Get tunnel information."""
        info = {
            "name": self.config.name,
            "status": self.status.value,
            "local_port": self.config.local_port,
            "remote": f"{self.config.remote_host}:{self.config.remote_port}",
            "host": f"{self.config.user}@{self.config.host}:{self.config.port}",
            "pid": self.process.pid if self.process else None,
            "retry_count": self.retry_count,
            "auto_reconnect": self.config.auto_reconnect,
        }
        
        if self.config.remote_command:
            info["remote_command"] = self.config.remote_command
        
        return info
    
    def _build_ssh_command(self) -> list[str]:
        """Build the SSH command with port forwarding."""
        if self.config.remote_command:
            ssh_args = [
                "ssh",
                "-L", f"{self.config.local_port}:{self.config.remote_host}:{self.config.remote_port}",
                "-p", str(self.config.port),
                f"{self.config.user}@{self.config.host}",
                "-o", "ServerAliveInterval=60",
                "-o", "ServerAliveCountMax=3",
                "-o", "ExitOnForwardFailure=yes",
                self.config.remote_command,
            ]
        else:
            ssh_args = [
                "ssh",
                "-N",
                "-L", f"{self.config.local_port}:{self.config.remote_host}:{self.config.remote_port}",
                "-p", str(self.config.port),
                f"{self.config.user}@{self.config.host}",
                "-o", "ServerAliveInterval=60",
                "-o", "ServerAliveCountMax=3",
                "-o", "ExitOnForwardFailure=yes",
            ]
        
        if self.config.password:
            ssh_args = ["sshpass", "-p", self.config.password] + ssh_args
            ssh_args.extend(["-o", "StrictHostKeyChecking=no"])
        
        return ssh_args
    
    def _save_pid(self) -> None:
        """Save process PID to file."""
        if self.process:
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            self.pid_file.write_text(str(self.process.pid))
    
    def _cleanup_pid(self) -> None:
        """Remove PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def _cleanup_remote_kubectl_processes(self) -> None:
        """Cleanup remote kubectl processes when stopping tunnel with remote_command."""
        try:
            # Extract the command name from remote_command (e.g., "kubectl" from the command)
            if "kubectl" in self.config.remote_command:
                cleanup_cmd = [
                    "ssh",
                    f"{self.config.user}@{self.config.host}",
                    "-p", str(self.config.port),
                    "pkill -9 kubectl"
                ]
                
                subprocess.run(
                    cleanup_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                self.logger.debug(f"Cleaned up remote kubectl processes for tunnel '{self.config.name}'")
        except Exception as e:
            self.logger.debug(f"Could not cleanup remote processes: {e}")
