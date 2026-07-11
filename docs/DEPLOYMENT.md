# Deployment Guide

This guide provides detailed instructions for deploying the RAG Platform to various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Local Deployment](#local-deployment)
- [Docker Deployment](#docker-deployment)
- [Render Deployment](#render-deployment)
- [Production Checklist](#production-checklist)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **PostgreSQL**: 15 or higher (for production)
- **Redis**: 7 or higher (for Celery)
- **Docker**: 20.10 or higher (for containerized deployment)
- **Docker Compose**: 2.0 or higher
- **Git**: For version control

### Required Accounts

- **GitHub**: For code repository and CI/CD
- **Docker Hub** (optional): For container registry
- **Render** (optional): For cloud deployment

## Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/rag-platform.git
cd rag-platform
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Application Settings
APP_NAME=RAG Platform
APP_VERSION=1.0.0
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database Settings
DATABASE_URL=postgresql://user:password@localhost:5432/rag_platform

# AI/ML Settings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
CHUNK_SIZE=512
CHUNK_OVERLAP=50
MAX_RESULTS=10
RERANK_TOP_K=5

# Vector Store Settings
VECTOR_STORE_PATH=./data/vector_stores
FAISS_INDEX_TYPE=flat

# Redis Settings
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# File Upload Settings
UPLOAD_DIR=./data/uploads
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=.pdf

# Logging Settings
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log

# CORS Settings
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 3. Generate Secure Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use the generated value for `SECRET_KEY`.

## Local Deployment

### Option 1: Direct Python Installation

1. **Create Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Download NLTK Data**

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('wordnet'); nltk.download('stopwords')"
```

4. **Initialize Database**

```bash
python -c "from app.database.connection import init_db; init_db()"
```

5. **Run the Application**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

6. **Run Celery Worker** (in separate terminal)

```bash
celery -A app.services.background_tasks worker --loglevel=info
```

7. **Run Celery Beat** (in separate terminal)

```bash
celery -A app.services.background_tasks beat --loglevel=info
```

### Option 2: Docker Compose

1. **Build and Start Services**

```bash
docker-compose up -d
```

2. **View Logs**

```bash
docker-compose logs -f
```

3. **Stop Services**

```bash
docker-compose down
```

## Docker Deployment

### Build Docker Image

```bash
docker build -t rag-platform:latest .
```

### Run Container

```bash
docker run -d \
  --name rag-platform \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@host:5432/rag_platform \
  -e REDIS_URL=redis://host:6379/0 \
  -e SECRET_KEY=your-secret-key \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  rag-platform:latest
```

### Docker Compose Production

1. **Create Production Compose File**

```bash
cp docker-compose.yml docker-compose.prod.yml
```

2. **Modify for Production**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: always

  api:
    image: rag-platform:latest
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    restart: always

  celery_worker:
    image: rag-platform:latest
    command: celery -A app.services.background_tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    restart: always

volumes:
  postgres_data:
  redis_data:
```

3. **Deploy**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Render Deployment

### Prerequisites

- Render account
- GitHub repository with the code
- Render API key

### Step 1: Prepare Repository

1. **Push code to GitHub**

```bash
git add .
git commit -m "Initial deployment setup"
git push origin main
```

2. **Ensure `.env.example` is in repository**

### Step 2: Create PostgreSQL Database

1. Go to Render Dashboard
2. Click "New" → "PostgreSQL"
3. Configure:
   - Name: `rag-platform-db`
   - Database: `rag_platform`
   - User: `rag_user`
4. Click "Create Database"
5. Copy the internal database URL

### Step 3: Create Redis Instance

1. Go to Render Dashboard
2. Click "New" → "Redis"
3. Configure:
   - Name: `rag-platform-redis`
4. Click "Create Redis"
5. Copy the internal Redis URL

### Step 4: Create Web Service

1. Go to Render Dashboard
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:

**Build & Deploy**
- Runtime: Docker
- Docker Context: `.`
- Dockerfile Path: `Dockerfile`

**Environment Variables**
```
DATABASE_URL=<your-postgres-url>
REDIS_URL=<your-redis-url>
CELERY_BROKER_URL=<your-redis-url>
CELERY_RESULT_BACKEND=<your-redis-url>
SECRET_KEY=<your-secret-key>
DEBUG=False
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-app-url.onrender.com
```

**Advanced**
- Health Check Path: `/health`
- Instance Type: Free (for testing) or Standard (for production)

5. Click "Create Web Service"

### Step 5: Create Celery Worker Service

1. Create another Web Service
2. Same configuration as API service
3. Override Command:
```
celery -A app.services.background_tasks worker --loglevel=info
```

### Step 6: Configure Domain (Optional)

1. Go to your web service settings
2. Add custom domain
3. Update DNS records
4. Update `CORS_ORIGINS` environment variable

### Step 7: Monitor Deployment

1. View logs in Render Dashboard
2. Check health status
3. Monitor resource usage

## Production Checklist

### Security

- [ ] Change default `SECRET_KEY`
- [ ] Enable HTTPS
- [ ] Configure strong database passwords
- [ ] Set up Redis password
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Set up backup strategy
- [ ] Configure log aggregation
- [ ] Enable audit logging
- [ ] Review CORS settings

### Performance

- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure connection pooling
- [ ] Enable database query caching
- [ ] Set up Redis for caching
- [ ] Configure CDN for static assets
- [ ] Optimize FAISS index type
- [ ] Enable gzip compression
- [ ] Configure worker concurrency
- [ ] Set up load balancing
- [ ] Monitor resource usage

### Reliability

- [ ] Configure health checks
- [ ] Set up auto-restart policies
- [ ] Configure database replication
- [ ] Set up Redis clustering
- [ ] Implement retry logic
- [ ] Configure graceful shutdown
- [ ] Set up monitoring alerts
- [ ] Configure log rotation
- [ ] Test disaster recovery
- [ ] Document rollback procedures

### Scalability

- [ ] Configure horizontal scaling
- [ ] Set up auto-scaling
- [ ] Optimize database queries
- [ ] Implement caching strategy
- [ ] Configure CDN
- [ ] Optimize asset delivery
- [ ] Set up queue monitoring
- [ ] Configure worker scaling
- [ ] Plan capacity requirements
- [ ] Test load handling

### Monitoring

- [ ] Set up application monitoring
- [ ] Configure error tracking (Sentry)
- [ ] Set up performance monitoring
- [ ] Configure log aggregation
- [ ] Set up uptime monitoring
- [ ] Configure alerting
- [ ] Set up dashboards
- [ ] Monitor API response times
- [ ] Track error rates
- [ ] Monitor resource usage

## Monitoring and Maintenance

### Health Checks

**Application Health**

```bash
curl https://your-domain.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "RAG Platform",
  "version": "1.0.0"
}
```

**Database Health**

```bash
docker exec -it rag_postgres pg_isready -U postgres
```

**Redis Health**

```bash
docker exec -it rag_redis redis-cli ping
```

### Log Monitoring

**View Application Logs**

```bash
# Docker
docker-compose logs -f api

# Direct
tail -f logs/app.log
```

**View Error Logs**

```bash
tail -f logs/app_error.log
```

### Celery Monitoring

**Access Flower**

Navigate to `http://your-domain.com:5555`

**Check Worker Status**

```bash
celery -A app.services.background_tasks inspect active
```

**Check Task Queue**

```bash
celery -A app.services.background_tasks inspect reserved
```

### Database Maintenance

**Backup Database**

```bash
docker exec rag_postgres pg_dump -U postgres rag_platform > backup.sql
```

**Restore Database**

```bash
docker exec -i rag_postgres psql -U postgres rag_platform < backup.sql
```

**Vacuum Database**

```bash
docker exec -it rag_postgres psql -U postgres -d rag_platform -c "VACUUM ANALYZE;"
```

### Storage Management

**Clean Old Logs**

```bash
find logs/ -name "*.log" -mtime +30 -delete
```

**Clean Old Uploads**

```bash
find data/uploads/ -type f -mtime +90 -delete
```

**Monitor Storage Usage**

```bash
du -sh data/
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Symptoms**: Application fails to start, database connection errors

**Solutions**:
- Verify database is running
- Check connection string
- Ensure database credentials are correct
- Check network connectivity
- Verify database exists

```bash
# Test database connection
psql $DATABASE_URL
```

#### 2. Redis Connection Failed

**Symptoms**: Celery tasks not processing, Redis connection errors

**Solutions**:
- Verify Redis is running
- Check Redis URL
- Ensure Redis is accessible
- Check Redis password

```bash
# Test Redis connection
redis-cli -h localhost -p 6379 ping
```

#### 3. PDF Processing Fails

**Symptoms**: Documents stuck in processing state

**Solutions**:
- Check Celery worker is running
- Verify file permissions
- Check disk space
- Review worker logs
- Restart Celery worker

```bash
# Check Celery worker status
celery -A app.services.background_tasks inspect active
```

#### 4. Memory Issues

**Symptoms**: Out of memory errors, slow performance

**Solutions**:
- Reduce `CHUNK_SIZE`
- Process documents in batches
- Increase system memory
- Optimize vector index type
- Clear unused data

#### 5. Slow Search Performance

**Symptoms**: Search queries take long time

**Solutions**:
- Use appropriate FAISS index type (IVF/HNSW)
- Reduce `MAX_RESULTS`
- Enable result caching
- Optimize embedding model
- Consider GPU acceleration

#### 6. Authentication Failures

**Symptoms**: Login fails, token validation errors

**Solutions**:
- Verify `SECRET_KEY` is consistent
- Check token expiration
- Verify user is active
- Check system time synchronization
- Review authentication logs

### Debug Mode

Enable debug mode for detailed error messages:

```bash
DEBUG=True
LOG_LEVEL=DEBUG
```

### Log Analysis

**Search for Errors**

```bash
grep ERROR logs/app.log
```

**Search for Warnings**

```bash
grep WARNING logs/app.log
```

**View Recent Logs**

```bash
tail -n 100 logs/app.log
```

## Backup and Recovery

### Automated Backups

**Database Backup Script**

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DATABASE_URL="postgresql://user:pass@host/db"

mkdir -p $BACKUP_DIR

pg_dump $DATABASE_URL > $BACKUP_DIR/backup_$DATE.sql

# Keep last 7 days of backups
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

**Schedule with Cron**

```bash
0 2 * * * /path/to/backup.sh
```

### Disaster Recovery

1. **Restore from Backup**

```bash
psql $DATABASE_URL < backup_YYYYMMDD_HHMMSS.sql
```

2. **Restore Vector Stores**

```bash
# Copy backup vector stores to data/vector_stores/
cp -r /backups/vector_stores/* data/vector_stores/
```

3. **Restore Uploads**

```bash
# Copy backup uploads to data/uploads/
cp -r /backups/uploads/* data/uploads/
```

## Performance Optimization

### Database Optimization

**Add Indexes**

```sql
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
```

**Connection Pooling**

```python
# In app/database/connection.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
```

### Caching Strategy

**Redis Caching**

```python
import redis
from functools import wraps

r = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(ttl=3600):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = f"{f.__name__}:{str(args)}:{str(kwargs)}"
            cached = r.get(key)
            if cached:
                return json.loads(cached)
            result = f(*args, **kwargs)
            r.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

## Security Hardening

### Firewall Configuration

```bash
# Allow only necessary ports
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

### SSL/TLS Configuration

**Using Let's Encrypt**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Rate Limiting

**Implement with Redis**

```python
from fastapi import HTTPException, Request
import redis

r = redis.Redis(host='localhost', port=6379, db=0)

async def rate_limit(request: Request, limit: int = 100, window: int = 60):
    client_id = request.client.host
    key = f"rate_limit:{client_id}"
    
    current = r.incr(key)
    if current == 1:
        r.expire(key, window)
    
    if current > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

## Support

For deployment issues:
- Check the logs
- Review this guide
- Open a GitHub issue
- Contact support team
