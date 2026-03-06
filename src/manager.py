"""Manager for multiple SSH tunnels."""

import signal
import threading
import time
from pathlib import Path
from typing import Optional

from .config import Config, TunnelConfig, load_config
from .logger import get_logger, setup_logger
from .tunnel import SSHTunnel, TunnelStatus


class TunnelManager:
    """Manages multiple SSH tunnels."""
    
    def __init__(self, config: Config):
        self.config = config
        self.tunnels: dict[str, SSHTunnel] = {}
        self.logger = setup_logger(
            level=config.global_config.log_level,
            log_file=config.global_config.log_file
        )
        self.healthcheck_thread: Optional[threading.Thread] = None
        self.running = False
        self._shutting_down = False
        self._setup_signal_handlers()
        
        for tunnel_config in config.tunnels:
            if tunnel_config.enabled:
                self.tunnels[tunnel_config.name] = SSHTunnel(tunnel_config)
    
    def start_all(self) -> bool:
        """Start all configured tunnels."""
        self.logger.info("Starting all tunnels...")
        success = True
        
        for name, tunnel in self.tunnels.items():
            if not tunnel.start():
                success = False
        
        if success:
            self.running = True
            self._start_healthcheck()
        
        return success
    
    def start_tunnel(self, name: str) -> bool:
        """Start a specific tunnel by name."""
        if name not in self.tunnels:
            self.logger.error(f"Tunnel '{name}' not found in configuration")
            return False
        
        result = self.tunnels[name].start()
        
        if result and not self.running:
            self.running = True
            self._start_healthcheck()
        
        return result
    
    def stop_all(self) -> bool:
        """Stop all running tunnels."""
        self.logger.info("Stopping all tunnels...")
        self.running = False
        
        if self.healthcheck_thread:
            self.healthcheck_thread.join(timeout=5)
        
        success = True
        for name, tunnel in self.tunnels.items():
            if not tunnel.stop():
                success = False
        
        return success
    
    def stop_tunnel(self, name: str) -> bool:
        """Stop a specific tunnel by name."""
        if name not in self.tunnels:
            self.logger.error(f"Tunnel '{name}' not found in configuration")
            return False
        
        result = self.tunnels[name].stop()
        
        if all(not t.is_running() for t in self.tunnels.values()):
            self.running = False
        
        return result
    
    def restart_all(self) -> bool:
        """Restart all tunnels."""
        self.logger.info("Restarting all tunnels...")
        self.stop_all()
        time.sleep(1)
        return self.start_all()
    
    def restart_tunnel(self, name: str) -> bool:
        """Restart a specific tunnel by name."""
        if name not in self.tunnels:
            self.logger.error(f"Tunnel '{name}' not found in configuration")
            return False
        
        return self.tunnels[name].restart()
    
    def get_status(self) -> dict:
        """Get status of all tunnels."""
        return {
            "running": self.running,
            "tunnels": [tunnel.get_info() for tunnel in self.tunnels.values()],
            "total": len(self.tunnels),
            "active": sum(1 for t in self.tunnels.values() if t.is_running()),
        }
    
    def _start_healthcheck(self) -> None:
        """Start the healthcheck thread."""
        if self.healthcheck_thread and self.healthcheck_thread.is_alive():
            return
        
        self.healthcheck_thread = threading.Thread(
            target=self._healthcheck_loop,
            daemon=True
        )
        self.healthcheck_thread.start()
        self.logger.info("Healthcheck thread started")
    
    def _healthcheck_loop(self) -> None:
        """Continuously monitor tunnel health."""
        interval = self.config.global_config.healthcheck_interval
        
        while self.running:
            time.sleep(interval)
            
            if not self.running:
                break
            
            for name, tunnel in self.tunnels.items():
                if not tunnel.healthcheck():
                    self.logger.error(f"Healthcheck failed for tunnel '{name}'")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            if self._shutting_down:
                return
            
            self._shutting_down = True
            self.logger.info(f"Received signal {signum}, shutting down...")
            self.stop_all()
            import sys
            sys.exit(0)
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except (AttributeError, ValueError):
            pass
    
    @classmethod
    def from_config_file(cls, config_path: Path) -> "TunnelManager":
        """Create a TunnelManager from a configuration file."""
        config = load_config(config_path)
        return cls(config)
