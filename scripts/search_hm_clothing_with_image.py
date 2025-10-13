#!/usr/bin/env python3
"""
Search H&M clothing with multi-modal image search.
Demonstrates "find clothing that matches this reference image" use case.

This script uses InMemoryExecutor (like the Superlinked notebook) to enable
direct PIL Image queries, bypassing REST API binary encoding limitations.

Example use cases:
- "Find a shirt that matches this clock" (color/style matching)
- "Find similar clothing to this reference image"
- Multi-modal: text + image combined search
"""
import argparse
import sys
from pathlib import Path
from PIL import Image
import pandas as pd

from superlinked import framework as sl
from datasets import load_dataset


# Configuration
VIT_MODEL_ID = "hf-hub:laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
TEXT_MODEL_ID = "Alibaba-NLP/gte-large-en-v1.5"


def load_hm_data(sample_size=100, seed=42):
    """
    Load H&M fashion dataset from HuggingFace.

    Args:
        sample_size: Number of items to load (None = all 20k)
        seed: Random seed for sampling

    Returns:
        List of dicts with id, description, and image (PIL Image)
    """
    print(f"Loading H&M fashion dataset...")
    fashion_dataset = load_dataset("tomytjandra/h-and-m-fashion-caption", split="train")

    if sample_size:
        print(f"Sampling {sample_size} items from {len(fashion_dataset)} total...")
        fashion_dataset = fashion_dataset.shuffle(seed=seed).select(range(sample_size))
    else:
        print(f"Loading all {len(fashion_dataset)} items...")

    # Convert to list of dicts
    items = []
    for i, item in enumerate(fashion_dataset):
        items.append({
            'id': str(i),
            'description': item['text'],
            'image': item['image']  # PIL Image
        })

    print(f"✓ Loaded {len(items)} clothing items")
    return items


def setup_superlinked(data):
    """
    Setup Superlinked InMemoryExecutor with H&M fashion data.

    Args:
        data: List of dicts with id, description, image

    Returns:
        Tuple of (app, query, schema) for querying
    """
    print("\nSetting up Superlinked InMemoryExecutor...")

    # Define schema
    class ClothingImage(sl.Schema):
        id: sl.IdField
        image: sl.Blob
        description: sl.String

    schema = ClothingImage()

    # Create spaces
    image_space = sl.ImageSpace(
        image=schema.image,
        model=VIT_MODEL_ID,
        model_handler=sl.ModelHandler.OPEN_CLIP
    )

    description_space = sl.TextSimilaritySpace(
        text=schema.description,
        model=TEXT_MODEL_ID
    )

    # Create index
    index = sl.Index([image_space, description_space])

    # Setup executor
    source = sl.InMemorySource(schema)
    executor = sl.InMemoryExecutor(sources=[source], indices=[index])
    app = executor.run()

    # Ingest data
    print(f"Ingesting {len(data)} items...")
    print("⚠️  This may take several minutes (embedding images with Vision Transformer)...")
    source.put(data)
    print("✓ Data ingested successfully")

    # Define query
    query = (
        sl.Query(
            index,
            weights={
                description_space: sl.Param("description_weight"),
                image_space: sl.Param("image_weight"),
            },
        )
        .find(schema)
        .similar(description_space.text, sl.Param("text_search"))
        .similar(image_space.image, sl.Param("image_search"))
        .similar(image_space.description, sl.Param("text_in_image_search"))
        .select_all()
        .limit(sl.Param("limit"))
    )

    return app, query, schema


def search_with_image(app, query, reference_image_path, text_query=None, limit=5):
    """
    Search for clothing items similar to a reference image.

    Args:
        app: Superlinked app (from executor.run())
        query: Query object
        reference_image_path: Path to reference image (e.g., clock.jpg)
        text_query: Optional text to filter results (e.g., "shirt")
        limit: Number of results to return

    Returns:
        pandas DataFrame with results
    """
    # Load reference image
    ref_image = Image.open(reference_image_path)
    print(f"\n{'='*80}")
    print(f"Searching with reference image: {reference_image_path}")
    if text_query:
        print(f"Text filter: '{text_query}'")
    print(f"{'='*80}\n")

    # Build query parameters
    params = {
        'image_search': ref_image,
        'image_weight': 2.0,  # Prioritize image similarity
        'limit': limit
    }

    if text_query:
        params['text_search'] = text_query
        params['description_weight'] = 1.0

    # Execute query
    results = app.query(query, **params)

    # Convert to pandas
    results_df = sl.PandasConverter.to_pandas(results)

    return results_df


def search_with_text_in_image(app, query, text_query, limit=5):
    """
    Search for clothing using text query in image space (CLIP semantic search).

    Args:
        app: Superlinked app
        query: Query object
        text_query: Text describing desired clothing (e.g., "red elegant dress")
        limit: Number of results

    Returns:
        pandas DataFrame with results
    """
    print(f"\n{'='*80}")
    print(f"Semantic image search (CLIP): '{text_query}'")
    print(f"{'='*80}\n")

    results = app.query(
        query,
        text_in_image_search=text_query,
        image_weight=1.0,
        limit=limit
    )

    return sl.PandasConverter.to_pandas(results)


def search_multimodal(app, query, reference_image_path, text_query, limit=5):
    """
    Multi-modal search: combine image + text for best results.

    Args:
        app: Superlinked app
        query: Query object
        reference_image_path: Path to reference image
        text_query: Text query
        limit: Number of results

    Returns:
        pandas DataFrame with results
    """
    ref_image = Image.open(reference_image_path)

    print(f"\n{'='*80}")
    print(f"Multi-modal search:")
    print(f"  Reference image: {reference_image_path}")
    print(f"  Text query: '{text_query}'")
    print(f"{'='*80}\n")

    results = app.query(
        query,
        image_search=ref_image,
        text_search=text_query,
        text_in_image_search=text_query,
        description_weight=1.0,
        image_weight=2.0,
        limit=limit
    )

    return sl.PandasConverter.to_pandas(results)


def display_results(results_df, data):
    """Display search results in a readable format."""
    print(f"Found {len(results_df)} results:\n")

    for idx, row in results_df.iterrows():
        item_id = row['id']
        score = row['_score'] if '_score' in row else 'N/A'

        # Get original item
        original_item = next((item for item in data if item['id'] == item_id), None)

        print(f"Result {idx + 1}:")
        print(f"  ID: {item_id}")
        print(f"  Score: {score}")
        if original_item:
            desc = original_item['description']
            desc_short = desc[:100] + "..." if len(desc) > 100 else desc
            print(f"  Description: {desc_short}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Search H&M clothing with multi-modal image search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Find clothing matching a reference image
  python scripts/search_hm_clothing_with_image.py --image clock.jpg --text "shirt" --limit 5

  # Semantic image search with text only (CLIP)
  python scripts/search_hm_clothing_with_image.py --text-in-image "elegant red dress" --limit 5

  # Multi-modal search (best results)
  python scripts/search_hm_clothing_with_image.py --image watch.jpg --text "elegant shirt" --multimodal --limit 5

  # Use more data (slower but more comprehensive)
  python scripts/search_hm_clothing_with_image.py --sample 1000 --image ref.jpg --text "jacket"
        """
    )

    parser.add_argument(
        "--image",
        type=str,
        help="Path to reference image (e.g., clock.jpg, watch.png)"
    )

    parser.add_argument(
        "--text",
        type=str,
        help="Text query to filter or combine with image search"
    )

    parser.add_argument(
        "--text-in-image",
        type=str,
        help="Text query for semantic image search (CLIP text-to-image)"
    )

    parser.add_argument(
        "--multimodal",
        action="store_true",
        help="Enable multi-modal search (requires --image and --text)"
    )

    parser.add_argument(
        "--sample",
        type=int,
        default=100,
        help="Number of clothing items to load (default: 100, use None for all 20k)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of results to return (default: 5)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.image and not args.text_in_image:
        print("Error: Must provide either --image or --text-in-image")
        sys.exit(1)

    if args.multimodal and (not args.image or not args.text):
        print("Error: --multimodal requires both --image and --text")
        sys.exit(1)

    # Load data
    data = load_hm_data(sample_size=args.sample)

    # Setup Superlinked
    app, query, schema = setup_superlinked(data)

    # Execute search based on mode
    if args.multimodal:
        results_df = search_multimodal(app, query, args.image, args.text, args.limit)
    elif args.text_in_image:
        results_df = search_with_text_in_image(app, query, args.text_in_image, args.limit)
    elif args.image:
        results_df = search_with_image(app, query, args.image, args.text, args.limit)

    # Display results
    display_results(results_df, data)

    print(f"\n{'='*80}")
    print("Search complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
