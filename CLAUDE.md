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
   - `ProductSchema`: Schema definition with fields (item_id, description, price)
   - `description_space`: TextSimilaritySpace using sentence-transformers/all-MiniLM-L6-v2 model
   - `price_space`: NumberSpace for price-based similarity (Mode.SIMILAR)
   - `index`: Index combining description and price spaces

2. **`superlinked_app/query.py`**: Defines query logic
   - `query`: Query definition for similarity search
   - Uses parameters: query_text, query_price, description_weight, price_weight, limit

3. **`superlinked_app/api.py`**: Application entry point
   - `product_source`: REST data source for manual ingestion
   - `data_loader_source`: DataLoaderSource for bulk ingestion from Parquet
   - `product_query`: REST query endpoint for product search
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

The default setup uses `InMemoryVectorDatabase()` (see `superlinked_app/api.py`). For production:
- Use Redis via configuration
- Or use PostgreSQL with pgvector extension (recommended for cost optimization)

### Data Source

The application uses Amazon product data with two loading methods:

1. **DataLoaderSource** (bulk ingestion from Parquet):
   - Test mode: `USE_TEST_DATA=1` loads `data/processed_products_1k.parquet`
   - Production mode: loads `data/processed_products.parquet`
   - Note: DataLoaderSource must be triggered manually, it does not auto-load on startup

2. **RestSource** (manual ingestion via API):
   - POST to `/api/v1/ingest/product_schema` with JSON payload
   - Fields: item_id, description, price

### Data Preprocessing

Raw data is preprocessed using `scripts/preprocess_amazon_data.py`:
- Input: `amazon_data/student_resource/dataset/train.csv` (75k products)
- Download dataset: https://www.kaggle.com/datasets/raghavdharwal/amazon-ml-challenge-2025
- Output: `data/processed_products.parquet` (batched with row groups)
- Images: Downloaded to `data/images/` (file paths stored in Parquet)

### Data Flow

1. **Ingestion**: POST to REST source endpoint → Schema validation → Embedding generation → Index storage
2. **Query**: POST to query endpoint → Parameter substitution → Vector similarity search → Filtered results
3. **Persistence**: In-memory VDB persists to `in_memory_vdb/` folder

## Important Implementation Notes

### Embedding Models
**Embedding models are specified in application code, not in config.yaml.** See `superlinked_app/index.py:13-18`:
```python
model_name = "sentence-transformers/all-MiniLM-L6-v2"
description_space = sl.TextSimilaritySpace(
    text=product_schema.description,
    model=model_name
)
```

### Number Space for Price
The price field uses NumberSpace with `Mode.SIMILAR` to find products at similar price points:
```python
price_space = sl.NumberSpace(
    number=product_schema.price,
    min_value=0.0,
    max_value=10000.0,
    mode=sl.Mode.SIMILAR  # Must use enum, not string
)
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

1. **Schema changes**: Modify `superlinked_app/index.py` → Update `ProductSchema`
2. **New spaces**: Add spaces in `index.py` → Combine in Index
3. **Query changes**: Modify `superlinked_app/query.py` → Add parameters, filters
4. **New endpoints**: Add sources/queries in `api.py` → Register with executor
5. **Configuration**: Update `config.yaml` → Restart server

**Do not modify the Superlinked server code itself** - it's a third-party package maintained by Superlinked.

## Current Dataset Schema

The application currently uses Amazon product data with the following schema:

**ProductSchema fields:**
- `item_id` (IdField): Unique product identifier
- `description` (String): Concatenated product information (name, bullet points, value, unit)
- `price` (Float): Product price in dollars

**API Endpoints:**
- Ingest: `POST /api/v1/ingest/product_schema`
- Search: `POST /api/v1/search/product_search`

**Query parameters:**
- `query_text`: Search query for description matching
- `query_price`: Target price for similarity
- `description_weight`: Weight for text similarity (default: 1.0)
- `price_weight`: Weight for price similarity (default: 0.3)
- `limit`: Maximum results to return