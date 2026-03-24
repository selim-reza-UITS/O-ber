# O-ber Backend — Production Deployment Guide

> **Domain**: `api.rydeislands.com` (API) / `rydeislands.com` (Admin Dashboard)
> **VPS**: `187.124.229.129`

---

## 1. Initial VPS Setup (One-Time)

SSH into your VPS and install prerequisites:

```bash
ssh root@187.124.229.129

# Install Docker & Docker Compose v2
apt update && apt upgrade -y
apt install -y docker.io docker-compose-v2 git ufw certbot python3-certbot-nginx

# Enable firewall — allow SSH, HTTP, HTTPS only
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Clone the repository
git clone https://github.com/<your-username>/O-ber.git /var/www/O-ber
cd /var/www/O-ber
```

## 2. Environment Configuration

Copy your `.env.production` to the VPS as `.env`:

```bash
# On your LOCAL machine — securely copy the file
scp .env.production root@187.124.229.129:/var/www/O-ber/.env
```

**⚠️ Before deploying, you MUST update these values in `.env`:**

| Variable | Action |
|---|---|
| `DJANGO_SECRET_KEY` | Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `POSTGRES_PASSWORD` | Replace with a strong random password |
| `STRIPE_SECRET_KEY` | Your live Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Your Stripe webhook signing secret |
| `EMAIL_HOST_USER` | Your SMTP email (e.g. `admin@rydeislands.com`) |
| `EMAIL_HOST_PASSWORD` | Your SMTP email password |

**Port Configuration (non-default for security):**

- PostgreSQL: internal port `5444`, exposed externally on `5431`
- Redis: internal port `6388`, exposed externally on `6378`
- Backend (Daphne): internal `8000`, exposed on `9500`
- Nginx: port `80` / `443`

## 3. SSL Setup with Certbot

After the first deploy (so Nginx is running on port 80):

```bash
# Point your DNS A records for api.rydeislands.com and rydeislands.com to 187.124.229.129

# Install Nginx on the HOST for SSL termination (proxies to Docker Nginx on port 80)
apt install -y nginx

# Create host Nginx config
cat > /etc/nginx/sites-available/rydeislands << 'EOF'
server {
    listen 80;
    server_name api.rydeislands.com rydeislands.com www.rydeislands.com;

    location / {
        proxy_pass http://127.0.0.1:9500;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 20M;
    }

    location /static/ {
        alias /var/www/O-ber/static/;
    }

    location /media/ {
        alias /var/www/O-ber/media/;
    }
}
EOF

ln -sf /etc/nginx/sites-available/rydeislands /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Get SSL certificates
certbot --nginx -d api.rydeislands.com -d rydeislands.com -d www.rydeislands.com

# Auto-renewal is set up automatically by certbot
```

## 4. First Deploy

```bash
cd /var/www/O-ber

# Build and start all containers
docker compose up -d --build

# Verify all containers are running
docker compose ps

# Create an admin superuser
docker compose exec backend python manage.py createsuperuser
```

## 5. GitHub CI/CD Pipeline

The `.github/workflows/deploy.yml` auto-deploys on every push to `main`.

### Required GitHub Secrets

Go to **GitHub Repo → Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `VPS_IP` | `187.124.229.129` |
| `VPS_USER` | `root` (or your deploy user) |
| `VPS_SSH_KEY` | Private SSH key (matching `~/.ssh/authorized_keys` on VPS) |

### How it works

1. You push code to `main`
2. GitHub Actions SSHs into the VPS
3. Pulls latest code, rebuilds Docker containers
4. `entrypoint.sh` automatically runs migrations and collectstatic
5. Health check verifies the deployment succeeded

## 6. Local Development (Flutter & React)

`django-cors-headers` is installed with `CORS_ALLOW_ALL_ORIGINS = True`, so your local development apps can freely hit the API:

- **Flutter app**: Point API base URL to `https://api.rydeislands.com/api/v1/`
- **React admin dashboard**: Set `REACT_APP_API_URL=https://api.rydeislands.com/api/v1/`

WebSocket connections (for riders) are also supported through the Nginx proxy config.

## 7. Useful Commands

```bash
# View logs
docker compose logs -f backend
docker compose logs -f worker

# Run migrations manually
docker compose exec backend python manage.py migrate

# Restart a single service
docker compose restart backend

# Full rebuild (after major changes)
docker compose down && docker compose up -d --build

# Check disk usage
docker system df
```

## 8. Monitoring & Maintenance

```bash
# Check container health
docker compose ps

# Backup the database
docker compose exec db pg_dump -U ober_db_admin ober_prod_db > backup_$(date +%Y%m%d).sql

# Prune old Docker images (free disk space)
docker image prune -af
```
