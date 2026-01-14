# Exact Commands to Run on DigitalOcean Droplet

This document provides the exact commands to run on your droplet. Copy and paste these commands.

## Initial Setup (Run Once as Root)

```bash
# 1. Update system
apt-get update && apt-get upgrade -y

# 2. Install Docker
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 3. Install Docker Compose (standalone)
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 4. Install Nginx
apt-get install -y nginx

# 5. Install Certbot
apt-get install -y certbot python3-certbot-nginx

# 6. Create regimeflex user
useradd -m -s /bin/bash regimeflex
usermod -aG docker regimeflex

# 7. Configure firewall
ufw --force enable
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw status

# 8. Create directories
mkdir -p /opt/regimeflex
mkdir -p /opt/regimeflex_backups
mkdir -p /var/www/certbot
chown -R regimeflex:regimeflex /opt/regimeflex
chown -R regimeflex:regimeflex /opt/regimeflex_backups

# 9. Verify installations
docker --version
docker-compose --version
nginx -v
certbot --version
```

## After First Deployment (As regimeflex User)

```bash
# Switch to regimeflex user
su - regimeflex
cd /opt/regimeflex

# 1. Install systemd service
sudo cp /opt/regimeflex/systemd/regimeflex.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable regimeflex.service
sudo systemctl start regimeflex.service

# 2. Configure Nginx
sudo cp /opt/regimeflex/nginx/regimeflex.conf /etc/nginx/sites-available/regimeflex
sudo nano /etc/nginx/sites-available/regimeflex
# Replace YOUR_DOMAIN with your actual domain name in the SSL paths

# 3. Enable Nginx site
sudo ln -s /etc/nginx/sites-available/regimeflex /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# 4. Test Nginx config
sudo nginx -t

# 5. Reload Nginx
sudo systemctl reload nginx

# 6. Get SSL certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com

# 7. Verify services
docker-compose ps
curl http://localhost:8080/health
curl http://localhost:3000/api/health
```

## Daily Operations (As regimeflex User)

```bash
cd /opt/regimeflex

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Restart services
docker-compose restart

# Check health
curl http://localhost:8080/health
curl http://localhost:3000/api/health

# View systemd status
sudo systemctl status regimeflex.service
```

## Troubleshooting Commands

```bash
cd /opt/regimeflex

# Check container logs
docker-compose logs backend
docker-compose logs frontend

# Restart specific service
docker-compose restart backend
docker-compose restart frontend

# Rebuild containers
docker-compose build --no-cache
docker-compose up -d

# Check Nginx logs
sudo tail -f /var/log/nginx/regimeflex_error.log
sudo tail -f /var/log/nginx/regimeflex_access.log

# Test Nginx config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Check firewall
sudo ufw status

# Check disk space
df -h

# Check Docker
docker ps
docker images
```

## Rollback Commands

```bash
cd /opt/regimeflex

# List backups
ls -1t /opt/regimeflex_backups/

# Rollback to specific backup
./rollback.sh 20250114_120000
```

## Verification After Reboot

```bash
# After rebooting the droplet, verify services started
ssh regimeflex@YOUR_DROPLET_IP
cd /opt/regimeflex
docker-compose ps
sudo systemctl status regimeflex.service
curl http://localhost:8080/health
```

All services should be running automatically after reboot.

