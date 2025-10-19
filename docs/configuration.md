# Configuration System

This document describes the configuration system for the search_rec_api project, which uses Dynaconf with GCP Secret Manager integration for secure secret management.

## Overview

The configuration system uses **Dynaconf** as the configuration management framework with multiple configuration sources and environment-based settings. In production, secrets are automatically loaded from **GCP Secret Manager** via a custom Dynaconf hook.

## Configuration Sources (Priority Order)

Configuration is loaded from multiple sources in this priority order (later sources override earlier ones):

1. **Default values** in `settings.toml` (`[default]` section)
2. **Environment-specific settings** in `settings.toml` (`[development]` or `[production]`)
3. **Local overrides** from `.secrets.toml` (git-ignored, for local development)
4. **Environment variables** (prefix: `SEARCHREC__`)
5. **GCP Secret Manager** (production only, via Dynaconf hook)

## File Structure

```
superlinked_app/config/
├── __init__.py          # Re-exports settings from config.py
├── config.py            # Dynaconf initialization with GCP hook
├── settings.toml        # Main configuration file (committed to git)
└── .secrets.toml        # Local overrides (git-ignored, create if needed)
```

## Configuration Files

### settings.toml

Main configuration file with three sections:

- `[default]` - Base configuration inherited by all environments
- `[development]` - Development environment overrides
- `[production]` - Production environment overrides

**Example:**
```toml
[default]
pandas_chunksize = 10
vector_db_type = "inmemory"

[development]
use_test_data = true
log_level = "DEBUG"

[production]
use_test_data = false
log_level = "WARNING"
gcp_project_id = "your-gcp-project-id"
```

### .secrets.toml (Optional, Local Only)

Local override file for development secrets. **Never commit this file to git.**

**Example:**
```toml
[development]
api_key = "my-local-dev-key"
redis_password = "my-local-redis-password"
```

## Environment Variables

All settings can be overridden via environment variables with the `SEARCHREC__` prefix:

```bash
# Switch environment
export ENV_FOR_DYNACONF=production

# Override specific settings
export SEARCHREC__VECTOR_DB_TYPE=redis
export SEARCHREC__REDIS_HOST=10.0.0.1
export SEARCHREC__API_KEY=your_api_key
export SEARCHREC__USE_TEST_DATA=false
```

## GCP Secret Manager Integration

In production (`ENV_FOR_DYNACONF=production`), secrets are automatically loaded from GCP Secret Manager via the `load_gcp_secrets()` Dynaconf hook.

### Required GCP Secrets

Create these secrets in GCP Secret Manager:

1. **api-key**: API authentication key for Superlinked server
   ```bash
   echo -n "your-secret-api-key" | gcloud secrets create api-key \
       --data-file=- \
       --project=your-gcp-project-id
   ```

2. **redis-password**: Redis authentication password (if using Redis)
   ```bash
   echo -n "your-redis-password" | gcloud secrets create redis-password \
       --data-file=- \
       --project=your-gcp-project-id
   ```

### Secret Format

Secrets are accessed using the path:
```
projects/{project_id}/secrets/{secret_name}/versions/latest
```

### How It Works

1. When `ENV_FOR_DYNACONF=production`, the `load_gcp_secrets()` hook runs automatically
2. It creates a GCP Secret Manager client
3. Fetches secrets from `projects/{gcp_project_id}/secrets/{name}/versions/latest`
4. Sets the secrets in Dynaconf settings
5. Also sets environment variables for Superlinked compatibility:
   - `SERVER__API_KEY` (for Superlinked authentication)
   - `REDIS_PASSWORD` (for Redis connection)

## Configuration Parameters

### Data Loading

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pandas_chunksize` | int | 10 | Chunk size for Pandas DataLoader |
| `use_test_data` | bool | false | Use test datasets (1k rows) instead of full datasets |

### Server

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `server_port` | int | 8080 | Server port (informational, Superlinked uses config.yaml) |
| `log_level` | str | "INFO" | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### Vector Database

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `vector_db_type` | str | "inmemory" | Vector database type (inmemory, redis) |

### Redis Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `redis_host` | str | "localhost" | Redis server hostname |
| `redis_port` | int | 6379 | Redis server port |
| `redis_password` | str | "" | Redis password (loaded from GCP in production) |
| `redis_username` | str | "default" | Redis username |
| `redis_db` | int | 0 | Redis database number |
| `redis_max_connections` | int | 50 | Maximum connections in pool |
| `redis_socket_timeout` | int | 5 | Socket timeout in seconds |
| `redis_socket_connect_timeout` | int | 5 | Socket connect timeout in seconds |

### Authentication

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | str | "" | API authentication key (loaded from GCP in production) |

### GCP Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gcp_project_id` | str | "" | GCP project ID (required in production) |

## Usage in Code

### Importing Settings

```python
from superlinked_app.config import settings

# Access settings
if settings.use_test_data:
    data_file = "data/test.parquet"
else:
    data_file = "data/full.parquet"

# Vector database configuration
db_type = settings.vector_db_type
redis_host = settings.redis_host
```

### Environment-Aware Configuration

```python
import os

# Check current environment
env = os.getenv("ENV_FOR_DYNACONF", "development")

if env == "production":
    # Production-specific logic
    # Secrets are automatically loaded from GCP
    pass
```

## Development Workflow

### Local Development

1. Set environment to development (default):
   ```bash
   export ENV_FOR_DYNACONF=development
   ```

2. (Optional) Create `.secrets.toml` for local overrides:
   ```bash
   cat > superlinked_app/config/.secrets.toml <<EOF
   [development]
   api_key = "my-local-key"
   EOF
   ```

3. Run the server:
   ```bash
   python -m superlinked.server
   ```

### Production Deployment

1. Set environment to production:
   ```bash
   export ENV_FOR_DYNACONF=production
   ```

2. Ensure GCP project ID is set in `settings.toml`:
   ```toml
   [production]
   gcp_project_id = "your-gcp-project-id"
   ```

3. Ensure GCP secrets exist:
   ```bash
   gcloud secrets list --project=your-gcp-project-id
   ```

4. Run the server (secrets loaded automatically):
   ```bash
   python -m superlinked.server
   ```

## Superlinked Integration

The application configuration is separate from Superlinked's `config.yaml`. However, some settings bridge both systems:

### API Key

- **Application setting**: `settings.api_key` (loaded from GCP in production)
- **Superlinked setting**: `SERVER__API_KEY` environment variable
- **How it works**: The GCP hook sets both `settings.api_key` and `os.environ["SERVER__API_KEY"]`

### Redis Password

- **Application setting**: `settings.redis_password` (loaded from GCP in production)
- **How it works**: The GCP hook sets both `settings.redis_password` and `os.environ["REDIS_PASSWORD"]`

### Data Loading

- **Application setting**: `settings.use_test_data`
- **Old system**: `USE_TEST_DATA` environment variable
- **Migration**: All code now uses `settings.use_test_data`

## Security Best Practices

1. **Never commit secrets to git**
   - `.secrets.toml` is git-ignored
   - `.env` files are git-ignored
   - Use GCP Secret Manager for production

2. **Use environment-specific secrets**
   - Development: Local `.secrets.toml` or environment variables
   - Production: GCP Secret Manager

3. **Rotate secrets regularly**
   - Update secrets in GCP Secret Manager
   - Restart application to load new secrets

4. **Limit secret access**
   - Use GCP IAM to restrict Secret Manager access
   - Follow principle of least privilege

## Troubleshooting

### Secrets Not Loading in Production

**Problem**: Settings show empty values for `api_key` or `redis_password`

**Solution**:
1. Verify environment is set: `echo $ENV_FOR_DYNACONF`
2. Check GCP project ID in settings: `settings.gcp_project_id`
3. Verify secrets exist in GCP:
   ```bash
   gcloud secrets list --project=your-project-id
   ```
4. Check IAM permissions for Secret Manager
5. Review logs for GCP Secret Manager errors

### Environment Not Switching

**Problem**: Settings from wrong environment are loaded

**Solution**:
```bash
# Unset any conflicting variables
unset ENV_FOR_DYNACONF

# Set explicitly
export ENV_FOR_DYNACONF=production

# Verify
python -c "from superlinked_app.config import settings; print(settings.current_env)"
```

### Settings Not Updating

**Problem**: Changed settings in `settings.toml` but no effect

**Solution**:
1. Restart the application (Dynaconf loads on import)
2. Check if environment variable is overriding:
   ```bash
   env | grep SEARCHREC__
   ```
3. Clear any cached `.pyc` files:
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} +
   ```

## Migration from Environment Variables

The old system used direct environment variables (`VECTOR_DB_TYPE`, `USE_TEST_DATA`, etc.). The new system uses Dynaconf settings.

### Migration Checklist

- [x] Replace `os.getenv("USE_TEST_DATA")` with `settings.use_test_data`
- [x] Replace `os.getenv("VECTOR_DB_TYPE")` with `settings.vector_db_type`
- [x] Replace Redis env vars with `settings.redis_*`
- [x] Remove `.env` file (configuration now in `settings.toml`)
- [x] Add `.secrets.toml` to `.gitignore`
- [x] Update documentation

### Backward Compatibility

Environment variables with the `SEARCHREC__` prefix still work and override `settings.toml`:

```bash
# Old way (still works)
export VECTOR_DB_TYPE=redis

# New way (preferred)
export SEARCHREC__VECTOR_DB_TYPE=redis
```

## References

- [Dynaconf Documentation](https://www.dynaconf.com/)
- [GCP Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Superlinked Configuration](./superlinked_config.md)
