# Redis Vector Database Setup Guide

This guide explains how to use Redis Stack as the vector database for the Superlinked search & recommendations API.

## Architecture Overview

The system uses **Redis Stack** which includes:
- **Redis Server** - Core key-value store (port 6379)
- **RediSearch** - Full-text and vector similarity search
- **RedisJSON** - Native JSON document storage
- **RedisInsight UI** - Web-based management interface (port 8001)
- **RedisBloom** - Probabilistic data structures
- **RedisTimeSeries** - Time series data

### Why Redis Stack?

- **Performance**: 100+ queries/second with 30ms p95 latency
- **Persistence**: Hybrid RDB + AOF for durability
- **Scalability**: Handles millions of vectors efficiently
- **Cost**: More cost-effective than managed Postgres with pgvector for production
- **Debugging**: RedisInsight provides excellent visualization and monitoring

## Quick Start

### 1. Start Redis Stack

```bash
# Start Redis with persistent storage
./scripts/redis_manager.sh start

# Check status
./scripts/redis_manager.sh status

# Access RedisInsight UI
open http://localhost:8001
```

### 2. Configure Application

Set environment variable in `.env`:

```bash
VECTOR_DB_TYPE=redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=          # Optional, leave empty for no auth
REDIS_USERNAME=default
REDIS_DB=0
```

### 3. Start Superlinked Server

```bash
source .env
USE_TEST_DATA=1 python -m superlinked.server
```

The server will automatically use Redis as the vector database.

### 4. Load Data

```bash
# Load H&M clothing dataset (100 items test data)
curl -X POST http://localhost:8080/data-loader/hm_clothing_loader/run

# Or load Amazon grocery dataset
curl -X POST http://localhost:8080/data-loader/amazon_grocery_loader/run
```

### 5. Query Data

```bash
# Text search on H&M clothing
curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
  -H "Content-Type: application/json" \
  -d '{
    "text_search": "elegant blue dress",
    "description_weight": 1.0,
    "limit": 5
  }'
```

## Redis Management

The `scripts/redis_manager.sh` script provides convenient management commands:

### Start/Stop

```bash
./scripts/redis_manager.sh start    # Start Redis Stack
./scripts/redis_manager.sh stop     # Stop Redis Stack
./scripts/redis_manager.sh restart  # Restart Redis Stack
```

### Monitoring

```bash
./scripts/redis_manager.sh status   # Show Redis status and memory usage
./scripts/redis_manager.sh logs     # View Redis logs (follow mode)
./scripts/redis_manager.sh cli      # Access Redis CLI
```

### Backup & Restore

```bash
# Create backup
./scripts/redis_manager.sh backup

# Restore from backup
./scripts/redis_manager.sh restore backups/redis-backup-YYYYMMDD-HHMMSS.tar.gz

# Clean all data (with confirmation)
./scripts/redis_manager.sh clean
```

## Persistence Configuration

Redis is configured for production-grade persistence:

### RDB Snapshots (Point-in-time backups)

```
save 900 1     # Save after 15 min if 1+ keys changed
save 300 10    # Save after 5 min if 10+ keys changed
save 60 10000  # Save after 1 min if 10000+ keys changed
```

### AOF (Write-ahead log)

```
appendonly yes
appendfsync everysec  # Sync to disk every second (good balance)
```

### Data Location

```
data/redis/dump.rdb        # RDB snapshot file
data/redis/appendonly.aof  # AOF log file
```

## Switching Between Vector Databases

The system supports multiple vector database backends:

### InMemory (Default for development)

```bash
export VECTOR_DB_TYPE=inmemory
```

- Fastest for development and testing
- Data persists to `in_memory_vdb/` folder
- No external dependencies

### Redis (Recommended for production)

```bash
export VECTOR_DB_TYPE=redis
export REDIS_HOST=localhost
export REDIS_PORT=6379
```

- High performance (100+ QPS)
- Persistent storage
- Production-ready
- Cost-effective

### Future: PostgreSQL with pgvector

```bash
export VECTOR_DB_TYPE=postgres
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
```

- Ultra-low cost option (~$12/month)
- Good for budget-constrained deployments
- Lower performance than Redis

## RedisInsight UI

Access the web UI at http://localhost:8001

### Features

- **Browser**: Explore keys and indices
- **Workbench**: Run Redis commands interactively
- **Analysis**: Memory usage and key patterns
- **Profiler**: Monitor slow queries
- **Vector Search**: Visualize vector indices

### Common Operations

```bash
# List all indices
FT._LIST

# Get index info
FT.INFO idx_ef084eed8f75dd77

# Count keys
DBSIZE

# Check memory usage
INFO memory

# List keys by pattern
KEYS HMClothingSchema:*
```

## Performance Tuning

### Connection Pool Settings

```bash
# Increase for high-concurrency workloads
export REDIS_MAX_CONNECTIONS=100
export REDIS_SOCKET_TIMEOUT=10
export REDIS_SOCKET_CONNECT_TIMEOUT=10
```

### Memory Management

Redis is configured with `maxmemory-policy noeviction` to prevent data loss. Monitor memory usage:

```bash
docker exec superlinked-redis-stack redis-cli INFO memory
```

### Resource Limits

Docker Compose configures:
- CPU: 1 core (can burst higher)
- Memory: 2GB limit, 1GB reserved

Adjust in `docker-compose.redis.yml` if needed.

## Troubleshooting

### Redis won't start

```bash
# Check if port 6379 is already in use
sudo lsof -i :6379

# Check Docker logs
docker logs superlinked-redis-stack

# Ensure data directory exists and has correct permissions
ls -la data/redis
```

### Connection refused

```bash
# Verify Redis is running
./scripts/redis_manager.sh status

# Test connection
docker exec superlinked-redis-stack redis-cli ping
# Should return: PONG

# Check network
docker network ls
```

### Data not persisting

```bash
# Verify AOF is enabled
docker exec superlinked-redis-stack redis-cli CONFIG GET appendonly
# Should return: appendonly yes

# Force save
docker exec superlinked-redis-stack redis-cli BGSAVE

# Check persistence files
ls -lh data/redis/
```

### Out of memory

```bash
# Check memory usage
docker exec superlinked-redis-stack redis-cli INFO memory

# Options:
# 1. Increase Docker memory limit in docker-compose.redis.yml
# 2. Clean old data: ./scripts/redis_manager.sh clean
# 3. Enable eviction policy (not recommended for vectors)
```

### Slow queries

```bash
# Enable slow log
docker exec superlinked-redis-stack redis-cli CONFIG SET slowlog-log-slower-than 10000

# View slow queries
docker exec superlinked-redis-stack redis-cli SLOWLOG GET 10
```

## Production Deployment

### Security

1. **Set Redis password**:
```bash
export REDIS_PASSWORD=your_strong_password_here
```

2. **Enable TLS** (if using Redis Cloud or managed Redis):
```bash
export REDIS_TLS=true
```

3. **Firewall rules**: Only allow connections from application server

### Monitoring

Monitor these metrics:
- **used_memory_human**: Total memory usage
- **connected_clients**: Number of active connections
- **instantaneous_ops_per_sec**: Query throughput
- **keyspace_hits** vs **keyspace_misses**: Cache hit rate

### Backups

Automate backups with cron:

```bash
# Add to crontab: Daily backup at 2 AM
0 2 * * * /path/to/scripts/redis_manager.sh backup
```

### High Availability

For production, consider:
- **Redis Enterprise Cloud**: Managed, auto-failover, multi-zone replication
- **Redis Sentinel**: Self-managed high availability
- **Redis Cluster**: Horizontal scaling (if needed)

## Cost Comparison

### Self-hosted Redis Stack (this setup)

- **Cost**: ~$0/month (runs on existing server)
- **Performance**: Excellent
- **Maintenance**: Manual

### Redis Cloud (Free Tier)

- **Cost**: $0/month up to 30MB
- **Performance**: Good (with some limits)
- **Maintenance**: Fully managed

### Redis Cloud (Paid)

- **Cost**: ~$5-10/month for 100MB-1GB
- **Performance**: Excellent
- **Maintenance**: Fully managed

### Cloud SQL (PostgreSQL + pgvector)

- **Cost**: ~$12/month (db-f1-micro)
- **Performance**: Moderate
- **Maintenance**: Managed database, self-managed extensions

## Configuration Reference

See `.env.example` for all configuration options:

```bash
# Vector Database Type
VECTOR_DB_TYPE=redis|inmemory|postgres

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_USERNAME=default
REDIS_DB=0

# Connection Pool
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5
REDIS_SOCKET_CONNECT_TIMEOUT=5

# Data Loading
USE_TEST_DATA=0|1  # 1 for 1k rows, 0 for full dataset
```

## Next Steps

- [Deployment Guide](development_plan.md) - Deploy to GCP
- [Configuration Reference](superlinked_config.md) - All config.yaml options
- [API Documentation](../README.md) - API endpoints and examples
