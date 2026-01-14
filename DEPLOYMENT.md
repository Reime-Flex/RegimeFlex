# RegimeFlex Production Deployment Guide

This guide provides complete instructions for deploying RegimeFlex to a DigitalOcean droplet with zero-downtime updates, automatic restarts, health monitoring, and TLS encryption.

## Architecture Overview

- **Backend**: Python Flask API (port 8080) - Trading logic and data processing
- **Frontend**: Next.js web dashboard (port 3000) - User interface
- **Reverse Proxy**: Nginx with Let's Encrypt TLS
- **Orchestration**: Docker Compose
- **Process Management**: systemd (survives reboots)
- **Health Monitoring**: Built-in health checks at `/health` and `/api/health`

## Prerequisites

- DigitalOcean droplet (Ubuntu 22.04+ recommended)
- Domain name pointing to droplet IP (for TLS)
- SSH access to droplet
- Local machine with `rsync` and `ssh` installed

## Step 1: Initial Droplet Setup

### 1.1 Create Droplet

1. Create a new DigitalOcean droplet:
   - OS: Ubuntu 22.04 LTS
   - Plan: $12/month (2GB RAM) minimum, $24/month (4GB RAM) recommended
   - Region: Choose closest to you
   - Authentication: SSH keys (recommended)

2. Note the droplet IP address

### 1.2 Initial Server Configuration

SSH into your droplet and run the setup script:

```bash
# On your local machine, copy setup script to droplet
scp setup-droplet.sh root@YOUR_DROPLET_IP:/tmp/

# SSH into droplet
ssh root@YOUR_DROPLET_IP

# Run setup script
bash /tmp/setup-droplet.sh
```

This script installs:
- Docker and Docker Compose
- Nginx
- Certbot (for Let's Encrypt)
- Creates `regimeflex` user
- Configures firewall (UFW)
- Creates necessary directories

### 1.3 Configure SSH Key for Deploy User

```bash
# On your local machine
ssh-copy-id regimeflex@YOUR_DROPLET_IP

# Test SSH access
ssh regimeflex@YOUR_DROPLET_IP
```

## Step 2: Initial Deployment

### 2.1 Prepare Environment File

On your local machine, create `.env` file from template:

```bash
cp env.example .env
# Edit .env with your API keys
nano .env
```

**Critical variables:**
- `ALPACA_KEY` - Your Alpaca paper trading key
- `ALPACA_SECRET` - Your Alpaca paper trading secret
- `ENV=prod` - Set to production mode
- `PORT=8080` - Backend port (don't change)
- `PYTHON_BACKEND_URL=http://backend:8080` - Internal Docker network URL

### 2.2 Deploy Application

From your local machine:

```bash
./deploy.sh YOUR_DROPLET_IP regimeflex
```

This script:
1. Creates backup of existing deployment
2. Syncs code to droplet
3. Builds Docker images
4. Starts services
5. Verifies health checks

### 2.3 Verify Deployment

SSH into droplet and check status:

```bash
ssh regimeflex@YOUR_DROPLET_IP
cd /opt/regimeflex
docker-compose ps
docker-compose logs --tail=50
```

Check health endpoints:

```bash
curl http://localhost:8080/health
curl http://localhost:3000/api/health
```

Both should return `{"status": "ok"}`.

## Step 3: Configure Nginx and TLS

### 3.1 Update Nginx Configuration

Edit the Nginx config with your domain:

```bash
sudo nano /etc/nginx/sites-available/regimeflex
```

Replace `YOUR_DOMAIN` with your actual domain name in the SSL certificate paths.

### 3.2 Install Nginx Config

```bash
# Copy config
sudo cp /opt/regimeflex/nginx/regimeflex.conf /etc/nginx/sites-available/regimeflex

# Create symlink
sudo ln -s /etc/nginx/sites-available/regimeflex /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 3.3 Obtain SSL Certificate

```bash
# Replace your-domain.com with your actual domain
sudo certbot --nginx -d your-domain.com

# Certbot will:
# 1. Update Nginx config with SSL paths
# 2. Set up auto-renewal
# 3. Configure HTTP to HTTPS redirect
```

### 3.4 Verify TLS

Visit `https://your-domain.com` in a browser. You should see:
- Valid SSL certificate
- RegimeFlex dashboard
- No security warnings

## Step 4: Enable Automatic Startup

Enable systemd service to start on boot:

```bash
sudo systemctl enable regimeflex.service
sudo systemctl start regimeflex.service
sudo systemctl status regimeflex.service
```

Test reboot survival:

```bash
sudo reboot
# Wait 2 minutes, then SSH back in
ssh regimeflex@YOUR_DROPLET_IP
docker-compose ps  # Should show running containers
```

## Step 5: Ongoing Operations

### 5.1 View Logs

**All services:**
```bash
cd /opt/regimeflex
docker-compose logs -f
```

**Backend only:**
```bash
docker-compose logs -f backend
```

**Frontend only:**
```bash
docker-compose logs -f frontend
```

**Last 100 lines:**
```bash
docker-compose logs --tail=100
```

**Nginx logs:**
```bash
sudo tail -f /var/log/nginx/regimeflex_access.log
sudo tail -f /var/log/nginx/regimeflex_error.log
```

### 5.2 Update Application

From your local machine:

```bash
./deploy.sh YOUR_DROPLET_IP regimeflex
```

The deploy script automatically:
- Creates backup
- Pulls latest code (if using git)
- Rebuilds containers
- Restarts services
- Verifies health

### 5.3 Manual Restart

If you need to restart services manually:

```bash
cd /opt/regimeflex
docker-compose restart

# Or restart specific service
docker-compose restart backend
docker-compose restart frontend
```

### 5.4 Check Service Status

```bash
# Docker containers
docker-compose ps

# Systemd service
sudo systemctl status regimeflex.service

# Health checks
curl http://localhost:8080/health
curl http://localhost:3000/api/health
```

### 5.5 Rollback to Previous Version

List available backups:

```bash
ls -1t /opt/regimeflex_backups/
```

Rollback to specific backup:

```bash
cd /opt/regimeflex
./rollback.sh 20250114_120000  # Use timestamp from backup filename
```

## Step 6: Environment Variable Management

### 6.1 Update Environment Variables

**Never commit `.env` to git!**

To update environment variables:

1. Edit `.env` on your local machine
2. Redeploy: `./deploy.sh YOUR_DROPLET_IP regimeflex`

Or edit directly on droplet:

```bash
ssh regimeflex@YOUR_DROPLET_IP
cd /opt/regimeflex
nano .env
docker-compose restart
```

### 6.2 Required Environment Variables

See `env.example` for all available variables. Minimum required:

- `ALPACA_KEY` - Alpaca API key
- `ALPACA_SECRET` - Alpaca API secret
- `ENV=prod` - Production mode
- `PORT=8080` - Backend port

### 6.3 Secrets Management

For production, consider using:
- Docker secrets (for Docker Swarm)
- HashiCorp Vault
- AWS Secrets Manager
- Environment variable injection at deploy time

Current setup uses `.env` file (ensure it's not in git).

## Step 7: Monitoring and Health Checks

### 7.1 Health Endpoints

**Backend:**
- `http://localhost:8080/health` - Simple health check
- `http://localhost:8080/health-full` - Detailed diagnostics

**Frontend:**
- `http://localhost:3000/api/health` - Frontend health check

**Via Nginx (external):**
- `https://your-domain.com/health` - Backend health
- `https://your-domain.com/api/health` - Frontend health

### 7.2 Docker Health Checks

Docker automatically monitors container health:

```bash
docker-compose ps  # Shows health status
```

### 7.3 Set Up External Monitoring (Optional)

Use services like:
- UptimeRobot
- Pingdom
- StatusCake

Monitor: `https://your-domain.com/health`

## Step 8: Troubleshooting

### 8.1 Services Won't Start

```bash
# Check logs
docker-compose logs

# Check if ports are in use
sudo netstat -tulpn | grep -E ':(8080|3000)'

# Restart Docker
sudo systemctl restart docker
docker-compose up -d
```

### 8.2 Health Checks Failing

```bash
# Test endpoints directly
curl -v http://localhost:8080/health
curl -v http://localhost:3000/api/health

# Check container logs
docker-compose logs backend
docker-compose logs frontend

# Restart containers
docker-compose restart
```

### 8.3 Nginx Issues

```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/regimeflex_error.log

# Reload Nginx
sudo systemctl reload nginx
```

### 8.4 SSL Certificate Issues

```bash
# Renew certificate manually
sudo certbot renew

# Check certificate expiration
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal
```

### 8.5 Container Build Failures

```bash
# Clean build (no cache)
cd /opt/regimeflex
docker-compose build --no-cache

# Remove old images
docker system prune -a
```

### 8.6 Database/State Issues

If state files are corrupted:

```bash
# Backup current state
cp -r /opt/regimeflex/data /opt/regimeflex/data_backup

# Clear state (CAUTION: This resets trading state)
rm -rf /opt/regimeflex/data/state/*.json

# Restart services
docker-compose restart
```

### 8.7 Firewall Issues

```bash
# Check firewall status
sudo ufw status

# Allow specific ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Reload firewall
sudo ufw reload
```

### 8.8 Disk Space Issues

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a

# Clean old backups (keep last 5)
cd /opt/regimeflex_backups
ls -1t | tail -n +6 | xargs rm -f
```

## Step 9: Security Hardening

### 9.1 Firewall Configuration

UFW is configured during setup. Verify:

```bash
sudo ufw status
```

Should show:
- OpenSSH allowed
- Nginx Full (80, 443) allowed
- All other ports blocked

### 9.2 SSH Hardening

```bash
# Disable root login
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no

# Use key-based auth only
# Set: PasswordAuthentication no

sudo systemctl restart sshd
```

### 9.3 Docker Security

Containers run as non-root users where possible. Backend runs as root inside container (required for some operations), but frontend runs as `nextjs` user.

### 9.4 Regular Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
cd /opt/regimeflex
docker-compose pull
docker-compose up -d
```

## Step 10: Backup and Recovery

### 10.1 Automatic Backups

Deploy script creates backups automatically. Manual backup:

```bash
cd /opt/regimeflex
tar -czf /opt/regimeflex_backups/manual_$(date +%Y%m%d_%H%M%S).tar.gz \
    --exclude='node_modules' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='data/cache' \
    .
```

### 10.2 Backup Strategy

Recommended:
- Daily automated backups (cron job)
- Keep last 7 days
- Weekly backups kept for 4 weeks
- Monthly backups kept for 6 months

### 10.3 Restore from Backup

```bash
cd /opt/regimeflex
./rollback.sh BACKUP_TIMESTAMP
```

## Quick Reference

### Essential Commands

```bash
# Deploy
./deploy.sh DROPLET_IP regimeflex

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Status
docker-compose ps
sudo systemctl status regimeflex.service

# Health check
curl http://localhost:8080/health

# Rollback
./rollback.sh TIMESTAMP
```

### File Locations

- Application: `/opt/regimeflex`
- Backups: `/opt/regimeflex_backups`
- Logs: `docker-compose logs` or `/var/log/nginx/`
- Environment: `/opt/regimeflex/.env`
- Nginx config: `/etc/nginx/sites-available/regimeflex`
- Systemd service: `/etc/systemd/system/regimeflex.service`

### Ports

- Backend: `127.0.0.1:8080` (internal only)
- Frontend: `127.0.0.1:3000` (internal only)
- Nginx: `0.0.0.0:80, 443` (public)

## Support

For issues:
1. Check logs: `docker-compose logs`
2. Check health: `curl http://localhost:8080/health`
3. Review this guide's troubleshooting section
4. Check GitHub issues: https://github.com/Reime-Flex/RegimeFlex/issues

## Deployment Checklist

Before going live:

- [ ] Droplet created and accessible
- [ ] Initial setup script run
- [ ] SSH keys configured
- [ ] `.env` file configured with API keys
- [ ] Initial deployment successful
- [ ] Health checks passing
- [ ] Nginx configured
- [ ] SSL certificate obtained
- [ ] TLS working (HTTPS)
- [ ] systemd service enabled
- [ ] Reboot test passed
- [ ] Logs accessible
- [ ] Backup system working
- [ ] Monitoring configured (optional)
- [ ] Firewall configured
- [ ] Security hardening complete

---

**Deployment Complete!** Your RegimeFlex system is now running perpetually with automatic restarts, health monitoring, and TLS encryption.

