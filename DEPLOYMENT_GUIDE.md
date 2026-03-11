# Honasa Task Force - Production Deployment Guide

## Overview
This guide covers deploying Honasa Task Force on AWS (or any Docker-compatible environment).

## Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    AWS / Cloud Provider                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Frontend  │  │   Backend   │  │    MongoDB      │ │
│  │   (Nginx)   │──│  (FastAPI)  │──│  (Persistent)   │ │
│  │   Port 80   │  │  Port 8001  │  │   Port 27017    │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│                         │                               │
│                    ┌────┴────┐                          │
│                    │   GCS   │  (Optional)              │
│                    │ Storage │                          │
│                    └─────────┘                          │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites
- Docker & Docker Compose installed
- AWS account (for EC2/ECS deployment)
- Domain name (optional, for HTTPS)
- GCS bucket & credentials (optional, for cloud storage)

## Quick Start (Local Docker)

1. **Clone and configure:**
```bash
cd /path/to/honasa-task-force

# Create .env file
cp .env.example .env
# Edit .env with your values
```

2. **Build and start:**
```bash
docker-compose up -d --build
```

3. **Access the app:**
- Frontend: http://localhost
- API: http://localhost/api

## Environment Variables

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `MONGO_URL` | MongoDB connection string | `mongodb://mongodb:27017` |
| `DB_NAME` | Database name | `honasa_taskforce` |
| `REACT_APP_BACKEND_URL` | Public URL for frontend | `https://yourdomain.com` |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `*` |
| `GCS_BUCKET` | GCS bucket name for file storage | (empty = local) |
| `GCS_CREDENTIALS_PATH` | Path to GCS service account JSON | (empty) |
| `MAX_CONCURRENT_AGENTS` | Max simultaneous agent executions | `10` |
| `RESEND_API_KEY` | Resend API key for email notifications | (empty) |
| `SENDER_EMAIL` | Email sender address | `onboarding@resend.dev` |

## AWS Deployment Options

### Option 1: EC2 with Docker Compose (Recommended for small-medium)

1. **Launch EC2 instance:**
   - AMI: Amazon Linux 2023 or Ubuntu 22.04
   - Instance type: t3.medium (minimum)
   - Storage: 30GB+ EBS
   - Security group: Allow ports 80, 443, 22

2. **Install Docker:**
```bash
# Amazon Linux 2023
sudo dnf install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

3. **Deploy application:**
```bash
# Clone repository
git clone <your-repo> /opt/honasa-taskforce
cd /opt/honasa-taskforce

# Create .env
cat > .env << EOF
MONGO_URL=mongodb://mongodb:27017
DB_NAME=honasa_taskforce
REACT_APP_BACKEND_URL=http://YOUR_EC2_PUBLIC_IP
MAX_CONCURRENT_AGENTS=10
EOF

# Start services
docker-compose up -d --build
```

### Option 2: AWS ECS (Fargate)

1. **Create ECR repositories:**
```bash
aws ecr create-repository --repository-name honasa-backend
aws ecr create-repository --repository-name honasa-frontend
```

2. **Build and push images:**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -f Dockerfile.backend -t honasa-backend .
docker tag honasa-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/honasa-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/honasa-backend:latest

docker build -f Dockerfile.frontend --build-arg REACT_APP_BACKEND_URL=https://yourdomain.com -t honasa-frontend .
docker tag honasa-frontend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/honasa-frontend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/honasa-frontend:latest
```

3. **Create ECS task definitions and services via AWS Console or Terraform**

## GCS Storage Setup (Optional)

For production, use GCS for file storage instead of local volumes:

1. **Create GCS bucket:**
```bash
gsutil mb -p YOUR_PROJECT gs://honasa-taskforce-files
```

2. **Create service account:**
```bash
gcloud iam service-accounts create honasa-storage \
    --display-name="Honasa Storage Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT \
    --member="serviceAccount:honasa-storage@YOUR_PROJECT.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud iam service-accounts keys create gcs-credentials.json \
    --iam-account=honasa-storage@YOUR_PROJECT.iam.gserviceaccount.com
```

3. **Configure environment:**
```bash
GCS_BUCKET=honasa-taskforce-files
GCS_CREDENTIALS_PATH=/app/credentials/gcs-credentials.json
```

4. **Mount credentials in docker-compose:**
```yaml
backend:
  volumes:
    - ./gcs-credentials.json:/app/credentials/gcs-credentials.json:ro
```

## HTTPS Setup (Recommended)

### Using Caddy (Easiest)

Create `Caddyfile`:
```
yourdomain.com {
    reverse_proxy frontend:80
}
```

Add to docker-compose.yml:
```yaml
caddy:
  image: caddy:2
  restart: unless-stopped
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile
    - caddy_data:/data
```

### Using AWS ALB + ACM
1. Create ACM certificate
2. Create ALB with HTTPS listener
3. Point ALB to EC2/ECS targets

## MongoDB Setup (Production)

For production, use MongoDB Atlas or a dedicated MongoDB server:

1. **MongoDB Atlas:**
   - Create cluster at mongodb.com
   - Get connection string
   - Update `MONGO_URL` in .env

2. **Self-hosted MongoDB:**
   - Separate EC2 instance for MongoDB
   - Enable authentication
   - Regular backups

## Health Checks

- Backend: `GET /api/` - Returns `{"message": "Honasa Task Force API"}`
- Queue status: `GET /api/queue/status` - Returns active/queued jobs

## Monitoring

Add logging and monitoring:
```yaml
backend:
  logging:
    driver: "awslogs"
    options:
      awslogs-group: "honasa-backend"
      awslogs-region: "us-east-1"
```

## Scaling

### Horizontal Scaling
- Use multiple backend containers behind a load balancer
- Ensure MongoDB is properly replicated
- Use shared GCS storage for files

### Queue Management
- `MAX_CONCURRENT_AGENTS=10` limits concurrent executions
- Excess jobs are queued automatically
- Monitor queue via `/api/queue/status`

## Troubleshooting

### Container won't start
```bash
docker-compose logs backend
docker-compose logs frontend
```

### MongoDB connection issues
```bash
docker exec -it honasa-mongodb mongosh --eval "db.adminCommand('ping')"
```

### File download issues
- Ensure `uploads_data` and `outputs_data` volumes are properly mounted
- Check GCS credentials if using cloud storage

## Security Checklist

- [ ] Change default MongoDB credentials
- [ ] Enable HTTPS
- [ ] Set specific CORS origins (not `*`)
- [ ] Use secrets manager for sensitive env vars
- [ ] Enable CloudWatch/logging
- [ ] Regular security updates
- [ ] Set up backup strategy for MongoDB

## Support

For issues or questions, contact the development team.
