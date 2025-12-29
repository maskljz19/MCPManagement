# Docker Deployment Guide

## Overview

This guide provides instructions for deploying the MCP Platform Backend using Docker and Docker Compose. The deployment includes all necessary services: API, Celery workers, databases, and message broker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB of available RAM
- At least 10GB of available disk space

## Quick Start

### 1. Environment Configuration

Copy the appropriate environment file for your deployment:

```bash
# For Docker Compose deployment
cp .env.docker .env

# For local development
cp .env.development .env
```

Edit `.env` and update the following critical values:

```bash
# Security - MUST CHANGE IN PRODUCTION!
SECRET_KEY=your-secure-secret-key-min-32-characters-long
MYSQL_PASSWORD=your-secure-mysql-password
RABBITMQ_PASSWORD=your-secure-rabbitmq-password

# External Services
OPENAI_API_KEY=sk-your-openai-api-key
GITHUB_TOKEN=ghp_your-github-token
```

### 2. Build and Start Services

```bash
# Build all images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Verify Deployment

Check that all services are healthy:

```bash
docker-compose ps
```

All services should show status as "Up" and "healthy".

Test the API health endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "checks": {
    "mysql": true,
    "mongodb": true,
    "redis": true,
    "qdrant": true,
    "rabbitmq": true
  }
}
```

### 4. Run Database Migrations

```bash
docker-compose exec api alembic upgrade head
```

## Architecture

### Services

The deployment includes the following services:

1. **api** - FastAPI application (port 8000)
   - Handles HTTP requests
   - Provides REST API endpoints
   - Serves WebSocket connections

2. **worker** - Celery worker (2 replicas)
   - Processes background tasks
   - Handles AI analysis
   - Manages GitHub synchronization

3. **beat** - Celery beat scheduler
   - Schedules periodic tasks
   - Manages task scheduling

4. **mysql** - MySQL 8.0 database (port 3306)
   - Stores structured data
   - Manages users, tools, deployments

5. **mongodb** - MongoDB 7.0 (port 27017)
   - Stores document data
   - Manages version history

6. **redis** - Redis 7.2 (port 6379)
   - Caching layer
   - Session management
   - Task result storage

7. **qdrant** - Qdrant vector database (port 6333)
   - Stores document embeddings
   - Enables semantic search

8. **rabbitmq** - RabbitMQ 3.12 (ports 5672, 15672)
   - Message broker for Celery
   - Management UI at http://localhost:15672

### Network

All services communicate through a dedicated Docker network (`mcp-network`).

### Volumes

Persistent data is stored in Docker volumes:

- `mysql_data` - MySQL database files
- `mongodb_data` - MongoDB database files
- `redis_data` - Redis persistence files
- `qdrant_data` - Qdrant vector storage
- `rabbitmq_data` - RabbitMQ data

## Configuration

### Environment Variables

See `.env.example` for a complete list of configuration options with detailed documentation.

Key configuration categories:

- **Application**: Basic app settings
- **Databases**: Connection strings for MySQL, MongoDB, Redis, Qdrant
- **Message Broker**: RabbitMQ configuration
- **Security**: JWT settings, secret keys
- **External Services**: OpenAI, GitHub API keys
- **CORS**: Cross-origin resource sharing settings
- **Logging**: Log level and format

### Port Mappings

Default port mappings (can be changed in `.env`):

- `8000` - API server
- `3306` - MySQL
- `27017` - MongoDB
- `6379` - Redis
- `6333` - Qdrant HTTP API
- `6334` - Qdrant gRPC API
- `5672` - RabbitMQ AMQP
- `15672` - RabbitMQ Management UI

## Scaling

### Horizontal Scaling

Scale API instances:

```bash
docker-compose up -d --scale api=3
```

Scale Celery workers:

```bash
docker-compose up -d --scale worker=4
```

### Resource Limits

Add resource limits in `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## Monitoring

### Health Checks

All services include health checks that run automatically:

- **API**: HTTP check on `/health` endpoint
- **MySQL**: `mysqladmin ping`
- **MongoDB**: `mongosh` ping command
- **Redis**: `redis-cli ping`
- **Qdrant**: HTTP check on `/health` endpoint
- **RabbitMQ**: `rabbitmq-diagnostics ping`
- **Worker**: Celery inspect ping

### Logs

View logs for all services:

```bash
docker-compose logs -f
```

View logs for specific service:

```bash
docker-compose logs -f api
docker-compose logs -f worker
```

### RabbitMQ Management UI

Access the RabbitMQ management interface at http://localhost:15672

Default credentials (change in production):
- Username: `guest`
- Password: `guest`

## Maintenance

### Backup

Backup all data volumes:

```bash
# Stop services
docker-compose stop

# Backup volumes
docker run --rm -v mcp-mysql_data:/data -v $(pwd):/backup alpine tar czf /backup/mysql-backup.tar.gz /data
docker run --rm -v mcp-mongodb_data:/data -v $(pwd):/backup alpine tar czf /backup/mongodb-backup.tar.gz /data

# Restart services
docker-compose start
```

### Restore

Restore from backup:

```bash
# Stop services
docker-compose stop

# Restore volumes
docker run --rm -v mcp-mysql_data:/data -v $(pwd):/backup alpine tar xzf /backup/mysql-backup.tar.gz -C /

# Restart services
docker-compose start
```

### Updates

Update to latest version:

```bash
# Pull latest code
git pull

# Rebuild images
docker-compose build

# Restart services
docker-compose up -d
```

### Database Migrations

Run migrations after updates:

```bash
docker-compose exec api alembic upgrade head
```

Rollback migrations:

```bash
docker-compose exec api alembic downgrade -1
```

## Troubleshooting

### Service Won't Start

Check service logs:

```bash
docker-compose logs <service-name>
```

Check service health:

```bash
docker-compose ps
```

### Database Connection Issues

Verify database is running and healthy:

```bash
docker-compose ps mysql
docker-compose logs mysql
```

Test connection from API container:

```bash
docker-compose exec api ping mysql
```

### Out of Memory

Check container memory usage:

```bash
docker stats
```

Increase Docker memory limit in Docker Desktop settings or add resource limits to services.

### Port Conflicts

If ports are already in use, change them in `.env`:

```bash
MYSQL_PORT=3307
REDIS_PORT=6380
```

## Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Generate secure SECRET_KEY (32+ characters)
- [ ] Use strong database passwords
- [ ] Configure CORS_ORIGINS to specific domains
- [ ] Enable rate limiting
- [ ] Use HTTPS/TLS for external access
- [ ] Restrict RabbitMQ management UI access
- [ ] Review and restrict exposed ports
- [ ] Enable firewall rules
- [ ] Set up log aggregation
- [ ] Configure monitoring and alerts
- [ ] Disable DEBUG mode (DEBUG=false)
- [ ] Use production-grade database instances
- [ ] Implement database connection pooling
- [ ] Configure proper backup retention policies
- [ ] Set up SSL/TLS certificates
- [ ] Enable audit logging
- [ ] Implement intrusion detection
- [ ] Configure DDoS protection

### Recommended Production Setup

1. **Reverse Proxy with SSL/TLS**
   - Use nginx or Traefik for SSL termination
   - Configure HTTP/2 for better performance
   - Enable HSTS headers
   - Set up automatic certificate renewal (Let's Encrypt)

2. **Log Aggregation**
   - ELK Stack (Elasticsearch, Logstash, Kibana)
   - Loki + Grafana
   - CloudWatch Logs (AWS)
   - Stackdriver (GCP)

3. **Monitoring and Alerting**
   - Prometheus + Grafana for metrics
   - AlertManager for notifications
   - Uptime monitoring (UptimeRobot, Pingdom)
   - APM tools (New Relic, DataDog)

4. **Database Management**
   - Use managed database services (AWS RDS, Azure Database, GCP Cloud SQL)
   - Configure automated backups with point-in-time recovery
   - Set up read replicas for scaling
   - Enable encryption at rest and in transit

5. **Automated Backups**
   - Daily database backups
   - Weekly full system backups
   - Off-site backup storage
   - Regular backup restoration tests

6. **CI/CD Pipeline**
   - Automated testing on pull requests
   - Automated deployments to staging
   - Manual approval for production
   - Rollback capabilities

7. **Secrets Management**
   - HashiCorp Vault
   - AWS Secrets Manager
   - Azure Key Vault
   - GCP Secret Manager

8. **Auto-scaling**
   - Kubernetes for container orchestration
   - AWS ECS/EKS with auto-scaling groups
   - Azure Container Instances
   - GCP Cloud Run

### Environment-Specific Configurations

Use different environment files:

- `.env.development` - Local development
- `.env.staging` - Staging environment
- `.env.production` - Production environment

### Production Nginx Configuration

Example nginx configuration for production:

```nginx
upstream mcp_api {
    least_conn;
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://mcp_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://mcp_api/health;
        access_log off;
    }
}
```

### Kubernetes Deployment

For Kubernetes deployments, see the `k8s/` directory for manifests:

```bash
# Apply configurations
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/mysql.yaml
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/qdrant.yaml
kubectl apply -f k8s/rabbitmq.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get pods -n mcp-platform
kubectl get services -n mcp-platform

# View logs
kubectl logs -f deployment/mcp-api -n mcp-platform
```

### Cloud Provider Deployments

#### AWS Deployment

1. **ECS with Fargate**
   - Use AWS ECS for container orchestration
   - Deploy API and workers as separate services
   - Use Application Load Balancer for traffic distribution
   - Use RDS for MySQL, DocumentDB for MongoDB
   - Use ElastiCache for Redis
   - Use Amazon MQ for RabbitMQ

2. **Infrastructure as Code**
   ```bash
   # Using Terraform
   cd terraform/aws
   terraform init
   terraform plan
   terraform apply
   ```

#### Azure Deployment

1. **Azure Container Instances**
   - Deploy containers to ACI
   - Use Azure Database for MySQL
   - Use Cosmos DB for MongoDB
   - Use Azure Cache for Redis
   - Use Azure Service Bus for messaging

2. **Infrastructure as Code**
   ```bash
   # Using Terraform
   cd terraform/azure
   terraform init
   terraform plan
   terraform apply
   ```

#### GCP Deployment

1. **Cloud Run**
   - Deploy API as Cloud Run service
   - Use Cloud SQL for MySQL
   - Use Firestore for document storage
   - Use Memorystore for Redis
   - Use Cloud Tasks for async processing

2. **Infrastructure as Code**
   ```bash
   # Using Terraform
   cd terraform/gcp
   terraform init
   terraform plan
   terraform apply
   ```

### Performance Optimization

1. **Database Optimization**
   - Add indexes for frequently queried fields
   - Use connection pooling (SQLAlchemy pool_size=20)
   - Enable query caching
   - Optimize slow queries

2. **Caching Strategy**
   - Cache frequently accessed data
   - Set appropriate TTL values
   - Use cache warming for critical data
   - Implement cache invalidation strategies

3. **API Performance**
   - Enable gzip compression
   - Use CDN for static assets
   - Implement request batching
   - Use async/await for I/O operations

4. **Worker Optimization**
   - Adjust worker concurrency based on load
   - Use task priorities for critical operations
   - Implement task result expiration
   - Monitor task queue length

### Disaster Recovery

1. **Backup Strategy**
   - Automated daily backups
   - Backup retention: 30 days
   - Off-site backup storage
   - Encrypted backups

2. **Recovery Procedures**
   ```bash
   # Restore from backup
   docker-compose down
   ./scripts/restore-backup.sh backup-2024-01-15.tar.gz
   docker-compose up -d
   docker-compose exec api alembic upgrade head
   ```

3. **High Availability**
   - Multi-region deployment
   - Database replication
   - Load balancer health checks
   - Automatic failover

### Compliance and Security

1. **Data Protection**
   - Encrypt data at rest
   - Encrypt data in transit (TLS 1.2+)
   - Implement data retention policies
   - Regular security audits

2. **Access Control**
   - Role-based access control (RBAC)
   - Multi-factor authentication (MFA)
   - API key rotation policies
   - Audit logging for all access

3. **Compliance**
   - GDPR compliance for EU users
   - SOC 2 compliance
   - HIPAA compliance (if handling health data)
   - Regular penetration testing

## Support

For issues and questions:

1. Check the logs: `docker-compose logs -f`
2. Verify health checks: `docker-compose ps`
3. Review configuration: Check `.env` file
4. Consult documentation: See README.md

## License

See LICENSE file for details.
