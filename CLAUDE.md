# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Superlinked-based search & recommendations API** designed for e-commerce SaaS customers. It provides a production-ready setup for building performant and scalable search and recommendation systems. The project should be branded as "search_rec_api" and does not publicly emphasize Superlinked as the underlying framework.

**Target Stack:**
- Python 3.12
- FastAPI (via Superlinked server)
- Superlinked framework for vector search
- Google Cloud Platform for hosting
- BigQuery for analytics
- Redis for caching
- Postgres for data storage
- Pulumi for infrastructure as code

The team is small and prefers managed services and SaaS solutions within free tiers, primarily in the EU region.

## Development Commands

### Environment Setup
```bash
# Install dependencies (using uv)
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Running the Server
```bash
# Start the Superlinked server with config.yaml
python -m superlinked.server

# The server will:
# - Load configuration from config.yaml
# - Load app code from superlinked_app/ (specified in config.yaml's app_module_path)
# - Start on port 8080 (default)
```

### Testing
```bash
# Run tests
pytest

# Run specific test file
pytest tests/test_specific.py
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint
ruff check .

# Type checking
mypy .

# Security scanning
bandit -r superlinked_app/
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Architecture

### Core Application Structure

The application follows Superlinked's modular architecture:

1. **`superlinked_app/index.py`**: Defines the schema, spaces, and indices
   - `YourSchema`: Schema definition with fields (item_id, attribute)
   - `text_space`: TextSimilaritySpace using sentence-transformers model
   - `index`: Index combining the text space

2. **`superlinked_app/query.py`**: Defines query logic
   - `query`: Query definition for similarity search
   - Uses parameters for dynamic query text

3. **`superlinked_app/api.py`**: Application entry point
   - `your_source`: REST data source for ingestion
   - `your_query`: REST query endpoint
   - `executor`: Orchestrates sources, indices, and queries
   - Registers executor with SuperlinkedRegistry

### Configuration System

Configuration is managed via `config.yaml` (see `docs/superlinked_config.md` for complete parameter reference):

**Key sections:**
- `framework.app_module_path`: Points to Python module (e.g., `superlinked_app.api`)
- `framework.disable_recency_space`: Must be `false` if using RecencySpace
- `api.api_keys`: List of API keys for authentication
- `api.allowed_origins`: CORS origins
- `model.embedding_model`: Note - this is NOT used by Superlinked; models are specified in code
- `resource.max_workers`: Worker process count

**Important:** The server is maintained by Superlinked. Configuration happens through `config.yaml`, not by modifying server code.

### Vector Database

The default setup uses `InMemoryVectorDatabase()` (see `superlinked_app/api.py:13`). For production:
- Use Redis via configuration
- Or use PostgreSQL with pgvector extension (recommended for cost optimization)

### Data Flow

1. **Ingestion**: POST to REST source endpoint → Schema validation → Embedding generation → Index storage
2. **Query**: POST to query endpoint → Parameter substitution → Vector similarity search → Filtered results
3. **Persistence**: In-memory VDB persists to `in_memory_vdb/` folder

## Important Implementation Notes

### Embedding Models
**Embedding models are specified in application code, not in config.yaml.** See `superlinked_app/index.py:11-12`:
```python
model_name = "sentence-transformers/all-MiniLM-L6-v2"
text_space = sl.TextSimilaritySpace(text=your_schema.attribute, model=model_name)
```

### API Authentication
- Only single API key supported via config (or multiple keys via list in config.yaml)
- Must be sent in `Authorization` header
- For multi-tenant scenarios, implement custom authentication logic

### CORS Configuration
No built-in CORS in Superlinked settings. Configure via `api.allowed_origins` in config.yaml.

## Deployment Architecture

See `docs/development_plan.md` for complete GCP deployment guide. Key points:

**Ultra-Budget Strategy (~$12-41/month):**
- Cloud SQL (db-f1-micro) for PostgreSQL with pgvector
- Cloud Run for serverless API hosting
- BigQuery for analytics (free tier: 10GB + 1TB queries)
- Looker Studio for dashboards (free)
- Secret Manager for API keys
- No Redis unless needed (use in-memory + PostgreSQL)

**Cost Optimization:**
- Use `europe-west?` region (cheapest)
- Set strict budget alerts
- Implement caching layers (in-memory, database query cache)
- Use partitioned BigQuery tables
- Minimal Cloud Run instances (512Mi RAM, 1 CPU, min-instances=0)

**Scaling Indicators:**
- >80% CPU consistently
- Response times >2s
- Database connection pool exhaustion

## Configuration Files

- **`config.yaml`**: Main server configuration (see docs/superlinked_config.md for all parameters)
- **`pyproject.toml`**: Python dependencies and project metadata
- **`uv.lock`**: Dependency lockfile (managed by uv)
- **`.python-version`**: Python version (3.12)

## Key Documentation

- **`docs/development_plan.md`**: Complete GCP deployment guide with cost optimization
- **`docs/superlinked_config.md`**: Comprehensive config.yaml parameter reference
- **`README.md`**: Project overview and quick start

## Working with Superlinked

When modifying the application:

1. **Schema changes**: Modify `superlinked_app/index.py` → Update `YourSchema`
2. **New spaces**: Add spaces in `index.py` → Combine in Index
3. **Query changes**: Modify `superlinked_app/query.py` → Add parameters, filters
4. **New endpoints**: Add sources/queries in `api.py` → Register with executor
5. **Configuration**: Update `config.yaml` → Restart server

**Do not modify the Superlinked server code itself** - it's a third-party package maintained by Superlinked.