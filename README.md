# SSH Tunnel Manager

Python SSH tunnel manager with support for multiple simultaneous connections and automatic reconnection.

## 🚀 Features

- ✅ Management of multiple simultaneous SSH tunnels
- ✅ Automatic reconnection when a tunnel drops
- ✅ Configuration via JSON files
- ✅ Automatic tunnel healthcheck
- ✅ Intuitive CLI with simple commands
- ✅ Detailed logging with colors
- ✅ Robust process management

## 📋 Requirements

- Python 3.11 or higher
- UV (Python package manager)
- SSH installed on system
- SSH keys configured (optional if using passwords)

## 🔧 Installation

1. **Install project dependencies**:
```bash
cd ssh-tunnel-manager
uv sync
```

## ⚙️ Configuration

1. **Create configuration file**:
```bash
cp configs/tunnels.example.json configs/tunnels.json
```

2. **Edit `configs/tunnels.json`** with your tunnels:
```json
{
  "tunnels": [
    {
      "name": "production-db",
      "host": "192.168.4.163",
      "port": 11050,
      "user": "username",
      "password": "your_password_here",
      "local_port": 5433,
      "remote_host": "localhost",
      "remote_port": 5433,
      "auto_reconnect": true,
      "max_retries": 5,
      "retry_delay": 10,
      "enabled": true
    }
  ],
  "global": {
    "log_level": "INFO",
    "log_file": "logs/tunnels.log",
    "healthcheck_interval": 30
  }
}
```

### Configuration Parameters

Each tunnel can have the following parameters:

- `name`: Unique tunnel name (required)
- `enabled`: Whether the tunnel is enabled (default: true, optional)
- `host`: SSH server (required)
- `port`: SSH port (default: 22)
- `user`: SSH user (required)
- `password`: SSH password (optional, uses SSH keys if not provided)
- `local_port`: Local port to bind (required)
- `remote_host`: Remote host to forward to (default: localhost)
- `remote_port`: Remote port to forward to (required)
- `remote_command`: Command to execute on remote server (optional, for double tunnels)
- `auto_reconnect`: Automatically reconnect on failure (default: true)
- `max_retries`: Maximum reconnection attempts (default: 5)
- `retry_delay`: Delay between retries in seconds (default: 10)
- `enabled`: Whether the tunnel is enabled (default: true, optional)

#### Global:
- `log_level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_file`: Log file path
- `healthcheck_interval`: Healthcheck interval in seconds

## 📖 Usage

### Basic Commands

**Start all tunnels**:
```bash
uv run ssh-tunnel start
```

**Start a specific tunnel**:
```bash
uv run ssh-tunnel start --tunnel production-db
```

**Start in foreground mode** (blocks terminal):
```bash
uv run ssh-tunnel start --foreground
```

**Stop all tunnels**:
```bash
uv run ssh-tunnel stop
```

**Stop a specific tunnel**:
```bash
uv run ssh-tunnel stop --tunnel production-db
```

**Restart tunnels**:
```bash
uv run ssh-tunnel restart
uv run ssh-tunnel restart --tunnel production-db
```

**View tunnel status**:
```bash
uv run ssh-tunnel status
uv run ssh-tunnel status --json  # JSON output
```

**View logs**:
```bash
uv run ssh-tunnel logs              # Last 50 lines
uv run ssh-tunnel logs --lines 100  # Last 100 lines
uv run ssh-tunnel logs --follow     # Follow logs in real-time
```

## 🔍 Usage Examples

### Example 1: Simple SSH Tunnel

```json
{
  "name": "production-db",
  "enabled": true,
  "host": "192.168.4.163",
  "port": 11050,
  "user": "username",
  "password": "your_password_here",
  "local_port": 5433,
  "remote_host": "localhost",
  "remote_port": 5433
}
```

**Note:** The `enabled` field is optional and defaults to `true`. Use `"enabled": false` to temporarily disable a tunnel without removing it from the configuration.

Then connect locally:
```bash
psql -h localhost -p 5433 -U postgres
```

### Example 2: Double Tunnel with kubectl port-forward

This example creates an SSH tunnel to the remote server and automatically executes `kubectl port-forward`:

```json
{
  "name": "k8s-postgres",
  "host": "192.168.4.163",
  "port": 11050,
  "user": "username",
  "local_port": 5432,
  "remote_host": "localhost",
  "remote_port": 5432,
  "remote_command": "kubectl port-forward postgres-8767c76bf-2gvpz 5432:5432 -n kptm-production"
}
```

**Note:** To use `kubectl` without `sudo`, you need to configure kubectl on the remote server.

**⚠️ Important:** Tunnels with `remote_command` **only work in foreground mode** because the remote command needs to stay active. Use:
```bash
uv run ssh-tunnel start --tunnel k8s-postgres --foreground
```

**Double tunnel flow:**
1. Your local machine port 5432
2. → SSH tunnel to server 192.168.4.163
3. → Executes `kubectl port-forward` on server
4. → Connects to Kubernetes pod
5. → PostgreSQL pod port 5432

Then connect from your local machine:
```bash
psql -h localhost -p 5432 -U postgres
```

### Example 3: Multiple Tunnels

```json
{
  "tunnels": [
    {
      "name": "production-db",
      "enabled": true,
      "host": "192.168.4.163",
      "port": 11050,
      "user": "username",
      "local_port": 5433,
      "remote_host": "localhost",
      "remote_port": 5433
    },
    {
      "name": "staging-api",
      "enabled": true,
      "host": "192.168.4.164",
      "port": 22,
      "user": "username",
      "local_port": 8080,
      "remote_host": "localhost",
      "remote_port": 8080,
      "remote_command": "kubectl port-forward svc/api-service 8080:80 -n production"
    },
    {
      "name": "development-redis",
      "enabled": false,
      "host": "192.168.4.165",
      "port": 22,
      "user": "username",
      "local_port": 6379,
      "remote_host": "localhost",
      "remote_port": 6379
    }
  ]
}
```

**Note:** The `development-redis` tunnel has `"enabled": false`, so it will be ignored when starting tunnels. This is useful for maintaining configurations without having to delete them.

##  Notes

- **Authentication**: You can use passwords (`password` field) or SSH keys
- If you use SSH keys, they must be previously configured (`~/.ssh/id_rsa` or similar)
- If you use passwords, you need to have `sshpass` installed
- Healthcheck runs automatically in background
- Logs are saved in `logs/tunnels.log` by default

## 🔐 Security

- **IMPORTANT**: Never share your `configs/tunnels.json` file as it contains passwords (it's in `.gitignore`)
- Passwords are stored in plain text in the configuration file
- Consider using SSH keys instead of passwords for better security
- Limit permissions on the configuration file:
  ```bash
  # Linux/macOS
  chmod 600 configs/tunnels.json
  
  # Windows (PowerShell as administrator)
  icacls configs\tunnels.json /inheritance:r /grant:r "$env:USERNAME:F"
  ```

## 📄 License

This project is for personal use.

## 🤝 Contributions

This is a personal developer tools project. Feel free to adapt it to your needs.
