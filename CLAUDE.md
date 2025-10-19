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

**With InMemory vector database (default)**:
```bash
python -m superlinked.server
```

**With Redis vector database**:
```bash
# Start Redis Stack first
./scripts/redis_manager.sh start

# Set environment and start server
ENV_FOR_DYNACONF=development python -m superlinked.server
```

The server will:
- Load Superlinked configuration from config.yaml
- Load application configuration from superlinked_app/config/settings.toml
- Load app code from superlinked_app/ (specified in config.yaml's app_module_path)
- Initialize vector database based on settings (Dynaconf)
- Start on port 8080 (default)

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

The project uses a **dual configuration system**:

1. **Superlinked Server Configuration** (`config.yaml`)
   - Framework-level settings
   - See `docs/superlinked_config.md` for complete reference
   - Key sections: `framework`, `resource`

2. **Application Configuration** (Dynaconf with GCP Secret Manager)
   - Application-level settings in `superlinked_app/config/settings.toml`
   - Environment-based configuration (development, production)
   - GCP Secret Manager integration for production secrets
   - See `docs/configuration.md` for complete guide

**Key Superlinked config.yaml sections:**
- `framework.app_module_path`: Points to Python module (e.g., `superlinked_app.api`)
- `framework.disable_recency_space`: Must be `false` if using RecencySpace
- `resource.max_workers`: Worker process count

**Key Application settings (Dynaconf):**
- `vector_db_type`: inmemory or redis
- `use_test_data`: Use test datasets (1k rows) vs full datasets
- `redis_*`: Redis connection settings
- `api_key`: API authentication (loaded from GCP Secret Manager in production)
- `gcp_project_id`: GCP project for Secret Manager

**Environment Switching:**
```bash
# Development (default)
ENV_FOR_DYNACONF=development python -m superlinked.server

# Production (loads secrets from GCP)
ENV_FOR_DYNACONF=production python -m superlinked.server
```

**Important:**
- Superlinked server is a third-party package - configure via `config.yaml`, don't modify server code
- Application settings use Dynaconf - see `docs/configuration.md` for details

### Vector Database

The application supports multiple vector database backends (configured via environment variables):

**InMemory (Default for development)**:
- Uses `InMemoryVectorDatabase()` (see `superlinked_app/api.py`)
- Data persists to `in_memory_vdb/` folder
- Fast for development and testing
- Set `VECTOR_DB_TYPE=inmemory`

**Redis Stack (Recommended for production)**:
- Uses `RedisVectorDatabase()` with RediSearch
- High performance (100+ QPS, 30ms p95 latency)
- Persistent storage with RDB + AOF
- Includes RedisInsight UI for monitoring (http://localhost:8001)
- Set `VECTOR_DB_TYPE=redis` and configure `REDIS_HOST`, `REDIS_PORT`, etc.
- See `docs/redis_setup.md` for complete setup guide
- Manage with `./scripts/redis_manager.sh` (start, stop, backup, restore)

**PostgreSQL with pgvector (Future option)**:
- Low cost (~$12/month for Cloud SQL db-f1-micro)
- Good for budget-constrained deployments
- Lower performance than Redis
- Set `VECTOR_DB_TYPE=postgres` (when implemented)

**Configuration**: Vector database is configured via Dynaconf settings (`superlinked_app/config/settings.toml`) and `superlinked_app/vector_db.py` factory function.

### Data Sources

The application currently supports multiple datasets with separate schemas and indices:

#### Amazon Grocery Dataset (Current)

Uses Amazon ML Challenge 2025 grocery/food product data with two loading methods:

1. **DataLoaderSource** (bulk ingestion from Parquet):
   - Test mode: `settings.use_test_data=true` loads `data/processed_amazon_grocery_1k.parquet`
   - Production mode: loads `data/processed_amazon_grocery.parquet`
   - Data loader name: `amazon_grocery_loader`
   - Note: DataLoaderSource must be triggered manually via API, it does not auto-load on startup

2. **RestSource** (manual ingestion via API):
   - POST to `/api/v1/ingest/product_schema` with JSON payload
   - Fields: item_id, description, price

**Data Preprocessing:**
Raw data is preprocessed using `scripts/preprocess_amazon_grocery.py`:
- Input: `amazon_grocery_data/student_resource/dataset/train.csv` (75k products)
- Download dataset: https://www.kaggle.com/datasets/raghavdharwal/amazon-ml-challenge-2025
- Output: `data/processed_amazon_grocery.parquet` (batched with row groups)
- Images: Downloaded to `data/images_amazon_grocery/` (file paths stored in Parquet)

#### H&M Fashion Clothing Dataset

Uses H&M fashion caption dataset from HuggingFace with multi-modal image+text search:

1. **DataLoaderSource** (bulk ingestion from Parquet):
   - Test mode: `settings.use_test_data=true` loads `data/processed_hm_clothing_1k.parquet`
   - Production mode: loads `data/processed_hm_clothing.parquet`
   - Data loader name: `hm_clothing_loader`
   - Note: DataLoaderSource must be triggered manually via API, it does not auto-load on startup

2. **RestSource** (manual ingestion via API):
   - POST to `/api/v1/ingest/hm_clothing_schema` with JSON payload
   - Fields: item_id, description, image (binary blob)

**Data Preprocessing:**
Raw data is preprocessed using `scripts/preprocess_hm_clothing.py`:
- Input: `tomytjandra/h-and-m-fashion-caption` HuggingFace dataset (20,491 items)
- Output: `data/processed_hm_clothing.parquet` with file paths to images
- Images: Saved to `data/images_hm_clothing/` as JPEG files (~120KB per image)
- First download: ~6GB (cached locally after first run)
- **Important**: Blob fields in Parquet must contain file paths, NOT base64-encoded data

**Memory Considerations for Image Embeddings:**

The CLIP Vision Transformer model (`laion/CLIP-ViT-H-14-laion2B-s32B-b79K`) generates large embeddings that consume significant RAM. Loading 100 images via DataLoaderSource can consume 30-40GB RAM, causing OOM kills.

**Recommendations:**
- Use `--chunk-size 5-10` for CLIP image embeddings
- Load each chunk separately via DataLoader API (manually trigger or modify api.py)
- Allow garbage collection between chunk loads
- Monitor RAM usage with `htop` or similar tools

**Note:** Superlinked's DataLoaderSource loads entire Parquet files into memory at once (no streaming support). For large datasets with image embeddings, chunking is essential.

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

**Strategy (~$50/month):**
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

- **`config.yaml`**: Superlinked server configuration (see docs/superlinked_config.md)
- **`superlinked_app/config/settings.toml`**: Application configuration with Dynaconf (see docs/configuration.md)
- **`superlinked_app/config/.secrets.toml`**: Local secret overrides (git-ignored, optional)
- **`pyproject.toml`**: Python dependencies and project metadata
- **`uv.lock`**: Dependency lockfile (managed by uv)
- **`.python-version`**: Python version (3.12)

## Key Documentation

- **`docs/configuration.md`**: Complete guide to Dynaconf-based configuration with GCP Secret Manager
- **`docs/development_plan.md`**: Complete GCP deployment guide with cost optimization
- **`docs/superlinked_config.md`**: Comprehensive config.yaml parameter reference
- **`docs/redis_setup.md`**: Redis Stack setup, configuration, and management guide
- **`README.md`**: Project overview and quick start

## Working with Superlinked

When modifying the application:

1. **Schema changes**: Modify `superlinked_app/index.py` → Update `ProductSchema`
2. **New spaces**: Add spaces in `index.py` → Combine in Index
3. **Query changes**: Modify `superlinked_app/query.py` → Add parameters, filters
4. **New endpoints**: Add sources/queries in `api.py` → Register with executor
5. **Configuration**: Update `config.yaml` → Restart server

**Do not modify the Superlinked server code itself** - it's a third-party package maintained by Superlinked.

## Current Schemas and Datasets

### Amazon Grocery Schema (ProductSchema)

Currently active schema for grocery/food products:

**ProductSchema fields:**
- `item_id` (IdField): Unique product identifier
- `description` (String): Concatenated product information (name, bullet points, value, unit)
- `price` (Float): Product price in dollars

**API Endpoints:**
- Ingest: `POST /api/v1/ingest/product_schema`
- Search: `POST /api/v1/search/product_search`
- Data Loader: `POST /data-loader/amazon_grocery_loader/run`

**Query parameters:**
- `query_text`: Search query for description matching
- `query_price`: Target price for similarity
- `description_weight`: Weight for text similarity (default: 1.0)
- `price_weight`: Weight for price similarity (default: 0.3)
- `limit`: Maximum results to return

**Data files:**
- Full: `data/processed_amazon_grocery.parquet` (75k products)
- Test: `data/processed_amazon_grocery_1k.parquet` (1k products)
- Images: `data/images_amazon_grocery/` and `data/images_amazon_grocery_1k/`

### H&M Fashion Clothing Schema (HMClothingSchema)

Schema for fashion/clothing items with multi-modal image+text search:

**HMClothingSchema fields:**
- `item_id` (IdField): Unique product identifier
- `description` (String): Text description of clothing item
- `image` (Blob): Binary image data (JPEG format, ~120KB per image)

**API Endpoints:**
- Ingest: `POST /api/v1/ingest/hm_clothing_schema`
- Search: `POST /api/v1/search/hm_clothing_search`
- Data Loader: `POST /data-loader/hm_clothing_loader/run`

**Query parameters:**
- `text_search`: Text query for description matching (text-in-text)
- `text_in_image_search`: Text query in image embeddings (CLIP text-to-image)
- `image_search`: Binary image data for image-in-image similarity
- `description_weight`: Weight for text similarity
- `image_weight`: Weight for image similarity
- `limit`: Maximum results to return

**Data files:**
- Full: `data/processed_hm_clothing.parquet` (20,491 items, ~2.5GB)
- Test: `data/processed_hm_clothing_1k.parquet` (100 items, ~26MB)

**Key differences from Grocery Schema:**
- **Multi-modal**: Uses CLIP Vision Transformer (`laion/CLIP-ViT-H-14-laion2B-s32B-b79K`)
- **Image search**: Supports text-to-image and image-to-image similarity
- **No price/ratings**: Pure visual + textual search
- **Larger model**: Uses `Alibaba-NLP/gte-large-en-v1.5` for text (same power as ESCI example)
- **Binary blobs**: Images stored as JPEG bytes in Parquet

**Image Search Scripts:**

Approache for image-based search ("find clothing matching this watch"):

1. **Direct curl** - Quick testing:
   ```bash
   # Multi-modal image+text search (single command)
   curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
     -H "Content-Type: application/json" \
     -d "{\"image_search\":\"$(base64 -w 0 your_image.jpg)\",\"text_search\":\"shirt\",\"description_weight\":1.0,\"image_weight\":2.0,\"limit\":5}"

   # Image-only search
   curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
     -H "Content-Type: application/json" \
     -d "{\"image_search\":\"$(base64 -w 0 your_image.jpg)\",\"image_weight\":2.0,\"limit\":5}"

   # Text-to-image search (CLIP semantic)
   curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
     -H "Content-Type: application/json" \
     -d '{"text_in_image_search":"elegant blue dress","image_weight":1.0,"limit":5}'
   ```
   - On macOS, use `base64 -i your_image.jpg` instead of `base64 -w 0`
   - Images are base64-encoded inline using command substitution
   - No intermediate files or placeholders needed