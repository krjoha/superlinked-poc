# Superlinked Configuration Analysis

## Executive Summary

This document provides a comprehensive analysis of configuration options available for the Superlinked server (started with `python -m superlinked.server`). The analysis was performed on the installed package at `.venv/lib/python3.12/site-packages/superlinked/`.

## Configuration System Architecture

Superlinked uses **Pydantic Settings** with YAML-based configuration through the `config.yaml` file. The configuration is organized into **four main sections**:

1. `server` - Server-specific settings
2. `framework` - Framework-level settings
3. `image` - Image processing settings
4. `resource` - Resource management settings (with nested subsections)

### Configuration Loading Priority

Settings are loaded in the following order (later sources override earlier ones):
1. Default values in settings classes
2. Environment variables (with `__` as nested delimiter)
3. YAML configuration file (`config.yaml`)
4. File secret settings

### Source Files

- **Server Settings**: `.venv/lib/python3.12/site-packages/superlinked/server/configuration/settings.py`
- **Framework Settings**: `.venv/lib/python3.12/site-packages/superlinked/framework/common/settings.py`

---

## Complete Configuration Reference

### 1. SERVER SECTION (`server:`)

Server-specific settings that control the HTTP server, authentication, logging, and deployment configuration.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `app_module_path` | str | `"superlinked_app"` | Path to the application module containing your Superlinked app code |
| `log_level` | str | `"INFO"` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `persistence_folder_path` | str | `"in_memory_vdb"` | Folder path for persisting vector database data |
| `server_port` | int | `8080` | Port number for the HTTP server |
| `server_host` | str | `"0.0.0.0"` | Host address to bind the server to |
| `disable_recency_space` | bool | `True` | If True, disables RecencySpace functionality |
| `json_log_file` | str \| None | `None` | Path to JSON log file (if separate from main logs) |
| `log_as_json` | bool | `False` | Enable structured JSON logging format |
| `expose_pii` | bool | `False` | Allow personally identifiable information in logs |
| `environment_name` | str | `"DEV"` | Environment identifier (DEV, STAGING, PROD, etc.) |
| `api_key` | str \| None | `None` | Single API key for authentication (sent via Authorization header) |
| `worker_count` | int | `1` | Number of Uvicorn worker processes |
| `is_dockerized` | bool | `False` | Set to True when running in Docker (enables GCS download) |
| `bucket_name` | str \| None | `None` | GCS bucket name (required if is_dockerized=True) |
| `bucket_prefix` | str \| None | `None` | GCS bucket prefix (required if is_dockerized=True) |
| `project_id` | str \| None | `None` | GCP project ID for GCS access |
| `sentry_enable` | bool | `False` | Enable Sentry error tracking |
| `sentry_url` | str \| None | `None` | Sentry DSN URL |
| `sentry_send_default_pii` | bool | `True` | Send PII to Sentry |
| `sentry_traces_sample_rate` | float | `0.01` | Percentage of traces to send to Sentry (0.0-1.0) |
| `sentry_profiles_sample_rate` | float | `0.01` | Percentage of profiles to send to Sentry (0.0-1.0) |
| `opentelemetry_enable` | bool | `False` | Enable OpenTelemetry instrumentation |
| `opentelemetry_collector_endpoint` | str \| None | `"127.0.0.1:4317"` | OpenTelemetry collector gRPC endpoint |
| `opentelemetry_component_name` | str | `"superlinked-server"` | Service name for telemetry data |
| `opentelemetry_trace_sampling_rate` | float | `0.1` | Trace sampling rate (0.0-1.0) |
| `opentelemetry_metrics_export_interval_ms` | int | `15000` | Metrics export interval in milliseconds |

**Example:**
```yaml
server:
  app_module_path: superlinked_app
  server_port: 8080
  server_host: 0.0.0.0
  disable_recency_space: false
  api_key: "your_secret_api_key"
  worker_count: 4
  log_level: INFO
  log_as_json: true
  environment_name: PRODUCTION
```

---

### 2. FRAMEWORK SECTION (`framework:`)

Framework-level settings that control embedding models, batching, blob handling, and internal framework behavior.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `app_id` | str | `"default"` | Application identifier for multi-app scenarios |
| `enable_mps` | bool | `False` | Enable Metal Performance Shaders (Apple Silicon GPU acceleration) |
| `batched_embedding_wait_time_ms` | int | `0` | Wait time in ms before processing batched embeddings (0=disabled) |
| `batched_vdb_read_wait_time_ms` | int | `0` | Wait time in ms before processing batched VDB reads (0=disabled) |
| `batched_blob_load_wait_time_ms` | int | `0` | Wait time in ms before processing batched blob loads (0=disabled) |
| `batched_vdb_write_wait_time_ms` | int | `0` | Wait time in ms before processing batched VDB writes (0=disabled) |
| `model_warmup` | bool | `False` | Warm up embedding models on server startup |
| `model_cache_dir` | str \| None | `None` | Directory to cache downloaded embedding models |
| `model_lock_timeout_seconds` | int | `120` | Timeout for acquiring model lock |
| `sentence_transformers_model_lock_max_retries` | int | `10` | Max retries for acquiring Sentence Transformers model lock |
| `sentence_transformers_model_lock_retry_delay` | int | `1` | Delay in seconds between model lock retries |
| `sentence_transformers_model_lock_timeout_buffer_seconds` | int | `10` | Buffer time added to model lock timeout |
| `sentence_transformers_model_lock_timeout_min_seconds` | int | `5` | Minimum timeout for model lock |
| `blob_handler_module_path` | str \| None | `None` | Python module path for custom blob handler |
| `blob_handler_class_name` | str \| None | `None` | Class name of custom blob handler |
| `blob_handler_class_args` | dict \| None | `None` | Arguments to pass to custom blob handler constructor |
| `superlinked_log_level` | int \| str \| None | `None` | Superlinked-specific log level |
| `superlinked_log_as_json` | bool | `False` | Enable JSON logging for Superlinked logs |
| `superlinked_log_file_path` | str \| None | `None` | File path for Superlinked logs |
| `superlinked_expose_pii` | bool | `False` | Expose PII in Superlinked framework logs |
| `disable_rich_traceback` | bool | `False` | Disable rich/colorful tracebacks |
| `enable_dag_visualization` | bool | `False` | Enable DAG (Directed Acyclic Graph) visualization |
| `dag_visualization_output_dir` | str \| None | `None` | Output directory for DAG visualizations |
| `online_put_chunk_size` | int | `10000` | Chunk size for online data ingestion |
| `query_to_return_origin_id` | bool | `False` | Return original IDs in query results |
| `superlinked_nlq_max_retries` | int | `3` | Max retries for Natural Language Query processing |

**Example:**
```yaml
framework:
  app_id: my_app
  model_cache_dir: ./model_cache
  model_warmup: true
  enable_mps: true  # For Mac M1/M2
  batched_embedding_wait_time_ms: 100
  online_put_chunk_size: 5000
```

**Custom Blob Handler Example:**
```yaml
framework:
  blob_handler_module_path: my_custom_handlers.blob
  blob_handler_class_name: CustomBlobHandler
  blob_handler_class_args:
    bucket_name: my-bucket
    region: us-east-1
```

---

### 3. IMAGE SECTION (`image:`)

Settings for image processing and transformation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `resize_image_width` | int | `224` | Target width for image resizing |
| `resize_image_height` | int | `224` | Target height for image resizing |
| `image_format` | str | `"WebP"` | Output image format (WebP, JPEG, PNG, etc.) |
| `image_quality` | int | `95` | Image quality (0-100, higher=better quality) |

**Example:**
```yaml
image:
  resize_image_width: 512
  resize_image_height: 512
  image_format: JPEG
  image_quality: 85
```

---

### 4. RESOURCE SECTION (`resource:`)

Resource management settings including external message bus and vector database configurations.

#### 4.1 External Message Bus (`resource.external_message_bus:`)

Configure external message queue/bus for asynchronous ingestion.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `queue_module_path` | str \| None | `None` | Python module path for queue implementation |
| `queue_class_name` | str \| None | `None` | Queue class name |
| `queue_class_args` | dict \| None | `None` | Arguments for queue class constructor |
| `ingestion_topic_name` | str \| None | `None` | Topic/queue name for ingestion messages |
| `queue_message_version` | int | `1` | Message format version |

**Note:** All parameters must be set together for proper functionality.

**Example:**
```yaml
resource:
  external_message_bus:
    queue_module_path: my_queues.rabbitmq
    queue_class_name: RabbitMQHandler
    queue_class_args:
      host: localhost
      port: 5672
    ingestion_topic_name: superlinked-ingestion
    queue_message_version: 1
```

#### 4.2 Vector Database (`resource.vector_database:`)

Vector database configuration (primarily Redis-specific settings).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `init_search_indices` | bool | `True` | Initialize search indices on startup |
| `redis_max_connections` | int | `170` | Maximum Redis connection pool size |
| `redis_socket_timeout_seconds` | float \| None | `30.0` | Redis socket read/write timeout |
| `redis_socket_connect_timeout_seconds` | float \| None | `3.0` | Redis connection timeout |
| `redis_health_check_interval_seconds` | float | `30` | Health check interval for Redis connections |
| `redis_retry_on_timeout` | bool | `True` | Retry operations on Redis timeout |
| `redis_default_hybrid_policy` | str \| None | `None` | Default hybrid search policy for Redis |
| `redis_default_batch_size` | int \| None | `250` | Default batch size for Redis operations |

**Example:**
```yaml
resource:
  vector_database:
    init_search_indices: true
    redis_max_connections: 250
    redis_socket_timeout_seconds: 60.0
    redis_health_check_interval_seconds: 15
    redis_default_batch_size: 500
```

---

## Environment Variable Overrides

All configuration parameters can be overridden using environment variables with the following format:

```
{SECTION}__{PARAMETER_NAME}
```

For nested parameters:
```
{SECTION}__{SUBSECTION}__{PARAMETER_NAME}
```

**Examples:**
```bash
# Server settings
export SERVER__SERVER_PORT=9000
export SERVER__API_KEY="secret_key_123"
export SERVER__WORKER_COUNT=8

# Framework settings
export FRAMEWORK__MODEL_CACHE_DIR="/opt/models"
export FRAMEWORK__MODEL_WARMUP=true

# Resource settings
export RESOURCE__VECTOR_DATABASE__REDIS_MAX_CONNECTIONS=300
```

---

## Important Notes & Caveats

### 1. Embedding Model Configuration
**Embedding models are NOT configured in config.yaml.** They are specified in your application code when creating Space objects:

```python
import superlinked as sl

text_space = sl.TextSimilaritySpace(
    text=your_schema.attribute,
    model="sentence-transformers/all-MiniLM-L6-v2"  # Model specified here
)
```

### 2. API Authentication
- Only a **single API key** is supported via `server.api_key`
- The API key must be sent in the `Authorization` header
- Multiple API keys are not natively supported

### 3. CORS Configuration
- **No built-in CORS configuration** exists in the settings
- CORS must be handled at the FastAPI application level if needed

### 4. RecencySpace
- If your indices use `RecencySpace`, you must set `server.disable_recency_space: false`
- The server will fail to start if RecencySpace is found but disabled

### 5. Dockerized Deployment
When `server.is_dockerized: true`:
- Both `server.bucket_name` and `server.bucket_prefix` are **required**
- The server will download application code from GCS on startup

---

## Minimal Configuration Example

```yaml
server:
  app_module_path: superlinked_app
  disable_recency_space: false
```

## Production Configuration Example

```yaml
server:
  app_module_path: superlinked_app
  server_port: 8080
  server_host: 0.0.0.0
  disable_recency_space: false
  api_key: "${API_KEY}"  # Use env var for secrets
  worker_count: 4
  log_level: WARNING
  log_as_json: true
  environment_name: PRODUCTION
  persistence_folder_path: /data/superlinked

  # Monitoring
  sentry_enable: true
  sentry_url: "${SENTRY_DSN}"
  opentelemetry_enable: true
  opentelemetry_collector_endpoint: "otel-collector:4317"

framework:
  model_cache_dir: /opt/models
  model_warmup: true
  batched_embedding_wait_time_ms: 100
  batched_vdb_write_wait_time_ms: 50
  online_put_chunk_size: 5000

image:
  resize_image_width: 512
  resize_image_height: 512
  image_format: WebP
  image_quality: 90

resource:
  vector_database:
    init_search_indices: true
    redis_max_connections: 250
    redis_socket_timeout_seconds: 60.0
    redis_default_batch_size: 500
```

---

## Configuration File Location

The `config.yaml` file must be located in the **current working directory** where you run the `python -m superlinked.server` command.

## Validation

The Pydantic settings system automatically validates:
- Type correctness (int, str, bool, float, dict)
- Required fields
- Value constraints

Invalid configurations will raise errors on server startup with clear error messages.