#!/usr/bin/env python3
"""
Preprocess Amazon grocery product data for Superlinked ingestion.
Converts CSV with product descriptions, prices, and images to Parquet format.
Downloads images to local folder and stores file paths in the Parquet file.
Source: Amazon ML Challenge 2025 dataset (Kaggle)
"""
import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import urllib.request
from functools import partial
import multiprocessing
from tqdm import tqdm


def download_image(row_data, images_folder):
    """
    Download a single image from URL and return file path.

    Args:
        row_data: Tuple of (index, sample_id, image_link)
        images_folder: Path to save images

    Returns:
        Tuple of (sample_id, local_file_path or None, download_success)
    """
    idx, sample_id, image_link = row_data

    if not isinstance(image_link, str) or not image_link.strip():
        return (sample_id, None, False)

    try:
        # Extract filename from URL
        filename = Path(image_link).name
        if not filename:
            filename = f"{sample_id}.jpg"

        image_save_path = images_folder / filename

        # Skip if already downloaded
        if image_save_path.exists():
            return (sample_id, str(image_save_path), True)

        # Download image
        urllib.request.urlretrieve(image_link, image_save_path)
        return (sample_id, str(image_save_path), True)

    except Exception as ex:
        print(f"Warning: Unable to download image for {sample_id}: {ex}")
        return (sample_id, None, False)


def download_images_parallel(df, images_folder, max_workers=50):
    """
    Download images in parallel using multiprocessing.

    Args:
        df: DataFrame with 'sample_id' and 'image_link' columns
        images_folder: Path to save images
        max_workers: Number of parallel workers

    Returns:
        Dictionary mapping sample_id to local file path
    """
    images_folder.mkdir(parents=True, exist_ok=True)

    # Prepare data for parallel processing
    row_data = [
        (idx, row['sample_id'], row['image_link'])
        for idx, row in df.iterrows()
    ]

    download_partial = partial(download_image, images_folder=images_folder)

    results = {}
    failed_count = 0

    print(f"Downloading {len(row_data)} images using {max_workers} workers...")

    with multiprocessing.Pool(max_workers) as pool:
        for sample_id, file_path, success in tqdm(
            pool.imap_unordered(download_partial, row_data),
            total=len(row_data),
            desc="Downloading images"
        ):
            results[sample_id] = file_path
            if not success:
                failed_count += 1

    print(f"Downloaded {len(row_data) - failed_count} images successfully")
    print(f"Failed to download {failed_count} images")

    return results


def process_catalog_content(catalog_content):
    """
    Parse catalog_content field to extract structured information.
    The field contains item name, bullet points, value, and unit.

    Returns a cleaned text string suitable for search/embeddings.
    """
    if not isinstance(catalog_content, str):
        return ""

    # Clean up the text: remove excessive whitespace, newlines
    cleaned = " ".join(catalog_content.split())
    return cleaned


def main():
    """
    Main preprocessing pipeline:
    1. Load CSV data
    2. Download images in parallel
    3. Process catalog content
    4. Generate batched Parquet file with row groups
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Preprocess Amazon grocery product data for Superlinked ingestion"
    )
    parser.add_argument(
        "--nrows",
        type=int,
        default=None,
        help="Number of rows to process (default: all rows)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=50,
        help="Number of parallel workers for image downloads (default: 50)",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="amazon_grocery_data/student_resource/dataset/train.csv",
        help="Input CSV file path",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed_amazon_grocery.parquet",
        help="Output Parquet file path",
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default="data/images_amazon_grocery",
        help="Directory to save downloaded images",
    )

    args = parser.parse_args()

    # Paths (run from project root: python scripts/preprocess_amazon_grocery.py)
    input_csv = Path(args.input)
    output_parquet = Path(args.output)
    images_folder = Path(args.images_dir)

    # Validate input
    if not input_csv.exists():
        print(f"Error: Input file not found: {input_csv}")
        sys.exit(1)

    print(f"Loading data from {input_csv}...")
    if args.nrows:
        print(f"Processing first {args.nrows} rows only")
        df = pd.read_csv(input_csv, nrows=args.nrows)
    else:
        df = pd.read_csv(input_csv)

    print(f"Loaded {len(df)} products")
    print(f"Columns: {df.columns.tolist()}")
    print(f"\nSample data:")
    print(df.head(2))

    # Download images in parallel
    image_paths = download_images_parallel(df, images_folder, max_workers=args.max_workers)

    # Add image paths to dataframe
    df['image_path'] = df['sample_id'].map(image_paths)

    # Process catalog content
    print("\nProcessing catalog content...")
    df['description'] = df['catalog_content'].apply(process_catalog_content)

    # Create final dataset with clean schema
    processed_df = pd.DataFrame({
        'item_id': df['sample_id'].astype(str),
        'description': df['description'].astype(str),
        'price': df['price'].astype(float),
        'image_path': df['image_path'].fillna('').astype(str),
        'image_url': df['image_link'].fillna('').astype(str),
    })

    # Define PyArrow schema for proper types
    schema = pa.schema([
        ('item_id', pa.string()),
        ('description', pa.string()),
        ('price', pa.float64()),
        ('image_path', pa.string()),
        ('image_url', pa.string()),
    ])

    # Convert to PyArrow table
    table = pa.Table.from_pandas(processed_df, schema=schema)

    # Write Parquet with row groups for efficient batched reading
    # Row group size of 10,000 allows chunked processing without loading entire file
    print(f"\nWriting Parquet file to {output_parquet}...")
    output_parquet.parent.mkdir(parents=True, exist_ok=True)

    pq.write_table(
        table,
        output_parquet,
        compression='snappy',
        row_group_size=10000  # Split into 10k-row chunks for batched reading
    )

    # Print summary statistics
    print(f"\n{'='*60}")
    print(f"Preprocessing Complete!")
    print(f"{'='*60}")
    print(f"Total products: {len(processed_df):,}")
    print(f"Products with images: {(processed_df['image_path'] != '').sum():,}")
    print(f"Output file: {output_parquet}")
    print(f"File size: {output_parquet.stat().st_size / (1024*1024):.2f} MB")
    print(f"Images folder: {images_folder}")
    print(f"Images downloaded: {len(list(images_folder.glob('*')))} files")

    # Verify row groups
    parquet_file = pq.ParquetFile(output_parquet)
    print(f"Row groups: {parquet_file.num_row_groups}")

    # Show price statistics
    print(f"\nPrice statistics:")
    print(f"  Min: ${processed_df['price'].min():.2f}")
    print(f"  Max: ${processed_df['price'].max():.2f}")
    print(f"  Mean: ${processed_df['price'].mean():.2f}")
    print(f"  Median: ${processed_df['price'].median():.2f}")

    print(f"\nSample output:")
    print(processed_df.head(3))


if __name__ == "__main__":
    main()
