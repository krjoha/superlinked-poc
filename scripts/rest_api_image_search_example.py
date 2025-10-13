#!/usr/bin/env python3
"""
Example: Image search via REST API with base64 encoding.

Demonstrates how to:
1. Ingest clothing items with images via REST API
2. Search using reference images (e.g., "find shirt matching watch")
3. Use base64 encoding for binary image data

This script uses the REST API (production approach) instead of InMemoryExecutor.
"""
import argparse
import base64
import json
import sys
from pathlib import Path
from PIL import Image
import io
import requests


API_BASE_URL = "http://localhost:8080"
INGEST_ENDPOINT = f"{API_BASE_URL}/api/v1/ingest/hm_clothing_schema"
SEARCH_ENDPOINT = f"{API_BASE_URL}/api/v1/search/hm_clothing_search"


def image_to_base64(image_path_or_bytes):
    """
    Convert image to base64 string.

    Args:
        image_path_or_bytes: Path to image file or bytes

    Returns:
        Base64-encoded string
    """
    if isinstance(image_path_or_bytes, (str, Path)):
        # Load from file
        img = Image.open(image_path_or_bytes)
        buffer = io.BytesIO()
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(buffer, format='JPEG')
        image_bytes = buffer.getvalue()
    else:
        # Already bytes
        image_bytes = image_path_or_bytes

    return base64.b64encode(image_bytes).decode('utf-8')


def ingest_clothing_item(item_id, description, image_path_or_bytes, api_key=None):
    """
    Ingest a clothing item via REST API.

    Args:
        item_id: Unique identifier
        description: Text description
        image_path_or_bytes: Path to image or image bytes
        api_key: Optional API key for authentication

    Returns:
        Response object
    """
    # Convert image to base64
    base64_image = image_to_base64(image_path_or_bytes)

    # Prepare payload
    payload = {
        "item_id": item_id,
        "description": description,
        "image": base64_image
    }

    # Prepare headers
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = api_key

    # Send request
    response = requests.post(INGEST_ENDPOINT, json=payload, headers=headers)

    return response


def search_with_image(reference_image_path, text_query=None, description_weight=1.0,
                      image_weight=2.0, limit=5, api_key=None):
    """
    Search for clothing items using reference image.

    Args:
        reference_image_path: Path to reference image
        text_query: Optional text filter
        description_weight: Weight for text similarity
        image_weight: Weight for image similarity
        limit: Number of results
        api_key: Optional API key

    Returns:
        List of result entries
    """
    # Convert reference image to base64
    base64_image = image_to_base64(reference_image_path)

    # Build query payload
    payload = {
        "image_search": base64_image,
        "image_weight": image_weight,
        "limit": limit
    }

    if text_query:
        payload["text_search"] = text_query
        payload["description_weight"] = description_weight

    # Prepare headers
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = api_key

    # Send request
    response = requests.post(SEARCH_ENDPOINT, json=payload, headers=headers)
    response.raise_for_status()

    return response.json().get('entries', [])


def search_with_text_in_image(text_query, image_weight=1.0, limit=5, api_key=None):
    """
    Semantic text-to-image search using CLIP.

    Args:
        text_query: Natural language description
        image_weight: Weight for image space
        limit: Number of results
        api_key: Optional API key

    Returns:
        List of result entries
    """
    payload = {
        "text_in_image_search": text_query,
        "image_weight": image_weight,
        "limit": limit
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = api_key

    response = requests.post(SEARCH_ENDPOINT, json=payload, headers=headers)
    response.raise_for_status()

    return response.json().get('entries', [])


def main():
    parser = argparse.ArgumentParser(
        description="Image search via REST API with base64 encoding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  # Ingest clothing items from Parquet file
  python scripts/rest_api_image_search_example.py ingest --parquet data/processed_hm_clothing_1k.parquet --count 10

  # Search with reference image (e.g., "find shirt matching this watch")
  python scripts/rest_api_image_search_example.py search --image /tmp/watch.jpg --text "shirt" --limit 5

  # Semantic text-to-image search (CLIP)
  python scripts/rest_api_image_search_example.py search --text-in-image "elegant blue dress" --limit 5

  # Multi-modal search (image + text)
  python scripts/rest_api_image_search_example.py search --image /tmp/watch.jpg --text "elegant shirt" --limit 5
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest clothing items')
    ingest_parser.add_argument('--parquet', type=str, required=True, help='Path to Parquet file')
    ingest_parser.add_argument('--count', type=int, default=10, help='Number of items to ingest')
    ingest_parser.add_argument('--api-key', type=str, help='API key for authentication')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for clothing items')
    search_parser.add_argument('--image', type=str, help='Path to reference image')
    search_parser.add_argument('--text', type=str, help='Text query filter')
    search_parser.add_argument('--text-in-image', type=str, help='Text query for CLIP semantic search')
    search_parser.add_argument('--description-weight', type=float, default=1.0, help='Text weight')
    search_parser.add_argument('--image-weight', type=float, default=2.0, help='Image weight')
    search_parser.add_argument('--limit', type=int, default=5, help='Number of results')
    search_parser.add_argument('--api-key', type=str, help='API key for authentication')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'ingest':
        # Ingest items from Parquet
        import pyarrow.parquet as pq

        print(f"Loading {args.count} items from {args.parquet}...")
        parquet_file = pq.ParquetFile(args.parquet)
        table = parquet_file.read_row_group(0, columns=['item_id', 'description', 'image'])
        df = table.to_pandas()

        for i in range(min(args.count, len(df))):
            item = df.iloc[i]
            print(f"Ingesting item {i+1}/{args.count}: {item['item_id']}")

            response = ingest_clothing_item(
                item_id=item['item_id'],
                description=item['description'],
                image_path_or_bytes=item['image'],
                api_key=args.api_key
            )

            if response.status_code == 202:
                print(f"  ✓ Accepted (status 202)")
            else:
                print(f"  ✗ Failed: {response.status_code} - {response.text}")

        print(f"\n✓ Ingested {args.count} items successfully")
        print("Waiting 5 seconds for indexing...")
        import time
        time.sleep(5)
        print("Ready to search!")

    elif args.command == 'search':
        if args.text_in_image:
            # Text-to-image search
            print(f"Searching with text-in-image: '{args.text_in_image}'")
            results = search_with_text_in_image(
                text_query=args.text_in_image,
                image_weight=args.image_weight,
                limit=args.limit,
                api_key=args.api_key
            )
        elif args.image:
            # Image search (with optional text)
            print(f"Searching with reference image: {args.image}")
            if args.text:
                print(f"Text filter: '{args.text}'")
            results = search_with_image(
                reference_image_path=args.image,
                text_query=args.text,
                description_weight=args.description_weight,
                image_weight=args.image_weight,
                limit=args.limit,
                api_key=args.api_key
            )
        else:
            print("Error: Must provide either --image or --text-in-image")
            sys.exit(1)

        # Display results
        print(f"\nFound {len(results)} results:\n")
        for i, entry in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  ID: {entry['id']}")
            print(f"  Score: {entry['metadata']['score']:.4f}")
            desc = entry['fields']['description']
            desc_short = desc[:100] + "..." if len(desc) > 100 else desc
            print(f"  Description: {desc_short}")
            print()


if __name__ == "__main__":
    main()
