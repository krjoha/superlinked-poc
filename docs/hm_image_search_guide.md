# H&M Fashion Image Search Guide

## Overview

This guide demonstrates how to perform multi-modal image search on the H&M fashion clothing dataset. The system supports three search modes:

1. **Image-to-image search**: Find clothing that visually matches a reference image
2. **Text-to-image search (CLIP)**: Semantic search using natural language descriptions
3. **Multi-modal search**: Combine image and text for best results

## Use Cases

### "Find a Shirt That Matches This Watch"

Search for clothing items that match the visual style, color, or aesthetic of a reference object (e.g., a watch, piece of furniture, artwork).

**Example:**
```bash
python scripts/search_hm_clothing_with_image.py \
  --image /path/to/watch.jpg \
  --text "shirt" \
  --limit 5
```

**Results:** The system will find shirts with similar:
- Colors (blue gradient from watch face)
- Style (elegant, formal aesthetic)
- Visual properties (metallic tones, dark accents)

### Search by Style Description

Find clothing based on natural language descriptions using CLIP's semantic understanding:

```bash
python scripts/search_hm_clothing_with_image.py \
  --text-in-image "elegant red evening dress" \
  --limit 5
```

### Multi-Modal Search (Best Results)

Combine a reference image with text description for most accurate results:

```bash
python scripts/search_hm_clothing_with_image.py \
  --image /path/to/reference.jpg \
  --text "casual summer dress" \
  --multimodal \
  --limit 5
```

## Helper Script Reference

### Command Line Options

**`search_hm_clothing_with_image.py`** - InMemoryExecutor-based image search

```bash
python scripts/search_hm_clothing_with_image.py [OPTIONS]
```

**Options:**

- `--image PATH` - Path to reference image for image-to-image search
- `--text TEXT` - Text query to filter or combine with image search
- `--text-in-image TEXT` - Text query for CLIP semantic image search
- `--multimodal` - Enable multi-modal search (requires --image and --text)
- `--sample N` - Number of clothing items to load (default: 100)
- `--limit N` - Number of results to return (default: 5)

### Examples

#### 1. Image Search with Text Filter
```bash
python scripts/search_hm_clothing_with_image.py \
  --image /tmp/watch.jpg \
  --text "shirt" \
  --limit 5
```

**What it does:**
- Embeds the reference image using CLIP Vision Transformer
- Finds visually similar clothing items
- Filters results to shirt category using text similarity

#### 2. Semantic Text-to-Image Search
```bash
python scripts/search_hm_clothing_with_image.py \
  --text-in-image "black elegant dress" \
  --limit 5
```

**What it does:**
- Uses CLIP's text encoder to search in image embedding space
- Finds images semantically matching the description
- No reference image needed

#### 3. Multi-Modal Search
```bash
python scripts/search_hm_clothing_with_image.py \
  --image /tmp/watch.jpg \
  --text "elegant blue shirt" \
  --multimodal \
  --limit 5
```

**What it does:**
- Combines image similarity (weight: 2.0) + text similarity (weight: 1.0)
- Best for precise matching with style constraints

#### 4. Large Dataset Search
```bash
python scripts/search_hm_clothing_with_image.py \
  --sample 1000 \
  --image /tmp/reference.jpg \
  --text "summer dress" \
  --limit 10
```

**What it does:**
- Loads 1000 random clothing items
- More comprehensive search results
- Takes longer due to image embedding

## Technical Details

### Models Used

- **Vision Transformer**: `laion/CLIP-ViT-H-14-laion2B-s32B-b79K` (~1GB)
  - Multi-modal model trained on image-text pairs
  - Understands visual concepts and semantic relationships

- **Text Model**: `Alibaba-NLP/gte-large-en-v1.5`
  - High-quality text embeddings for description matching

### How It Works

1. **Data Loading**: Loads H&M fashion dataset from HuggingFace (cached after first run)
2. **InMemoryExecutor Setup**: Creates in-process vector database with indices
3. **Image Embedding**: Converts reference images to CLIP embeddings
4. **Vector Search**: Finds nearest neighbors in embedding space
5. **Result Ranking**: Combines similarity scores with configurable weights

### Performance Notes

- **First run**: Downloads ~6GB H&M dataset (cached locally)
- **Model download**: CLIP ViT-H-14 (~1GB) cached in `~/.cache/sentence-transformers`
- **Embedding time**: ~1 second per image with CLIP ViT-H-14
- **Sample size impact**: 100 items = ~2 minutes, 1000 items = ~15 minutes

### Why InMemoryExecutor?

The helper script uses `InMemoryExecutor` instead of the REST API because:

1. **Direct PIL Image support**: Can pass `PIL.Image` objects directly
2. **No JSON encoding**: Avoids base64/hex encoding overhead
3. **Faster iteration**: Immediate feedback during development
4. **Notebook-style workflow**: Similar to Superlinked documentation examples

## REST API Image Search (Production)

For production use, images must be sent via the REST API using base64 encoding.

### REST API Endpoints

**Ingest endpoint:**
```
POST /api/v1/ingest/hm_clothing_schema
```

**Search endpoint:**
```
POST /api/v1/search/hm_clothing_search
```

**Data loader (bulk ingestion):**
```
POST /data-loader/hm_clothing_loader/run
```

### Image Encoding: Base64

**Solution:** Binary image data is encoded as base64 strings for JSON compatibility.

**Ingest Example:**
```bash
python scripts/rest_api_image_search_example.py ingest \
  --parquet data/processed_hm_clothing_1k.parquet \
  --count 10
```

**Search Example (Find shirt matching watch):**
```bash
python scripts/rest_api_image_search_example.py search \
  --image /tmp/watch.jpg \
  --text "shirt" \
  --limit 5
```

### Query Parameters

- `text_search` - Text query for description matching
- `text_in_image_search` - Text query in image embeddings (CLIP)
- `image_search` - Base64-encoded image data
- `description_weight` - Weight for text similarity (default: 1.0)
- `image_weight` - Weight for image similarity (default: 2.0)
- `limit` - Maximum results

### Python API Example

```python
import base64
import requests
from PIL import Image
import io

# Convert image to base64
img = Image.open('/tmp/watch.jpg')
buffer = io.BytesIO()
img.save(buffer, format='JPEG')
img_bytes = buffer.getvalue()
base64_str = base64.b64encode(img_bytes).decode('utf-8')

# Search with image
response = requests.post(
    "http://localhost:8080/api/v1/search/hm_clothing_search",
    json={
        "image_search": base64_str,
        "text_search": "shirt",
        "description_weight": 1.0,
        "image_weight": 2.0,
        "limit": 5
    }
)

results = response.json()['entries']
for entry in results:
    print(f"ID: {entry['id']}, Score: {entry['metadata']['score']:.4f}")
    print(f"Description: {entry['fields']['description']}")
```

### curl Example

```bash
# 1. Convert image to base64
BASE64_IMAGE=$(base64 -w 0 /tmp/watch.jpg)

# 2. Search with curl
curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \
  -H "Content-Type: application/json" \
  -d "{
    \"image_search\": \"$BASE64_IMAGE\",
    \"text_search\": \"shirt\",
    \"description_weight\": 1.0,
    \"image_weight\": 2.0,
    \"limit\": 5
  }"
```

### Performance Notes

- Base64 encoding increases payload size by ~33%
- Example: 120KB JPEG → 160KB base64 string
- No significant performance impact for typical clothing images
- Consider compression or CDN for large-scale deployments

## Data Analysis

To understand what's in the dataset and generate sample queries:

```bash
# Analyze full dataset
USE_TEST_DATA=0 python scripts/analyze_hm_clothing.py

# Analyze test dataset (1k items)
USE_TEST_DATA=1 python scripts/analyze_hm_clothing.py
```

**Output includes:**
- Top colors (black 42%, white 16%, blue 12%)
- Top garment types (tops 35%, dresses 20%, shirts 18%)
- Top styles (long-sleeved, short-sleeved, fitted)
- Top materials (jersey 23%, cotton 16%, knit 9%)
- Sample search queries with curl commands

## Next Steps

1. ✅ Helper script with InMemoryExecutor (completed)
2. 🔄 REST API image upload investigation (in progress)
3. ⏳ Production deployment with RestExecutor
4. ⏳ Add Natural Language Query (NLQ) support (requires OpenAI API key)

## Troubleshooting

### Model Download Fails
```
Error: HTTP timeout downloading model
```

**Solution:** Increase timeout or use smaller model:
```python
# In search_hm_clothing_with_image.py
VIT_MODEL_ID = "hf-hub:openai/clip-vit-base-patch32"  # 150MB instead of 1GB
```

### Out of Memory
```
Error: CUDA out of memory
```

**Solution:** Reduce sample size:
```bash
python scripts/search_hm_clothing_with_image.py --sample 50 --image ref.jpg
```

### Slow Embedding
**Symptom:** Takes >5 minutes to embed 100 images

**Solution:**
- Use GPU if available (automatic with PyTorch + CUDA)
- Reduce sample size
- Consider using smaller CLIP model for development

## References

- H&M Fashion Dataset: https://huggingface.co/datasets/tomytjandra/h-and-m-fashion-caption
- CLIP Model: https://huggingface.co/laion/CLIP-ViT-H-14-laion2B-s32B-b79K
- Superlinked Docs: https://docs.superlinked.com
