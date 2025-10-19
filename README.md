# Search & Recommendations API

A production-ready search and recommendations API for e-commerce, powered by vector search and semantic understanding.

## Features

- **Multi-modal search**: Text and image-based product search
- **Semantic understanding**: Find products by natural language descriptions
- **Image similarity**: Visual search for fashion items (H&M dataset)
- **Price-based similarity**: Recommend products at similar price points (Amazon dataset)
- **Multiple datasets**: Amazon Grocery (75k products) and H&M Fashion (20k items)
- **Fast vector search**: Built on efficient embedding models (Sentence Transformers, CLIP)
- **REST API**: Simple HTTP endpoints for ingestion and search
- **Redis support**: High-performance persistent vector storage
- **Scalable architecture**: Ready for production deployment on GCP

## Quick Start

### Prerequisites

- Python 3.12
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd superlinked-poc
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Activate the virtual environment**
   ```bash
   source .venv/bin/activate
   ```

### Running the Server

**Development mode** (uses test datasets: 1k products):

```bash
ENV_FOR_DYNACONF=development python -m superlinked.server
```

**Production mode** (uses full datasets: 75k grocery + 20k fashion):

```bash
ENV_FOR_DYNACONF=production python -m superlinked.server
```

**With Redis** (recommended for production):

```bash
# Start Redis Stack
./scripts/redis_manager.sh start

# Start server
ENV_FOR_DYNACONF=development python -m superlinked.server
```

The server will start on `http://localhost:8080`

### Data Preprocessing

The project includes two datasets. You can preprocess either or both:

#### Amazon Grocery Dataset (75k products)

1. **Download the dataset**
   - Download from [Kaggle: Amazon ML Challenge 2025](https://www.kaggle.com/datasets/raghavdharwal/amazon-ml-challenge-2025)
   - Unzip the downloaded file
   - Place the contents in `amazon_grocery_data/student_resource/dataset/` (should contain `train.csv`)

2. **Run the preprocessing script**
   ```bash
   # Process a sample of 1000 products (for testing)
   python scripts/preprocess_amazon_grocery.py --nrows 1000

   # Process the full dataset (75,000 products)
   python scripts/preprocess_amazon_grocery.py
   ```

   This will:
   - Load product data from `amazon_grocery_data/student_resource/dataset/train.csv`
   - Download product images to `data/images_amazon_grocery/`
   - Generate Parquet files at `data/processed_amazon_grocery.parquet` and `data/processed_amazon_grocery_1k.parquet`

#### H&M Fashion Dataset (20k items)

1. **Run the preprocessing script** (no manual download needed - uses HuggingFace datasets)
   ```bash
   # Process a sample of 100 items (for testing)
   python scripts/preprocess_hm_clothing.py --nrows 100

   # Process the full dataset (20,491 items)
   python scripts/preprocess_hm_clothing.py
   ```

   This will:
   - Download H&M fashion dataset from HuggingFace (tomytjandra/h-and-m-fashion-caption)
   - Save images to `data/images_hm_clothing/`
   - Generate CSV files at `data/processed_hm_clothing.csv` and `data/processed_hm_clothing_1k.csv`

**Note**: The H&M dataset includes image embeddings using CLIP Vision Transformer, which requires significant RAM (~30-40GB for 100 images). Use small batch sizes for processing.

## API Usage

### Amazon Grocery API

#### Ingest Grocery Products

```bash
curl -X POST http://localhost:8080/api/v1/ingest/amazon_grocery_schema \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "12345",
    "description": "Organic whole milk 1 gallon grass-fed",
    "price": 6.99
  }'
```

#### Search Grocery Products

```bash
curl -X POST http://localhost:8080/api/v1/search/amazon_grocery_search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "organic milk",
    "query_price": 7.0,
    "description_weight": 1.0,
    "price_weight": 0.3,
    "limit": 5
  }'
```

**Query Parameters:**
- `query_text`: Natural language search query
- `query_price`: Target price for similarity matching
- `description_weight`: Weight for description similarity (default: 1.0)
- `price_weight`: Weight for price similarity (default: 0.3)
- `limit`: Maximum number of results

### H&M Fashion API

#### Ingest Fashion Items

```bash
curl -X POST http://localhost:8080/api/v1/ingest/hm_clothing_schema \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "67890",
    "description": "Blue denim jacket with buttons",
    "image": "base64_encoded_image_data_here"
  }'
```

#### Search Fashion Items (Text)

```bash
curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
  -H "Content-Type: application/json" \
  -d '{
    "text_search": "blue jacket",
    "description_weight": 1.0,
    "limit": 5
  }'
```

#### Search Fashion Items (Image)

```bash
# Image-to-image search
curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
  -H "Content-Type: application/json" \
  -d "{\"image_search\":\"$(base64 -w 0 your_image.jpg)\",\"image_weight\":2.0,\"limit\":5}"

# Text-to-image search (CLIP semantic)
curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
  -H "Content-Type: application/json" \
  -d '{"text_in_image_search":"elegant blue dress","image_weight":1.0,"limit":5}'

# Multi-modal (text + image)
curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
  -H "Content-Type: application/json" \
  -d "{\"image_search\":\"$(base64 -w 0 your_image.jpg)\",\"text_search\":\"jacket\",\"description_weight\":1.0,\"image_weight\":2.0,\"limit\":5}"
```

**Query Parameters:**
- `text_search`: Text query for description matching (text-in-text)
- `text_in_image_search`: Text query in image embeddings (CLIP text-to-image)
- `image_search`: Base64-encoded image data for image-in-image similarity
- `description_weight`: Weight for text similarity
- `image_weight`: Weight for image similarity
- `limit`: Maximum number of results

**Note**: On macOS, use `base64 -i your_image.jpg` instead of `base64 -w 0`

### Example Response

```json
{
  "entries": [
    {
      "id": "12345",
      "fields": {
        "description": "Laptop computer with 16GB RAM and 512GB SSD",
        "price": 899.99
      },
      "metadata": {
        "score": 0.8542
      }
    }
  ]
}
```

## Project Structure

```
superlinked-poc/
├── superlinked_app/                    # Application code
│   ├── config/                         # Configuration system
│   │   ├── config.py                   # Dynaconf with GCP Secret Manager
│   │   ├── settings.toml               # Application settings
│   │   └── .secrets.toml              # Local secrets (git-ignored)
│   ├── amazon_index.py                 # Amazon Grocery schema & index
│   ├── amazon_query.py                 # Amazon Grocery query logic
│   ├── hm_index.py                     # H&M Fashion schema & index
│   ├── hm_query.py                     # H&M Fashion query logic
│   ├── vector_db.py                    # Vector database factory
│   └── api.py                          # API setup and data sources
├── scripts/                            # Utility scripts
│   ├── preprocess_amazon_grocery.py    # Amazon data preprocessing
│   ├── preprocess_hm_clothing.py       # H&M data preprocessing
│   └── redis_manager.sh                # Redis management script
├── data/                               # Processed data (generated)
│   ├── processed_amazon_grocery.parquet
│   ├── processed_amazon_grocery_1k.parquet
│   ├── processed_hm_clothing.csv
│   ├── processed_hm_clothing_1k.csv
│   ├── images_amazon_grocery/
│   └── images_hm_clothing/
├── config.yaml                         # Superlinked server configuration
├── docs/                               # Documentation
│   ├── configuration.md                # Dynaconf configuration guide
│   ├── development_plan.md             # GCP deployment guide
│   ├── redis_setup.md                  # Redis setup guide
│   └── superlinked_config.md           # Superlinked config reference
└── README.md                           # This file
```

## Configuration

The project uses a **dual configuration system**:

### Superlinked Server (`config.yaml`)
Framework-level configuration:
- `framework.app_module_path`: Python module containing your application
- `framework.disable_recency_space`: Must be `false` if using RecencySpace
- `resource.max_workers`: Number of worker processes

See `docs/superlinked_config.md` for complete reference.

### Application Settings (Dynaconf)
Application-level configuration in `superlinked_app/config/settings.toml`:
- **Environment-based**: `development` and `production` sections
- **Vector database**: Configure InMemory or Redis
- **Data loading**: Test vs. full datasets
- **GCP Secret Manager**: Automatic secret loading in production
- **Local overrides**: Use `.secrets.toml` for development

**Switch environments:**
```bash
# Development (default)
ENV_FOR_DYNACONF=development python -m superlinked.server

# Production (loads secrets from GCP)
ENV_FOR_DYNACONF=production python -m superlinked.server
```

See `docs/configuration.md` for complete guide.

## Development

### Code Quality

```bash
# Format code
black .
isort .

# Lint
ruff check .

# Type checking
mypy .
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific.py
```

## Technology Stack

- **Python 3.12**: Core language
- **FastAPI**: Web framework (via Superlinked server)
- **Superlinked**: Vector search framework
- **Dynaconf**: Configuration management with GCP Secret Manager integration
- **Sentence Transformers**: Text embedding models (all-MiniLM-L6-v2, gte-large-en-v1.5)
- **CLIP**: Multi-modal image+text embeddings (laion/CLIP-ViT-H-14)
- **Redis Stack**: Vector database with RediSearch (persistent storage)
- **PyArrow/Parquet & CSV**: Efficient data storage
- **Google Cloud Platform**: Production hosting target
- **GCP Secret Manager**: Secure secret storage
- **BigQuery**: Analytics (planned)

## Deployment

This project is designed for deployment on Google Cloud Platform. See `docs/development_plan.md` for detailed deployment instructions including:

- Cloud Run serverless hosting
- Redis (Cloud Memorystore) or PostgreSQL (Cloud SQL with pgvector)
- GCP Secret Manager for API keys and secrets
- Cost optimization strategies (~$50/month)
- Infrastructure as code with Pulumi

## Documentation

- **[Configuration Guide](docs/configuration.md)**: Dynaconf configuration with GCP Secret Manager
- **[Development Plan](docs/development_plan.md)**: Complete GCP deployment guide with cost optimization
- **[Redis Setup](docs/redis_setup.md)**: Redis Stack setup and management
- **[Superlinked Config Reference](docs/superlinked_config.md)**: All available `config.yaml` parameters
- **[Claude Instructions](CLAUDE.md)**: Project guidelines for Claude Code

## Support

For questions or issues, please open an issue in this repository.

## License

Copyright © 2025 PGI AB. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, modification, or use of this software, via any medium, is strictly prohibited without the express written permission of PGI AB.

