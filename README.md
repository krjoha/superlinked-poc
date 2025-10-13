# Search & Recommendations API

A production-ready search and recommendations API for e-commerce, powered by vector search and semantic understanding.

## Features

- **Semantic search**: Find products by natural language descriptions
- **Price-based similarity**: Recommend products at similar price points
- **Fast vector search**: Built on efficient embedding models
- **REST API**: Simple HTTP endpoints for ingestion and search
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

Start the server with the test dataset (1,000 products):

```bash
USE_TEST_DATA=1 python -m superlinked.server
```

Or run with the full dataset:

```bash
python -m superlinked.server
```

The server will start on `http://localhost:8080`

### Data Preprocessing

Before running the server with the full dataset, you need to download and preprocess the Amazon product data:

1. **Download the dataset**
   - Download from [Kaggle: Amazon ML Challenge 2025](https://www.kaggle.com/datasets/raghavdharwal/amazon-ml-challenge-2025)
   - Unzip the downloaded file
   - Place the contents in `amazon_data/student_resource/dataset/` (should contain `train.csv` and other files)

2. **Run the preprocessing script**
   ```bash
   # Process a sample of 1000 products (for testing)
   python scripts/preprocess_amazon_data.py --nrows 1000

   # Process the full dataset (75,000 products)
   python scripts/preprocess_amazon_data.py
   ```

This will:
- Load product data from `amazon_data/student_resource/dataset/train.csv`
- Download product images to `data/images/`
- Generate a batched Parquet file at `data/processed_products.parquet`

## API Usage

### Ingest Products

```bash
curl -X POST http://localhost:8080/api/v1/ingest/product_schema \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "12345",
    "description": "Laptop computer with 16GB RAM and 512GB SSD",
    "price": 899.99
  }'
```

### Search Products

```bash
curl -X POST http://localhost:8080/api/v1/search/product_search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "laptop computer",
    "query_price": 500.0,
    "description_weight": 1.0,
    "price_weight": 0.3,
    "limit": 3
  }'
```

**Query Parameters:**
- `query_text`: Natural language search query
- `query_price`: Target price for similarity matching
- `description_weight`: Weight for description similarity (default: 1.0)
- `price_weight`: Weight for price similarity (default: 0.3)
- `limit`: Maximum number of results

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
├── superlinked_app/          # Application code
│   ├── index.py              # Schema, spaces, and index definitions
│   ├── query.py              # Query logic
│   └── api.py                # API setup and data sources
├── scripts/                  # Utility scripts
│   └── preprocess_amazon_data.py  # Data preprocessing
├── data/                     # Processed data (generated)
│   ├── processed_products.parquet
│   └── images/
├── config.yaml               # Server configuration
├── docs/                     # Documentation
│   ├── development_plan.md   # GCP deployment guide
│   └── superlinked_config.md # Configuration reference
└── README.md                 # This file
```

## Configuration

The server is configured via `config.yaml`. Key configuration options include:

- `framework.app_module_path`: Python module containing your application
- `api.api_keys`: Authentication keys for the API
- `resource.max_workers`: Number of worker processes

See `docs/superlinked_config.md` for complete configuration reference.

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
- **Sentence Transformers**: Embedding models
- **PyArrow/Parquet**: Efficient data storage
- **Google Cloud Platform**: Production hosting (planned)
- **PostgreSQL**: Data storage (planned)
- **Redis**: Caching layer (planned)
- **BigQuery**: Analytics (planned)

## Deployment

This project is designed for deployment on Google Cloud Platform. See `docs/development_plan.md` for detailed deployment instructions including:

- Cloud Run serverless hosting
- Cloud SQL with pgvector extension
- Cost optimization strategies
- Infrastructure as code with Pulumi

## Documentation

- **[Development Plan](docs/development_plan.md)**: Complete GCP deployment guide with cost optimization
- **[Configuration Reference](docs/superlinked_config.md)**: All available `config.yaml` parameters
- **[Claude Instructions](CLAUDE.md)**: Project guidelines for Claude Code

## Support

For questions or issues, please open an issue in this repository.

## License

Copyright © 2025 PGI AB. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, modification, or use of this software, via any medium, is strictly prohibited without the express written permission of PGI AB.

