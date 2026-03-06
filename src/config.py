"""Configuration management for SSH tunnels."""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TunnelConfig(BaseModel):
    """Configuration for a single SSH tunnel."""
    
    name: str = Field(..., description="Unique name for this tunnel")
    enabled: bool = Field(default=True, description="Whether this tunnel is enabled")
    host: str = Field(..., description="SSH server hostname or IP")
    port: int = Field(default=22, description="SSH server port")
    user: str = Field(..., description="SSH username")
    password: Optional[str] = Field(default=None, description="SSH password (optional, uses SSH keys if not provided)")
    local_port: int = Field(..., description="Local port to bind")
    remote_host: str = Field(default="localhost", description="Remote host to forward to")
    remote_port: int = Field(..., description="Remote port to forward to")
    remote_command: Optional[str] = Field(default=None, description="Command to execute on remote server (e.g., kubectl port-forward)")
    auto_reconnect: bool = Field(default=True, description="Auto-reconnect on failure")
    max_retries: int = Field(default=5, description="Maximum reconnection attempts")
    retry_delay: int = Field(default=10, description="Delay between retries in seconds")
    
    @field_validator("port", "local_port", "remote_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v
    
    @field_validator("max_retries")
    @classmethod
    def validate_retries(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_retries must be non-negative")
        return v
    
    @field_validator("retry_delay")
    @classmethod
    def validate_delay(cls, v: int) -> int:
        if v < 1:
            raise ValueError("retry_delay must be at least 1 second")
        return v


class GlobalConfig(BaseModel):
    """Global configuration settings."""
    
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="logs/tunnels.log", description="Log file path")
    healthcheck_interval: int = Field(default=30, description="Healthcheck interval in seconds")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper
    
    @field_validator("healthcheck_interval")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < 5:
            raise ValueError("healthcheck_interval must be at least 5 seconds")
        return v


class Config(BaseModel):
    """Main configuration containing all tunnels and global settings."""
    
    tunnels: list[TunnelConfig] = Field(default_factory=list)
    global_config: GlobalConfig = Field(default_factory=GlobalConfig, alias="global")
    
    @field_validator("tunnels")
    @classmethod
    def validate_unique_names(cls, v: list[TunnelConfig]) -> list[TunnelConfig]:
        names = [t.name for t in v]
        if len(names) != len(set(names)):
            raise ValueError("Tunnel names must be unique")
        return v
    
    @field_validator("tunnels")
    @classmethod
    def validate_unique_local_ports(cls, v: list[TunnelConfig]) -> list[TunnelConfig]:
        enabled_tunnels = [t for t in v if t.enabled]
        ports = [t.local_port for t in enabled_tunnels]
        if len(ports) != len(set(ports)):
            raise ValueError("Local ports must be unique among enabled tunnels")
        return v


def load_config(config_path: Path) -> Config:
    """Load configuration from a JSON file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return Config.model_validate(data)


def get_default_config_path() -> Path:
    """Get the default configuration file path."""
    return Path("configs/tunnels.json")
