# RegimeFlex Deployment Guide

## Production Deployment Overview

This guide covers deploying RegimeFlex in production environments with real broker integration, comprehensive monitoring, and operational safety.

## Prerequisites

### System Requirements

- **Python**: 3.12+ (recommended: 3.12.0)
- **Memory**: 4GB+ RAM (8GB+ recommended)
- **Storage**: 10GB+ available space
- **Network**: Stable internet connection for API calls
- **OS**: Linux (Ubuntu 20.04+), macOS (12+), or Windows (10+)

### Required Accounts

1. **Alpaca Markets**: Trading account (paper and live)
2. **Polygon.io**: Market data provider (optional)
3. **Telegram**: Bot for notifications (optional)

## Installation

### 1. System Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install python3.12 python3.12-venv python3.12-pip

# Create application user
sudo useradd -m -s /bin/bash regimeflex
sudo usermod -aG sudo regimeflex
```

### 2. Application Deployment

```bash
# Switch to application user
sudo su - regimeflex

# Clone repository
git clone <repository-url> /home/regimeflex/regimeflex
cd /home/regimeflex/regimeflex

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuration Setup

```bash
# Create environment file
cp config/env.example .env

# Set secure permissions
chmod 600 .env

# Edit environment variables
nano .env
```

**Environment Variables** (`.env`):
```bash
# Alpaca Markets API
ALPACA_KEY=your_alpaca_key_here
ALPACA_SECRET=your_alpaca_secret_here

# Polygon.io API (optional)
POLYGON_KEY=your_polygon_key_here

# Telegram Notifications (optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 4. Directory Structure Setup

```bash
# Create required directories
mkdir -p data/cache
mkdir -p logs/audit
mkdir -p reports
mkdir -p config

# Set proper permissions
chmod 755 data logs reports
chmod 700 config
chmod 600 .env
```

## Configuration

### 1. Broker Configuration

**File**: `config/broker.yaml`
```yaml
alpaca:
  enabled: true
  mode: "paper"        # Start with paper trading
  dry_run: true       # Master safety switch
```

**Production Settings**:
```yaml
alpaca:
  enabled: true
  mode: "live"        # Live trading (after testing)
  dry_run: false      # Disable dry-run for live trading
```

### 2. Data Configuration

**File**: `config/data.yaml`
```yaml
provider: "cache"     # Start with cache-only
symbols: ["QQQ", "PSQ"]
lookback_days: 800
force_refresh: false

# Live data providers
polygon:
  base_url: "https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{from}/{to}"

alpaca:
  base_url: "https://data.alpaca.markets/v2/stocks/{symbol}/bars"
```

### 3. Risk Configuration

**File**: `config/risk.yaml`
```yaml
position_sizing:
  risk_budget: 0.02
  max_position_pct: 0.25
  atr_multiplier: 2.0

circuit_breakers:
  vix_hard_block: 35.0
  vix_caution: 25.0
  realized_vol_block: 0.05
  fomc_blackout: true
  opex_caution: true
```

### 4. Run Configuration

**File**: `config/run.yaml`
```yaml
equity: 25000.0
vix_assumption: 20.0
minutes_to_close: 28
min_trade_value: 200.0

report:
  enabled: true
  out_dir: "reports"
  filename_prefix: "daily_report"
  include_positions: true
  include_intents: true
  include_breadcrumbs: true
```

## Security Configuration

### 1. API Key Security

```bash
# Secure environment file
chmod 600 .env
chown regimeflex:regimeflex .env

# Verify permissions
ls -la .env
# Should show: -rw------- 1 regimeflex regimeflex
```

### 2. Kill-Switch Setup

```bash
# Create kill-switch file (initially disabled)
touch config/kill_switch.flag

# Test kill-switch
python scripts/kill_switch.py
# Should show: Kill-switch ENABLED

# Disable for normal operation
python scripts/kill_switch.py
# Should show: Kill-switch DISABLED
```

### 3. Firewall Configuration

```bash
# Allow outbound HTTPS for API calls
sudo ufw allow out 443
sudo ufw allow out 80

# Block inbound connections (if needed)
sudo ufw deny in
```

## Production Deployment

### 1. Systemd Service

**File**: `/etc/systemd/system/regimeflex.service`
```ini
[Unit]
Description=RegimeFlex Trading System
After=network.target

[Service]
Type=simple
User=regimeflex
Group=regimeflex
WorkingDirectory=/home/regimeflex/regimeflex
Environment=PATH=/home/regimeflex/regimeflex/.venv/bin
ExecStart=/home/regimeflex/regimeflex/.venv/bin/python scripts/run_offline_from_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Service Management

```bash
# Enable service
sudo systemctl enable regimeflex

# Start service
sudo systemctl start regimeflex

# Check status
sudo systemctl status regimeflex

# View logs
sudo journalctl -u regimeflex -f
```

### 3. Cron Scheduling

**File**: `/etc/cron.d/regimeflex`
```bash
# Daily trading run at 3:30 PM ET (market close)
30 20 * * 1-5 regimeflex cd /home/regimeflex/regimeflex && /home/regimeflex/regimeflex/.venv/bin/python scripts/run_offline_from_config.py

# Data refresh at 6:00 AM ET (market open)
0 11 * * 1-5 regimeflex cd /home/regimeflex/regimeflex && /home/regimeflex/regimeflex/.venv/bin/python scripts/fetch_live_to_cache.py
```

## Monitoring and Alerting

### 1. Log Monitoring

```bash
# Monitor system logs
sudo journalctl -u regimeflex -f

# Monitor application logs
tail -f logs/audit/ledger_*.jsonl

# Monitor reports
ls -la reports/
```

### 2. Health Checks

**File**: `scripts/health_check.py`
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from engine.identity import RegimeFlexIdentity as RF
from engine.killswitch import is_killed
from engine.config import Config
from engine.env import load_env

def health_check():
    # Check kill-switch status
    if is_killed():
        RF.print_log("Kill-switch is ACTIVE", "RISK")
        return False
    
    # Check configuration
    try:
        cfg = Config(".")
        RF.print_log("Configuration loaded successfully", "SUCCESS")
    except Exception as e:
        RF.print_log(f"Configuration error: {e}", "ERROR")
        return False
    
    # Check environment
    try:
        env = load_env()
        RF.print_log("Environment loaded successfully", "SUCCESS")
    except Exception as e:
        RF.print_log(f"Environment error: {e}", "ERROR")
        return False
    
    # Check data cache
    cache_dir = Path("data/cache")
    if not cache_dir.exists():
        RF.print_log("Data cache directory missing", "ERROR")
        return False
    
    RF.print_log("Health check passed", "SUCCESS")
    return True

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)
```

### 3. Alerting Configuration

**File**: `config/telemetry.yaml`
```yaml
enabled: true
verbosity: "brief"  # brief | full
telegram:
  enabled: true
  chat_id: "your_chat_id"
  bot_token: "your_bot_token"
```

## Backup and Recovery

### 1. Data Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/regimeflex/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup data cache
tar -czf $BACKUP_DIR/data_cache_$DATE.tar.gz data/cache/

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

# Backup reports
tar -czf $BACKUP_DIR/reports_$DATE.tar.gz reports/

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz config/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh
```

### 2. Automated Backups

```bash
# Add to crontab
crontab -e

# Add backup job (daily at 2 AM)
0 2 * * * /home/regimeflex/regimeflex/backup.sh
```

### 3. Recovery Procedures

```bash
# Restore from backup
tar -xzf /home/regimeflex/backups/data_cache_20240101_020000.tar.gz
tar -xzf /home/regimeflex/backups/logs_20240101_020000.tar.gz
tar -xzf /home/regimeflex/backups/reports_20240101_020000.tar.gz
tar -xzf /home/regimeflex/backups/config_20240101_020000.tar.gz
```

## Security Hardening

### 1. User Permissions

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash regimeflex
sudo usermod -aG sudo regimeflex

# Set up SSH key authentication
sudo mkdir -p /home/regimeflex/.ssh
sudo chmod 700 /home/regimeflex/.ssh
sudo chown regimeflex:regimeflex /home/regimeflex/.ssh
```

### 2. File Permissions

```bash
# Secure configuration files
chmod 600 .env
chmod 600 config/*.yaml
chmod 600 config/kill_switch.flag

# Secure data directories
chmod 755 data logs reports
chmod 700 config
```

### 3. Network Security

```bash
# Configure firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow out 443  # HTTPS for API calls
sudo ufw allow out 80   # HTTP for API calls
sudo ufw deny in
```

## Performance Optimization

### 1. System Resources

```bash
# Monitor system resources
htop
iostat -x 1
df -h
```

### 2. Application Optimization

```bash
# Monitor Python performance
python -m cProfile scripts/run_offline_from_config.py

# Monitor memory usage
python -m memory_profiler scripts/run_offline_from_config.py
```

### 3. Database Optimization

```bash
# Optimize data cache
python -c "
import pandas as pd
from pathlib import Path

# Compress CSV files
for csv_file in Path('data/cache').glob('*.csv'):
    df = pd.read_csv(csv_file)
    df.to_csv(csv_file, compression='gzip')
"
```

## Troubleshooting

### 1. Common Issues

**Issue**: API key errors
```bash
# Check environment variables
source .env
echo $ALPACA_KEY
echo $ALPACA_SECRET
```

**Issue**: Permission errors
```bash
# Fix file permissions
chmod 600 .env
chmod 755 data logs reports
chmod 700 config
```

**Issue**: Service not starting
```bash
# Check service status
sudo systemctl status regimeflex
sudo journalctl -u regimeflex -f
```

### 2. Debug Mode

```bash
# Run with debug output
python -u scripts/run_offline_from_config.py 2>&1 | tee debug.log
```

### 3. Log Analysis

```bash
# Analyze audit logs
python -c "
import json
from pathlib import Path

# Count transaction types
counts = {}
for log_file in Path('logs/audit').glob('*.jsonl'):
    with open(log_file) as f:
        for line in f:
            data = json.loads(line)
            kind = data.get('kind', 'unknown')
            counts[kind] = counts.get(kind, 0) + 1

print('Transaction counts:', counts)
"
```

## Maintenance

### 1. Regular Maintenance

```bash
# Weekly maintenance script
cat > maintenance.sh << 'EOF'
#!/bin/bash

# Clean old logs (keep 30 days)
find logs/ -name "*.jsonl" -mtime +30 -delete

# Clean old reports (keep 7 days)
find reports/ -name "*.html" -mtime +7 -delete

# Update data cache
python scripts/fetch_live_to_cache.py

# Run health check
python scripts/health_check.py

echo "Maintenance completed: $(date)"
EOF

chmod +x maintenance.sh
```

### 2. System Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
pip install --upgrade pip
pip install --upgrade -r requirements.txt
```

### 3. Configuration Updates

```bash
# Backup configuration before changes
cp config/broker.yaml config/broker.yaml.backup

# Test configuration changes
python -c "from engine.config import Config; Config('.')"

# Apply changes if test passes
mv config/broker.yaml.backup config/broker.yaml
```

## Disaster Recovery

### 1. Emergency Procedures

```bash
# Emergency kill-switch activation
python scripts/kill_switch.py

# Verify kill-switch is active
python -c "from engine.killswitch import is_killed; print('Killed:', is_killed())"
```

### 2. System Recovery

```bash
# Restore from backup
tar -xzf /home/regimeflex/backups/data_cache_latest.tar.gz
tar -xzf /home/regimeflex/backups/logs_latest.tar.gz
tar -xzf /home/regimeflex/backups/config_latest.tar.gz

# Restart service
sudo systemctl restart regimeflex
```

### 3. Data Recovery

```bash
# Rebuild data cache
python scripts/fetch_live_to_cache.py

# Verify data integrity
python -c "
from engine.data import get_daily_bars
qqq = get_daily_bars('QQQ')
print(f'QQQ data: {len(qqq)} rows')
print(f'Latest date: {qqq.index[-1]}')
"
```

---

**RegimeFlex Deployment Guide v29** - Production deployment with comprehensive monitoring, security, and operational procedures.

*Deployed with confidence, monitored with precision, secured with diligence.*
