# Development Plan & Progress Tracking

**Last Updated:** 2025-10-07
**Project:** E-commerce Search & Recommendations API (search_rec_api)
**Dataset:** Amazon Berkeley Objects (ABO)

---

## 📊 Current Status: Phase 0 - Local Development (95% Complete)

### ✅ Completed Tasks

#### Data Acquisition & Processing
- ✅ Downloaded Amazon Berkeley Objects dataset
  - `abo-listings.tar` (84MB) - Product metadata (147,702 products)
  - `abo-images-small.tar` (3.1GB) - 256px product images
- ✅ Created preprocessing pipeline (`scripts/preprocess_amazon_data.py`)
  - Extracts English text from multilingual fields
  - Deduplicates items (removed 2,087 duplicates)
  - Outputs Parquet format with proper schema (17.38MB)
  - Generates 15 row groups @ ~10k rows each for efficient loading
- ✅ Generated datasets:
  - **Test:** 3,969 SHOES products (English-speaking countries only)
  - **Production:** 145,615 unique products (all categories)

#### Schema & Application Design
- ✅ Designed `ProductSchema` with 10 fields (item_id, item_name, brand, product_type, color, description, keywords, image_id, country, domain)
- ✅ Configured 4 similarity spaces with weighted multi-field search
- ✅ Environment variable switching (`USE_TEST_DATA`) between test/prod datasets
- ✅ Verified embedding model reuse (1x memory usage, not 3x)

### ⏳ Next Immediate Steps

1. **Ingest test dataset & validate search** (Phase 0 completion)
   ```bash
   USE_TEST_DATA=1 python -m superlinked.server
   curl -X POST http://localhost:8080/data-loader/amazon_products_loader/run
   ```

2. **Run test queries** to validate search quality
   ```bash
   curl -X POST http://localhost:8080/api/v1/search/product_search \
     -H "Content-Type: application/json" \
     -d '{"query_text": "running shoes", "product_type": "SHOES", "limit": 10}'
   ```

3. **Decision Point:** Evaluate if `all-MiniLM-L6-v2` model is sufficient or needs upgrade

---

## 🗺️ Deployment Roadmap

### Phase 0: Local Development & Validation (Current - 95%)
**Goal:** Confirm basic search works with test dataset

- [x] Download and preprocess Amazon Berkeley Objects data
- [x] Configure Superlinked schema and spaces
- [x] Set up test/prod dataset switching
- [ ] Ingest test data (3,969 products)
- [ ] Validate search quality with 10+ queries
- [ ] Benchmark query latency and relevance

**Success Criteria:**
- Search returns relevant results
- Query latency < 500ms for test dataset
- Ready to proceed to production data

---

### Phase 1: Production Readiness (Not Started)
**Goal:** Full dataset loaded, API secured, performance validated

**Tasks:**
- [ ] Load full 145k product dataset
- [ ] Configure API key authentication in `config.yaml`
- [ ] Set up CORS for allowed origins
- [ ] Add filtering by brand, color, country
- [ ] Map product images to API responses
- [ ] Benchmark with production data (target: p95 < 500ms)
- [ ] Create test suite

**Success Criteria:**
- Full dataset searchable
- API properly authenticated
- Performance targets met across all product types

---

### Phase 2: GCP Deployment (Detailed Instructions Below)
**Goal:** Deploy to GCP with ultra-budget strategy (~$12-41/month)

This phase follows the detailed deployment instructions in the sections below.

---

## GCP Deployment Instructions

## Overview
This guide provides a deployment strategy using GCP services with free tier monitoring and on-demand dashboards. Particularly BigQuery has a generous free tier offering.

## Cost Optimization Philosophy
- **Consolidate services**: Single PostgreSQL for vectors + billing
- **Maximize free tiers**: BigQuery, Looker Studio, Cloud Monitoring
- **Smart storage**: Use appropriate storage for each data type
- **Minimal infrastructure**: Only pay for what you actually use

## Prerequisites
- GCP account with billing enabled
- `gcloud` CLI installed and authenticated
- Docker installed locally
- Basic understanding of SQL and BigQuery

## Phase 1: Project Setup and Region Selection

### 1.1 Create GCP Project with Cost Controls
```bash
# Create project with cost optimization in mind
gcloud projects create your-superlinked-cheap --name="Superlinked Cheap"
gcloud config set project your-superlinked-cheap

# Choose cheapest region (us-central1 typically lowest cost)
export REGION="us-central1"
export ZONE="us-central1-a"
gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE

# Enable only necessary APIs (free within quotas)
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable logging.googleapis.com
```

### 1.2 Set Up Billing Budget and Alerts (FREE)
```bash
# Get your billing account ID
gcloud billing accounts list

# Create strict budget with email alerts
gcloud billing budgets create \
    --billing-account=YOUR-BILLING-ACCOUNT-ID \
    --display-name="Superlinked Budget" \
    --budget-amount=50USD \
    --threshold-percent=25,50,75,90 \
    --notification-channels-email=your-email@domain.com
```

## Phase 2: Consolidated Database Setup (Single PostgreSQL Instance)

### 2.1 Create Minimal PostgreSQL Instance
```bash
# Create smallest possible Cloud SQL instance
gcloud sql instances create superlinked-all-in-one \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --no-backup \
    --maintenance-release-channel=production \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --deletion-protection
```

### 2.2 Database Schema Design
This single PostgreSQL instance will handle:
- **Vector storage** with pgvector extension
- **Real-time billing** and user quotas
- **Application data** for your Superlinked app

**Key tables to create:**
```sql
-- Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Embeddings table (replaces Redis/external vector DB)
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    item_id VARCHAR(255) UNIQUE NOT NULL,
    attribute_text TEXT,
    embedding vector(384), -- Adjust dimension for your model
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Real-time billing table (for immediate quota checks)
CREATE TABLE user_quotas (
    api_key_hash VARCHAR(64) PRIMARY KEY,
    monthly_request_limit INTEGER DEFAULT 10000,
    monthly_embedding_limit INTEGER DEFAULT 50000,
    current_month_requests INTEGER DEFAULT 0,
    current_month_embeddings INTEGER DEFAULT 0,
    last_reset_date DATE DEFAULT CURRENT_DATE,
    billing_tier VARCHAR(50) DEFAULT 'free'
);

-- Performance indexes
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON embeddings (item_id);
CREATE INDEX ON user_quotas(last_reset_date);
```

## Phase 3: BigQuery Setup for Analytics (FREE Tier)

### 3.1 Create BigQuery Dataset
```bash
# Create dataset for usage analytics
bq mk --dataset --location=$REGION your-superlinked-cheap:usage_analytics
```

### 3.2 BigQuery Schema for Long-term Analytics
**Purpose**: Store detailed usage logs for analytics and historical reporting

**Key tables:**
```sql
-- Main usage tracking table (partitioned for cost efficiency)
CREATE TABLE usage_analytics.api_requests (
  timestamp TIMESTAMP,
  api_key_hash STRING,
  endpoint STRING,
  method STRING,
  response_time_ms INTEGER,
  status_code INTEGER,
  tokens_used INTEGER,
  vector_operations INTEGER,
  embedding_operations INTEGER,
  cost_cents INTEGER,
  user_ip STRING,
  user_agent STRING,
  request_size_bytes INTEGER
)
PARTITION BY DATE(timestamp)
CLUSTER BY api_key_hash, endpoint;

-- Pre-aggregated daily stats (faster dashboards, lower costs)
CREATE TABLE usage_analytics.daily_summary AS
SELECT
  DATE(timestamp) as usage_date,
  api_key_hash,
  endpoint,
  COUNT(*) as request_count,
  AVG(response_time_ms) as avg_response_time,
  SUM(tokens_used) as total_tokens,
  SUM(cost_cents) as total_cost_cents,
  COUNTIF(status_code >= 400) as error_count
FROM usage_analytics.api_requests
WHERE DATE(timestamp) = CURRENT_DATE()
GROUP BY 1,2,3;
```

### 3.3 Set Up Log Export to BigQuery (FREE)
```bash
# Create log sink to export usage logs to BigQuery
gcloud logging sinks create superlinked-usage-sink \
    bigquery.googleapis.com/projects/your-superlinked-cheap/datasets/usage_analytics \
    --log-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="superlinked-api" AND jsonPayload.event="api_request"'
```

## Phase 4: Application Configuration for Cheap Deployment

### 4.1 Optimized Dependencies
**pyproject.toml updates:**
```toml
dependencies = [
    "altair>=5.5.0",
    "dynaconf>=3.2.11",
    "superlinked-server>=1.56.4",
    "psycopg2-binary>=2.9.0",        # PostgreSQL
    "pgvector>=0.2.0",               # Vector support
    "sqlalchemy>=2.0.0",             # Database ORM
    "google-cloud-bigquery>=3.11.0", # BigQuery logging
    "google-cloud-secret-manager>=2.16.0", # Secrets
    "cachetools>=5.3.0",             # In-memory caching
    "structlog>=23.1.0",             # Structured logging
]
```

### 4.2 Cost-Optimized Configuration
**config/cheap.yaml:**
```yaml
framework:
  app_module_path: superlinked_app.api
  disable_recency_space: false

api:
  api_keys: []  # Loaded from Secret Manager
  allowed_origins:
    - "https://yourdomain.com"
  rate_limit:
    requests_per_minute: 30  # Reduced for cost control
    requests_per_hour: 300

model:
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

resource:
  max_workers: 2  # Minimal workers

# Single PostgreSQL configuration
database:
  type: "postgresql"
  url: ""  # From Secret Manager
  pool_size: 3    # Small pool
  max_overflow: 0 # No overflow

# Local storage (cheapest option)
storage:
  type: "local"
  path: "/tmp/images"
  max_size_mb: 50

# Logging configuration
logging:
  level: "INFO"
  structured: true
  bigquery_export: true

# Caching for cost optimization
caching:
  enable_embedding_cache: true
  cache_ttl_seconds: 600
  max_cache_entries: 500
```

## Phase 5: Secret Management (FREE Tier)

### 5.1 Store Configuration Secrets
```bash
# Generate API keys
API_KEY1=$(openssl rand -base64 32)
API_KEY2=$(openssl rand -base64 32)

# Store API keys in Secret Manager (6 secrets free per month)
gcloud secrets create api-keys --data-file=- <<EOF
["$API_KEY1", "$API_KEY2"]
EOF

# Store database connection string
gcloud secrets create database-url --data-file=- <<EOF
postgresql://app_user:PASSWORD@localhost/superlinked_app?host=/cloudsql/CONNECTION_NAME
EOF
```

## Phase 6: Docker Configuration for Minimal Resources

### 6.1 Lightweight Dockerfile
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY . .

# Create temp storage
RUN mkdir -p /tmp/images

# Set environment
ENV PORT=8080
ENV ENVIRONMENT=cheap
ENV PYTHONUNBUFFERED=1

# Run application
CMD ["python", "-m", "superlinked.server", "--host", "0.0.0.0", "--port", "8080", "--config", "config/cheap.yaml"]
```

## Phase 7: Cloud Run Deployment (Minimal Configuration)

### 7.1 Deploy with Minimal Resources
```bash
# Build image
gcloud builds submit --tag gcr.io/your-superlinked-cheap/superlinked-app

# Deploy with minimal settings
gcloud run deploy superlinked-cheap-api \
    --image gcr.io/your-superlinked-cheap/superlinked-app \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 3 \
    --min-instances 0 \
    --concurrency 50 \
    --timeout 120 \
    --set-env-vars ENVIRONMENT=cheap \
    --set-secrets DATABASE_URL=database-url:latest \
    --set-secrets API_KEYS=api-keys:latest \
    --add-cloudsql-instances your-superlinked-cheap:$REGION:superlinked-all-in-one
```

## Phase 8: Free Monitoring Setup

### 8.1 Option A: Free Looker Studio Dashboard (Recommended)

**Benefits:**
- Completely FREE
- Web-based, accessible anywhere
- Professional-looking dashboards
- Real-time data from BigQuery
- Shareable with team/stakeholders

**Setup Steps:**
1. Go to [lookerstudio.google.com](https://lookerstudio.google.com)
2. Create new report
3. Add BigQuery as data source
4. Connect to your `usage_analytics` dataset
5. Create visualizations for:
   - Daily request volume
   - Response time trends
   - Error rate monitoring
   - Cost per customer
   - Geographic usage distribution

**Sample Dashboard Widgets:**
- **Time Series**: Requests per hour/day
- **Scorecards**: Total requests, revenue, active users
- **Bar Charts**: Top customers by usage
- **Pie Charts**: Request distribution by endpoint
- **Tables**: Recent errors and performance issues

### 8.2 Option B: Local Laptop Dashboard (On-Demand)

**Benefits:**
- No ongoing costs
- Full customization control
- Works offline with exported data
- Can use advanced analytics tools

**Tools to Consider:**
- **Grafana**: Professional dashboards with BigQuery connector
- **Streamlit**: Simple Python dashboard app
- **Jupyter Notebooks**: For ad-hoc analysis
- **Google Colab**: Free cloud notebooks for analysis

**Connection Method:**
```bash
# Install BigQuery client
pip install google-cloud-bigquery pandas streamlit

# Export data for offline analysis
bq extract --destination_format=CSV \
    usage_analytics.daily_summary \
    gs://your-bucket/daily_summary.csv
```

### 8.3 Option C: Simple Custom Dashboard

**Create a minimal web dashboard using Cloud Functions (FREE tier):**
- Serverless dashboard endpoint
- Basic HTML/CSS/JavaScript
- Queries BigQuery on-demand
- 2M invocations per month free

## Phase 9: Alerting and Notifications (FREE)

### 9.1 Budget Alerts (Already configured in Phase 1)
- Email notifications at 25%, 50%, 75%, 90% of budget
- Daily spend reports
- Unusual usage pattern alerts

### 9.2 Application Health Monitoring
```bash
# Create simple uptime check (100 checks/month free)
gcloud monitoring uptime create \
    --display-name="Superlinked Cheap API Health" \
    --resource-type=URL \
    --hostname=your-cloud-run-url \
    --path=/health \
    --check-interval=300s \
    --timeout=10s
```

### 9.3 Custom Alerts via Cloud Functions
**Free tier provides 2M invocations/month**
- Error rate spikes
- Unusual cost increases
- High response times
- Quota threshold warnings

## Phase 10: Cost Optimization Strategies

### 10.1 Database Optimization
**Connection Pooling:**
```python
# Minimal connection pool
engine = create_engine(
    DATABASE_URL,
    pool_size=2,        # Minimal pool
    max_overflow=1,     # Small overflow
    pool_recycle=1800,  # 30-minute recycle
    pool_pre_ping=True
)
```

**Query Optimization:**
- Use prepared statements
- Implement proper indexes
- Cache frequent queries
- Batch operations when possible

### 10.2 BigQuery Cost Control
**Best Practices:**
- Use partitioned tables (automatic cost savings)
- Cluster frequently queried columns
- Avoid SELECT * queries
- Use approximate functions when exact counts not needed
- Set query timeouts and data size limits

**Query Optimization:**
```sql
-- Good: Efficient partitioned query
SELECT COUNT(*) FROM usage_analytics.api_requests
WHERE DATE(timestamp) = CURRENT_DATE()

-- Bad: Expensive full table scan
SELECT COUNT(*) FROM usage_analytics.api_requests
WHERE timestamp > '2024-01-01'
```

### 10.3 Application-Level Optimizations
**Caching Strategy:**
- Cache embedding computations
- Cache frequent database queries
- Implement request deduplication
- Use HTTP caching headers

**Batching:**
- Batch multiple embedding requests
- Aggregate logs before sending to BigQuery
- Process multiple vector searches together

## Phase 11: Scaling Strategy (When Needed)

### 11.1 When to Scale Up
**Indicators:**
- Consistent >80% CPU usage
- Response times >2 seconds consistently
- Database connection pool exhaustion
- Approaching BigQuery free tier limits

### 11.2 Cost-Effective Scaling Options
**Cloud Run Scaling:**
1. Increase memory before adding instances
2. Optimize code before scaling horizontally
3. Consider regional load balancing for global users

**Database Scaling:**
1. Optimize queries before upgrading instance
2. Consider read replicas only when necessary
3. Use connection pooling effectively

**BigQuery Scaling:**
1. Implement better partitioning
2. Use materialized views for common queries
3. Consider BigQuery BI Engine for dashboard acceleration

## Phase 12: Maintenance and Operations

### 12.1 Daily Operations (5 minutes/day)
- Check GCP billing dashboard
- Review Looker Studio dashboard for anomalies
- Scan Cloud Logging for errors

### 12.2 Weekly Operations (15 minutes/week)
- Review BigQuery usage and costs
- Check database performance insights
- Update rate limits if needed
- Review user usage patterns

### 12.3 Monthly Operations (30 minutes/month)
- Analyze cost trends and optimize
- Review and rotate API keys
- Clean up old data if approaching limits
- Plan capacity for next month

## Phase 13: Monitoring Dashboard Setup Guide

### 13.1 Looker Studio Dashboard Creation
**Step-by-step setup:**

1. **Create New Report**
   - Go to lookerstudio.google.com
   - Click "Create" → "Report"
   - Choose "BigQuery" connector

2. **Connect Data Source**
   - Select your project: `your-superlinked-cheap`
   - Choose dataset: `usage_analytics`
   - Select table: `api_requests`

3. **Create Key Visualizations**
   - **Page 1: Overview Dashboard**
     * Scorecard: Total requests today
     * Scorecard: Average response time
     * Scorecard: Error rate percentage
     * Time series: Requests per hour (last 24h)
     * Bar chart: Top endpoints by usage

   - **Page 2: User Analytics**
     * Table: Top users by request count
     * Pie chart: Request distribution by user
     * Time series: Active users per day
     * Geo map: Requests by location

   - **Page 3: Performance Monitoring**
     * Time series: Response time percentiles
     * Bar chart: Errors by endpoint
     * Scorecard: Database query time
     * Table: Slowest requests

   - **Page 4: Revenue Analytics**
     * Scorecard: Total revenue this month
     * Time series: Daily revenue
     * Bar chart: Revenue by customer
     * Table: Cost per customer

4. **Set Up Auto-Refresh**
   - Configure data refresh: Every 4 hours
   - Enable email reports: Daily summary

### 13.2 Local Dashboard Setup (Alternative)
**For Grafana users:**

1. **Install Grafana locally:**
   ```bash
   docker run -d -p 3000:3000 grafana/grafana
   ```

2. **Install BigQuery plugin:**
   ```bash
   grafana-cli plugins install grafana-bigquery-datasource
   ```

3. **Configure BigQuery connection:**
   - Add datasource
   - Use service account key
   - Test connection

4. **Import dashboard templates:**
   - API monitoring dashboard
   - Cost tracking dashboard
   - User analytics dashboard

## Phase 14: Cost Breakdown and ROI Analysis

### 14.1 Monthly Cost Estimate
**Infrastructure Costs:**
- Cloud SQL (db-f1-micro): $7-15/month
- Cloud Run (minimal usage): $3-20/month
- Cloud Build: $1-5/month
- Secret Manager: $1/month (6 secrets)

**Free Tier Services:**
- BigQuery: FREE (10GB storage + 1TB queries)
- Looker Studio: FREE (unlimited dashboards)
- Cloud Monitoring: FREE (basic metrics)
- Cloud Logging: FREE (50GB ingestion)
- Uptime checks: FREE (100 checks/month)

### 14.3 Break-Even Analysis
**Revenue needed to break even:**
- At $0.001 per API call: 12,000-41,000 calls/month
- At $0.01 per API call: 1,200-4,100 calls/month
- At $0.10 per API call: 120-410 calls/month

## Phase 15: Troubleshooting Common Issues

### 15.1 High Database Costs
**Symptoms:** Cloud SQL bill higher than expected
**Solutions:**
- Check for long-running queries in performance insights
- Implement connection pooling
- Add missing indexes
- Consider query optimization

### 15.2 BigQuery Costs Above Free Tier
**Symptoms:** BigQuery charges appearing
**Solutions:**
- Check query patterns in BigQuery console
- Implement query result caching
- Use more selective WHERE clauses
- Consider pre-aggregated tables

### 15.3 Cloud Run Cold Starts
**Symptoms:** High latency on first requests
**Solutions:**
- Set min-instances to 1 if budget allows
- Optimize container startup time
- Implement application warming
- Use smaller base Docker images

### 15.4 Poor Dashboard Performance
**Symptoms:** Looker Studio dashboards load slowly
**Solutions:**
- Use pre-aggregated tables in BigQuery
- Implement BI Engine acceleration
- Reduce data range in visualizations
- Optimize BigQuery query patterns

## Phase 16: Advanced Optimizations

### 16.1 Smart Data Retention
**Automatic cleanup to stay within free tiers:**
```sql
-- Weekly cleanup job (via Cloud Scheduler - free tier)
DELETE FROM usage_analytics.api_requests
WHERE DATE(timestamp) < DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY);

-- Keep only daily summaries for older data
INSERT INTO usage_analytics.historical_summary
SELECT DATE(timestamp) as date, ...
FROM usage_analytics.api_requests
WHERE DATE(timestamp) < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY);
```

### 16.2 Intelligent Caching
**Multi-level caching strategy:**
- Application memory: 5-minute cache for embeddings
- Database query cache: 15-minute cache for search results
- HTTP response cache: 1-minute cache for read operations

### 16.3 Request Optimization
**Batch processing:**
- Combine multiple embedding requests
- Aggregate multiple vector searches
- Batch log writes to BigQuery

## Phase 17: Going Live Checklist

### Pre-Launch Verification
- [ ] Database created with proper schemas and indexes
- [ ] BigQuery dataset configured with log export
- [ ] API keys stored in Secret Manager
- [ ] Cloud Run deployed and responding
- [ ] Looker Studio dashboard created and functional
- [ ] Budget alerts configured and tested
- [ ] Uptime checks configured
- [ ] Health endpoint responding correctly
- [ ] Rate limiting working as expected
- [ ] Vector search functionality verified

### Post-Launch Monitoring (First Week)
- [ ] Monitor GCP billing dashboard daily
- [ ] Check Looker Studio dashboard for data flow
- [ ] Verify BigQuery data ingestion
- [ ] Test API endpoints under various loads
- [ ] Monitor Cloud Run metrics for performance
- [ ] Validate cost projections against actual usage
- [ ] Check database performance and connections

### Ongoing Success Metrics
- **Cost Efficiency**: Stay under $50/month budget
- **Performance**: <500ms average response time
- **Reliability**: >99% uptime
- **Data Quality**: All usage properly logged and tracked
- **Scalability**: Handle growth without major cost increases

## Conclusion

The key to success is starting simple, monitoring closely, and scaling only when necessary. This setup can handle significant traffic and provides all the monitoring and analytics needed for a production API service while keeping costs minimal.