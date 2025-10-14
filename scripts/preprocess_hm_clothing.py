#!/usr/bin/env python3
"""
Preprocess H&M fashion clothing data for Superlinked ingestion.
Converts HuggingFace dataset with images and text to Parquet format.
Source: tomytjandra/h-and-m-fashion-caption dataset (20,491 items)
"""
import argparse
import base64
import io
import sys
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datasets import load_dataset
from PIL import Image


def image_to_base64(pil_image: Image.Image) -> str:
    """
    Convert PIL Image to base64-encoded string for Blob storage.
    Superlinked DataLoaderSource expects strings (base64) or PIL Images for Blob fields.

    Args:
        pil_image: PIL Image object

    Returns:
        Image data as base64-encoded string (JPEG format)
    """
    buffer = io.BytesIO()
    # Convert to RGB if necessary (some images might be RGBA or grayscale)
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    pil_image.save(buffer, format='JPEG', quality=85)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def main():
    """
    Main preprocessing pipeline:
    1. Load H&M fashion dataset from HuggingFace
    2. Convert images to bytes
    3. Generate batched Parquet file with row groups
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Preprocess H&M fashion clothing data for Superlinked ingestion"
    )
    parser.add_argument(
        "--nrows",
        type=int,
        default=None,
        help="Number of rows to process (default: all ~20k rows)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed_hm_clothing.parquet",
        help="Output Parquet file path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling (default: 42)",
    )

    args = parser.parse_args()

    output_parquet = Path(args.output)

    print(f"Loading H&M fashion dataset from HuggingFace...")
    print(f"(First download may take several minutes - ~6GB)")

    # Load the H&M fashion caption dataset
    fashion_dataset = load_dataset("tomytjandra/h-and-m-fashion-caption", split="train")

    # Sample or use full dataset
    if args.nrows and args.nrows < len(fashion_dataset):
        print(f"Sampling {args.nrows} rows from {len(fashion_dataset)} total items...")
        fashion_dataset = fashion_dataset.shuffle(seed=args.seed).select(range(args.nrows))
    else:
        print(f"Processing all {len(fashion_dataset)} items...")

    print(f"Loaded {len(fashion_dataset)} fashion items")

    # Convert to list of dicts for processing
    print("\nConverting images to base64 strings...")
    processed_items = []

    for i, item in enumerate(fashion_dataset):
        if i % 1000 == 0:
            print(f"  Processed {i}/{len(fashion_dataset)} items...")

        # Convert PIL Image to base64 string (required by Superlinked DataLoader)
        image_base64 = image_to_base64(item['image'])

        processed_items.append({
            'item_id': str(i),  # Generate sequential IDs
            'description': item['text'],
            'image': image_base64,
        })

    # Create DataFrame
    df = pd.DataFrame(processed_items)

    print(f"\nProcessed {len(df)} items")
    print(f"Sample descriptions:")
    for desc in df['description'].head(3):
        print(f"  - {desc}")

    # Define PyArrow schema for proper types
    schema = pa.schema([
        ('item_id', pa.string()),
        ('description', pa.string()),
        ('image', pa.string()),  # Blob data stored as base64 string
    ])

    # Convert to PyArrow table
    table = pa.Table.from_pandas(df, schema=schema)

    # Write Parquet with row groups for efficient batched reading
    print(f"\nWriting Parquet file to {output_parquet}...")
    output_parquet.parent.mkdir(parents=True, exist_ok=True)

    pq.write_table(
        table,
        output_parquet,
        compression='snappy',
        row_group_size=1000  # Smaller row groups due to large image data
    )

    # Print summary statistics
    print(f"\n{'='*60}")
    print(f"Preprocessing Complete!")
    print(f"{'='*60}")
    print(f"Total items: {len(df):,}")
    print(f"Output file: {output_parquet}")
    print(f"File size: {output_parquet.stat().st_size / (1024*1024):.2f} MB")

    # Verify row groups
    parquet_file = pq.ParquetFile(output_parquet)
    print(f"Row groups: {parquet_file.num_row_groups}")

    # Show description length statistics
    desc_lengths = df['description'].str.len()
    print(f"\nDescription length statistics:")
    print(f"  Min: {desc_lengths.min()} characters")
    print(f"  Max: {desc_lengths.max()} characters")
    print(f"  Mean: {desc_lengths.mean():.0f} characters")
    print(f"  Median: {desc_lengths.median():.0f} characters")

    print(f"\nSample output:")
    print(df[['item_id', 'description']].head(3))


if __name__ == "__main__":
    main()
