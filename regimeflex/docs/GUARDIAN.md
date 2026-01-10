# RegimeFlex Guardian Module

**Purpose:** Production-grade process management, monitoring, and alerting for the RegimeFlex trading system.

---

## Overview

The Guardian module provides four critical capabilities:

1. **Process Management** - PM2 ecosystem configuration for instant crash recovery
2. **Heartbeat Alerts** - Scheduled status messages every 4 hours
3. **Critical Error Routing** - Circuit breaker with emergency phone/SMS alerts
4. **Health Monitoring** - Watchdog timer that restarts stale processes

---

## 1. Process Management (PM2)

### Configuration: `ecosystem.config.js`

**Features:**
- ✅ Instant restart on crash (0ms delay)
- ✅ Exponential backoff disabled for immediate recovery
- ✅ Memory limit protection (1GB max)
- ✅ Separate watchdog process
- ✅ Scheduled heartbeat sender (every 4 hours)

**Usage:**
```bash
# Start all processes
pm2 start ecosystem.config.js

# Start in paper trading mode
pm2 start ecosystem.config.js --env paper

# View logs
pm2 logs regimeflex

# Check status
pm2 status

# Restart manually
pm2 restart regimeflex
```

**Processes:**
1. `regimeflex` - Main trading bot (trigger_server.py)
2. `regimeflex-watchdog` - Health monitor (watchdog_monitor.py)
3. `regimeflex-heartbeat` - Scheduled heartbeat sender (send_heartbeat.py)

---

## 2. Heartbeat Alerts

### Configuration: `config/guardian.yaml`

```yaml
heartbeat:
  enabled: true
  interval_hours: 4
  include_equity: true
  include_regime: true
  include_uptime: true
  include_last_cycle: true
```

### Features:
- ✅ Sends heartbeat every 4 hours via PM2 cron
- ✅ Includes current regime (BULL/BEAR)
- ✅ Includes account equity
- ✅ Includes process uptime
- ✅ Includes last cycle completion time

### Example Message:
```
💓 RegimeFlex Heartbeat
━━━━━━━━━━━━━━━━━━━━
🐂 Regime: BULL
💰 Equity: $50,000.00
⏱️ Uptime: 24.5h
🔄 Last Cycle: 2m ago
📅 2026-01-09 12:00 UTC
```

### Manual Trigger:
```bash
python regimeflex/scripts/send_heartbeat.py
```

---

## 3. Critical Error Routing (Circuit Breaker)

### Configuration: `config/guardian.yaml`

```yaml
circuit_breaker:
  enabled: true
  max_failures: 3              # Failures before circuit opens
  retry_delays: [1, 2, 4]      # Exponential backoff
  reset_timeout_sec: 300       # Auto-reset after 5 minutes
  emergency_on_open: true      # Send EMERGENCY alert
  
  services:
    alpaca:
      max_failures: 3
    polygon:
      max_failures: 5          # More tolerant
```

### Features:
- ✅ **Alpaca API** - Circuit breaker integrated in `exec_alpaca.py`
- ✅ **Polygon API** - Circuit breaker integrated in `data_providers.py`
- ✅ **Emergency Alerts** - Sends EMERGENCY alert when circuit opens
- ✅ **Phone/SMS** - Emergency alerts sent to phone if configured
- ✅ **Auto-Recovery** - Circuit auto-resets after timeout

### Emergency Alert Flow:
1. API fails 3+ times → Circuit opens
2. Emergency alert sent to Telegram/Discord
3. **Phone/SMS alert sent** (if configured)
4. Circuit auto-resets after 5 minutes

### Phone/SMS Configuration:

**Option 1: Twilio (Recommended)**
```bash
export TWILIO_ACCOUNT_SID="your_sid"
export TWILIO_AUTH_TOKEN="your_token"
export TWILIO_FROM_NUMBER="+1234567890"
export GUARDIAN_EMERGENCY_PHONE="+1987654321"
```

Enable in `config/guardian.yaml`:
```yaml
emergency:
  enabled: true
  phone_env: "GUARDIAN_EMERGENCY_PHONE"
```

**Option 2: Webhook (IFTTT, Zapier, etc.)**
```bash
export GUARDIAN_EMERGENCY_WEBHOOK="https://your-webhook-url"
export GUARDIAN_EMERGENCY_PHONE="+1987654321"
```

### Example Emergency Alert:
```
🚨 EMERGENCY - RegimeFlex
━━━━━━━━━━━━━━━━━━━━
Error: CIRCUIT_BREAKER_OPEN
Service: alpaca
Message: Service alpaca has failed 3 times

Trace:
[Error details...]

📅 2026-01-09 12:00:00 UTC
⚡ Immediate attention required
```

---

## 4. Health Monitoring (Watchdog)

### Configuration: `config/guardian.yaml`

```yaml
watchdog:
  enabled: true
  timeout_minutes: 10          # Max time between cycles
  heartbeat_file: ".guardian_heartbeat"
  action_on_stale: "restart"   # restart | alert_only
  check_interval_sec: 60       # Check every 60 seconds
```

### Features:
- ✅ **Heartbeat File** - Trading loop touches `.guardian_heartbeat` after each cycle
- ✅ **Staleness Detection** - Watchdog monitors heartbeat age
- ✅ **Auto-Restart** - PM2 restart triggered if stale > 10 minutes
- ✅ **Emergency Alert** - Sends EMERGENCY alert before restart

### Integration:
The trading loop automatically touches the heartbeat:
```python
# In runner.py (end of cycle)
from .guardian.watchdog import touch_heartbeat
touch_heartbeat(regime="BULL", equity=50000.0)
```

### Watchdog Monitor:
Runs as separate PM2 process (`regimeflex-watchdog`):
- Checks heartbeat every 60 seconds
- Triggers restart if stale > 10 minutes
- Sends emergency alert before restart

---

## Installation & Setup

### 1. Install PM2
```bash
npm install -g pm2
```

### 2. Install Twilio (Optional, for SMS)
```bash
pip install twilio
```

### 3. Configure Environment Variables
```bash
# Telegram (required for alerts)
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Discord (optional)
export DISCORD_WEBHOOK_URL="your_webhook_url"

# Phone/SMS (optional)
export TWILIO_ACCOUNT_SID="your_sid"
export TWILIO_AUTH_TOKEN="your_token"
export TWILIO_FROM_NUMBER="+1234567890"
export GUARDIAN_EMERGENCY_PHONE="+1987654321"

# Or use webhook
export GUARDIAN_EMERGENCY_WEBHOOK="https://your-webhook-url"
```

### 4. Enable Emergency Alerts
Edit `config/guardian.yaml`:
```yaml
emergency:
  enabled: true
  phone_env: "GUARDIAN_EMERGENCY_PHONE"
```

### 5. Start Guardian
```bash
pm2 start ecosystem.config.js
pm2 save                    # Save PM2 process list
pm2 startup                 # Enable PM2 on system boot
```

---

## Monitoring & Status

### Check PM2 Status
```bash
pm2 status
pm2 logs regimeflex
pm2 logs regimeflex-watchdog
pm2 logs regimeflex-heartbeat
```

### Check Guardian Status
```bash
python regimeflex/scripts/guardian_status.py
```

### Manual Heartbeat Test
```bash
python regimeflex/scripts/send_heartbeat.py --force
```

### Check Watchdog Health
```bash
python -c "
from regimeflex.engine.guardian.watchdog import Watchdog
wd = Watchdog('.')
print(wd.get_health_status())
"
```

---

## Architecture

```
┌─────────────────────────────────────┐
│  PM2 Process Manager                │
│  ┌───────────────────────────────┐ │
│  │ regimeflex (main bot)         │ │
│  │ - Instant restart on crash    │ │
│  │ - Memory limit protection     │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ regimeflex-watchdog           │ │
│  │ - Monitors heartbeat file     │ │
│  │ - Restarts if stale > 10min   │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ regimeflex-heartbeat (cron)   │ │
│  │ - Sends heartbeat every 4h   │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Guardian Module                     │
│  ┌───────────────────────────────┐ │
│  │ Circuit Breaker               │ │
│  │ - Alpaca API protection       │ │
│  │ - Polygon API protection     │ │
│  │ - Emergency alerts on open    │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ Alert Manager                  │ │
│  │ - Telegram alerts             │ │
│  │ - Discord alerts              │ │
│  │ - Phone/SMS emergency         │ │
│  └───────────────────────────────┘ │
│  ┌───────────────────────────────┐ │
│  │ Watchdog                      │ │
│  │ - Heartbeat monitoring        │ │
│  │ - Staleness detection         │ │
│  │ - Auto-restart                │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## Summary

✅ **Process Management** - PM2 ecosystem with instant restart  
✅ **Heartbeat Alerts** - Every 4 hours via Telegram/Discord  
✅ **Critical Error Routing** - Circuit breaker with phone/SMS alerts  
✅ **Health Monitoring** - Watchdog with auto-restart  

The Guardian module is **production-ready** and provides comprehensive protection for the RegimeFlex trading system.

