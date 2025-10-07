#!/usr/bin/env python3
"""
Preprocess Amazon Berkeley Objects data for Superlinked ingestion.
Converts nested JSONL to flat Parquet with proper types and extracted English text fields.
"""
import json
import gzip
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def extract_multilang_value(field, preferred_langs=["en_US", "en_GB", "en_CA"]):
    """Extract value from multilingual field, preferring English."""
    if not field:
        return ""
    if isinstance(field, list):
        # Try preferred languages first
        for lang in preferred_langs:
            for item in field:
                if isinstance(item, dict) and item.get("language_tag") == lang:
                    return item.get("value", "")
        # Fall back to first item with value
        for item in field:
            if isinstance(item, dict) and "value" in item:
                return item.get("value", "")
    return ""


def extract_keywords(keywords_field, preferred_langs=["en_US", "en_GB", "en_CA"]):
    """Extract and join keywords into a single string."""
    if not keywords_field:
        return ""
    keywords = []
    seen = set()

    # Prefer English keywords
    for lang in preferred_langs:
        for item in keywords_field:
            if isinstance(item, dict) and item.get("language_tag") == lang:
                kw = item.get("value", "").strip()
                if kw and kw not in seen:
                    keywords.append(kw)
                    seen.add(kw)

    # Add any remaining unique keywords
    for item in keywords_field:
        if isinstance(item, dict):
            kw = item.get("value", "").strip()
            if kw and kw not in seen:
                keywords.append(kw)
                seen.add(kw)

    return ", ".join(keywords[:20])  # Limit to 20 keywords


def extract_product_type(product_type_field):
    """Extract product type value."""
    if not product_type_field:
        return ""
    if isinstance(product_type_field, list) and len(product_type_field) > 0:
        item = product_type_field[0]
        if isinstance(item, dict):
            return item.get("value", "")
    return ""


def process_listing(raw_data):
    """Convert raw ABO listing to flat structure."""
    return {
        "item_id": raw_data.get("item_id", ""),
        "item_name": extract_multilang_value(raw_data.get("item_name", [])),
        "brand": extract_multilang_value(raw_data.get("brand", [])),
        "product_type": extract_product_type(raw_data.get("product_type", [])),
        "color": extract_multilang_value(raw_data.get("color", [])),
        "product_description": extract_multilang_value(raw_data.get("product_description", [])),
        "item_keywords": extract_keywords(raw_data.get("item_keywords", [])),
        "main_image_id": raw_data.get("main_image_id", ""),
        "country": raw_data.get("country", ""),
        "domain_name": raw_data.get("domain_name", ""),
    }


def main():
    # Run from project root: python scripts/preprocess_amazon_data.py
    input_dir = Path("amazon_objects/listings/metadata")
    output_file = Path("amazon_objects/processed_products.parquet")

    processed_data = []
    seen_ids = set()
    duplicate_count = 0

    # Process all listings_*.json.gz files
    for gz_file in sorted(input_dir.glob("listings_*.json.gz")):
        print(f"Processing {gz_file.name}...")
        with gzip.open(gz_file, "rt", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    raw_data = json.loads(line.strip())
                    processed = process_listing(raw_data)

                    # Only include items with name and unique ID
                    if processed["item_name"] and processed["item_id"]:
                        if processed["item_id"] in seen_ids:
                            duplicate_count += 1
                            continue

                        seen_ids.add(processed["item_id"])
                        processed_data.append(processed)

                except json.JSONDecodeError as e:
                    print(f"  Error in {gz_file.name}:{line_num}: {e}")
                    continue

    # Create DataFrame with proper types
    df = pd.DataFrame(processed_data)

    # Define schema with proper types
    schema = pa.schema([
        ("item_id", pa.string()),
        ("item_name", pa.string()),
        ("brand", pa.string()),
        ("product_type", pa.string()),
        ("color", pa.string()),
        ("product_description", pa.string()),
        ("item_keywords", pa.string()),
        ("main_image_id", pa.string()),
        ("country", pa.string()),
        ("domain_name", pa.string()),
    ])

    # Convert to PyArrow table and write Parquet with row groups for chunked reading
    # Each row group will be ~10,000 rows, allowing efficient chunked processing
    table = pa.Table.from_pandas(df, schema=schema)
    pq.write_table(
        table,
        output_file,
        compression='snappy',
        row_group_size=10000  # Split into row groups for chunked reading
    )

    print(f"\nProcessed {len(processed_data)} unique products -> {output_file}")
    print(f"Skipped {duplicate_count} duplicates")
    print(f"File size: {output_file.stat().st_size / (1024*1024):.2f} MB")

    # Verify row groups
    parquet_file = pq.ParquetFile(output_file)
    print(f"Row groups: {parquet_file.num_row_groups}")


if __name__ == "__main__":
    main()
