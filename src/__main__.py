"""CLI entry point for SSH Tunnel Manager."""

import sys
import time
from pathlib import Path

import click
from colorama import Fore, Style

from .config import get_default_config_path
from .manager import TunnelManager


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """SSH Tunnel Manager - Manages multiple SSH tunnels with automatic reconnection."""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to configuration file (default: configs/tunnels.json)"
)
@click.option(
    "--tunnel",
    "-t",
    type=str,
    default=None,
    help="Start only a specific tunnel by name"
)
@click.option(
    "--foreground",
    "-f",
    is_flag=True,
    help="Run in foreground (blocking mode)"
)
def start(config: Path, tunnel: str, foreground: bool):
    """Start SSH tunnels."""
    config_path = config or get_default_config_path()
    
    if not config_path.exists():
        click.echo(f"{Fore.RED}Error: Configuration file not found: {config_path}{Style.RESET_ALL}")
        click.echo(f"{Fore.YELLOW}Create a config file at {config_path} or use --config{Style.RESET_ALL}")
        sys.exit(1)
    
    try:
        manager = TunnelManager.from_config_file(config_path)
        
        if tunnel:
            success = manager.start_tunnel(tunnel)
        else:
            success = manager.start_all()
        
        if not success:
            click.echo(f"{Fore.RED}Failed to start tunnel(s){Style.RESET_ALL}")
            sys.exit(1)
        
        click.echo(f"{Fore.GREEN}✓ Tunnel(s) started successfully{Style.RESET_ALL}")
        
        if foreground:
            click.echo(f"{Fore.CYAN}Running in foreground mode. Press Ctrl+C to stop...{Style.RESET_ALL}")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                click.echo(f"\n{Fore.YELLOW}Stopping tunnels...{Style.RESET_ALL}")
                manager.stop_all()
                click.echo(f"{Fore.GREEN}✓ Tunnels stopped{Style.RESET_ALL}")
        
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to configuration file"
)
@click.option(
    "--tunnel",
    "-t",
    type=str,
    default=None,
    help="Stop only a specific tunnel by name"
)
def stop(config: Path, tunnel: str):
    """Stop SSH tunnels."""
    config_path = config or get_default_config_path()
    
    if not config_path.exists():
        click.echo(f"{Fore.RED}Error: Configuration file not found: {config_path}{Style.RESET_ALL}")
        sys.exit(1)
    
    try:
        manager = TunnelManager.from_config_file(config_path)
        
        if tunnel:
            success = manager.stop_tunnel(tunnel)
        else:
            success = manager.stop_all()
        
        if success:
            click.echo(f"{Fore.GREEN}✓ Tunnel(s) stopped{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.RED}Failed to stop tunnel(s){Style.RESET_ALL}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to configuration file"
)
@click.option(
    "--tunnel",
    "-t",
    type=str,
    default=None,
    help="Restart only a specific tunnel by name"
)
def restart(config: Path, tunnel: str):
    """Restart SSH tunnels."""
    config_path = config or get_default_config_path()
    
    if not config_path.exists():
        click.echo(f"{Fore.RED}Error: Configuration file not found: {config_path}{Style.RESET_ALL}")
        sys.exit(1)
    
    try:
        manager = TunnelManager.from_config_file(config_path)
        
        if tunnel:
            success = manager.restart_tunnel(tunnel)
        else:
            success = manager.restart_all()
        
        if success:
            click.echo(f"{Fore.GREEN}✓ Tunnel(s) restarted{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.RED}Failed to restart tunnel(s){Style.RESET_ALL}")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to configuration file"
)
@click.option(
    "--json",
    "-j",
    is_flag=True,
    help="Output in JSON format"
)
def status(config: Path, json: bool):
    """Show status of SSH tunnels."""
    config_path = config or get_default_config_path()
    
    if not config_path.exists():
        click.echo(f"{Fore.RED}Error: Configuration file not found: {config_path}{Style.RESET_ALL}")
        sys.exit(1)
    
    try:
        manager = TunnelManager.from_config_file(config_path)
        status_info = manager.get_status()
        
        if json:
            import json as json_lib
            click.echo(json_lib.dumps(status_info, indent=2))
        else:
            click.echo(f"\n{Fore.CYAN}SSH Tunnel Manager Status{Style.RESET_ALL}")
            click.echo(f"{'=' * 60}")
            click.echo(f"Total tunnels: {status_info['total']}")
            click.echo(f"Active tunnels: {Fore.GREEN}{status_info['active']}{Style.RESET_ALL}")
            click.echo(f"\n{Fore.CYAN}Tunnels:{Style.RESET_ALL}")
            
            for tunnel in status_info['tunnels']:
                status_color = Fore.GREEN if tunnel['status'] == 'running' else Fore.RED
                click.echo(f"\n  {Fore.YELLOW}• {tunnel['name']}{Style.RESET_ALL}")
                click.echo(f"    Status: {status_color}{tunnel['status']}{Style.RESET_ALL}")
                click.echo(f"    Local Port: {tunnel['local_port']}")
                click.echo(f"    Remote: {tunnel['remote']}")
                click.echo(f"    Host: {tunnel['host']}")
                if tunnel['pid']:
                    click.echo(f"    PID: {tunnel['pid']}")
                if tunnel['retry_count'] > 0:
                    click.echo(f"    Retries: {tunnel['retry_count']}")
            
            click.echo()
            
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output"
)
@click.option(
    "--lines",
    "-n",
    type=int,
    default=50,
    help="Number of lines to show (default: 50)"
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to configuration file"
)
def logs(follow: bool, lines: int, config: Path):
    """Show tunnel logs."""
    config_path = config or get_default_config_path()
    
    try:
        from .config import load_config
        cfg = load_config(config_path)
        log_file = Path(cfg.global_config.log_file)
        
        if not log_file.exists():
            click.echo(f"{Fore.YELLOW}No log file found at {log_file}{Style.RESET_ALL}")
            return
        
        if follow:
            click.echo(f"{Fore.CYAN}Following logs (Ctrl+C to stop)...{Style.RESET_ALL}\n")
            import subprocess
            try:
                if sys.platform == 'win32':
                    subprocess.run(["powershell", "-Command", f"Get-Content {log_file} -Wait -Tail {lines}"])
                else:
                    subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)])
            except KeyboardInterrupt:
                click.echo(f"\n{Fore.YELLOW}Stopped following logs{Style.RESET_ALL}")
        else:
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    click.echo(line.rstrip())
                    
    except Exception as e:
        click.echo(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
