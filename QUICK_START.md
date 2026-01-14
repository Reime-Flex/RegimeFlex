# RegimeFlex Quick Start - Production Deployment

## TL;DR

```bash
# 1. Create droplet, then on your laptop:
./deploy.sh YOUR_DROPLET_IP regimeflex

# 2. On droplet, configure Nginx and SSL:
sudo cp /opt/regimeflex/nginx/regimeflex.conf /etc/nginx/sites-available/regimeflex
sudo ln -s /etc/nginx/sites-available/regimeflex /etc/nginx/sites-enabled/
sudo certbot --nginx -d your-domain.com

# 3. Enable auto-start:
sudo systemctl enable regimeflex.service
```

## Full Steps

### Prerequisites
- DigitalOcean droplet (Ubuntu 22.04)
- Domain name pointing to droplet IP
- SSH access to droplet

### Step 1: Initial Setup (One Time)

```bash
# Copy setup script to droplet
scp setup-droplet.sh root@YOUR_DROPLET_IP:/tmp/

# SSH and run setup
ssh root@YOUR_DROPLET_IP
bash /tmp/setup-droplet.sh

# Configure SSH for deploy user
exit
ssh-copy-id regimeflex@YOUR_DROPLET_IP
```

### Step 2: Configure Environment

```bash
# On your laptop
cp env.example .env
nano .env  # Add your API keys
```

### Step 3: Deploy

```bash
./deploy.sh YOUR_DROPLET_IP regimeflex
```

### Step 4: Configure Nginx and SSL

```bash
ssh regimeflex@YOUR_DROPLET_IP
sudo cp /opt/regimeflex/nginx/regimeflex.conf /etc/nginx/sites-available/regimeflex
sudo nano /etc/nginx/sites-available/regimeflex  # Replace YOUR_DOMAIN
sudo ln -s /etc/nginx/sites-available/regimeflex /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com
```

### Step 5: Enable Auto-Start

```bash
sudo systemctl enable regimeflex.service
sudo systemctl start regimeflex.service
```

## Verify

```bash
# Check containers
docker-compose ps

# Check health
curl http://localhost:8080/health
curl http://localhost:3000/api/health

# Check systemd
sudo systemctl status regimeflex.service

# Visit in browser
https://your-domain.com
```

## Common Commands

```bash
# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Update
./deploy.sh DROPLET_IP regimeflex

# Rollback
./rollback.sh TIMESTAMP
```

## Troubleshooting

**Services not starting?**
```bash
docker-compose logs
docker-compose ps
```

**Health checks failing?**
```bash
curl -v http://localhost:8080/health
curl -v http://localhost:3000/api/health
```

**Nginx issues?**
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/regimeflex_error.log
```

See `DEPLOYMENT.md` for complete troubleshooting guide.

