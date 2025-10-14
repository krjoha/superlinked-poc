#!/usr/bin/env python3
"""
Analyze H&M fashion clothing data to understand product descriptions and patterns.
Helps determine what to search for when testing the clothing API.
"""
import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from collections import Counter
import re


def extract_clothing_attributes(description):
    """
    Extract clothing attributes from description.
    Looks for colors, styles, garment types, and materials.
    """
    desc_lower = description.lower()

    attributes = {
        'colors': [],
        'garment_types': [],
        'styles': [],
        'materials': []
    }

    # Color patterns
    color_patterns = [
        r'\b(black|white|grey|gray|blue|red|green|yellow|pink|purple|orange|brown|beige|navy|khaki|burgundy|turquoise|olive|cream|ivory)\b',
    ]

    # Garment type patterns
    garment_patterns = [
        r'\b(dress|dresses|top|tops|blouse|shirt|t-shirt|tee|sweater|cardigan|jacket|coat|jeans|trousers|pants|shorts|skirt|leggings|tights)\b',
        r'\b(suit|blazer|hoodie|sweatshirt|jumpsuit|romper|vest|parka|pullover|tank|cami|tunic)\b',
    ]

    # Style patterns
    style_patterns = [
        r'\b(casual|formal|elegant|sporty|fitted|loose|oversized|slim|skinny|straight|flared|wide)\b',
        r'\b(high-waist|low-waist|cropped|mini|midi|maxi|long|short|sleeveless|long-sleeved|short-sleeved)\b',
        r'\b(v-neck|crew-neck|round-neck|collar|hooded|patterned|striped|printed|solid|plain)\b',
    ]

    # Material patterns
    material_patterns = [
        r'\b(cotton|denim|linen|silk|wool|leather|suede|velvet|satin|chiffon|jersey|knit|knitted)\b',
        r'\b(polyester|nylon|spandex|elastane|fleece|corduroy|tweed|flannel|lace|mesh)\b',
    ]

    # Extract colors
    for pattern in color_patterns:
        matches = re.findall(pattern, desc_lower)
        attributes['colors'].extend(matches)

    # Extract garment types
    for pattern in garment_patterns:
        matches = re.findall(pattern, desc_lower)
        attributes['garment_types'].extend(matches)

    # Extract styles
    for pattern in style_patterns:
        matches = re.findall(pattern, desc_lower)
        attributes['styles'].extend(matches)

    # Extract materials
    for pattern in material_patterns:
        matches = re.findall(pattern, desc_lower)
        attributes['materials'].extend(matches)

    return attributes


def analyze_parquet(file_path, sample_size=None):
    """
    Analyze the H&M clothing parquet file and generate statistics.

    Args:
        file_path: Path to parquet file
        sample_size: Number of rows to analyze (None = all)
    """
    print(f"\n{'='*80}")
    print(f"H&M Fashion Clothing Data Analysis")
    print(f"{'='*80}\n")

    # Read parquet file
    print(f"Reading data from {file_path}...")
    table = pq.read_table(file_path)
    df = table.to_pandas()

    if sample_size:
        print(f"Analyzing sample of {sample_size} items...")
        df = df.head(sample_size)
    else:
        print(f"Analyzing all {len(df)} items...")

    # Basic statistics
    print(f"\n{'─'*80}")
    print("BASIC STATISTICS")
    print(f"{'─'*80}")
    print(f"Total clothing items: {len(df):,}")
    print(f"Items with images: {len(df):,} (100%)")  # All items have images

    # Calculate average image size
    avg_image_size = df['image'].apply(len).mean()
    total_image_size = df['image'].apply(len).sum()
    print(f"Average image size: {avg_image_size / 1024:.1f} KB")
    print(f"Total image data: {total_image_size / (1024*1024):.1f} MB")

    # Description length statistics
    print(f"\n{'─'*80}")
    print("DESCRIPTION LENGTH STATISTICS")
    print(f"{'─'*80}")
    desc_lengths = df['description'].str.len()
    print(f"Min length:    {desc_lengths.min()} characters")
    print(f"Max length:    {desc_lengths.max()} characters")
    print(f"Mean length:   {desc_lengths.mean():.0f} characters")
    print(f"Median length: {desc_lengths.median():.0f} characters")

    # Extract attributes from descriptions
    print(f"\n{'─'*80}")
    print("CLOTHING ATTRIBUTE ANALYSIS")
    print(f"{'─'*80}")
    print("Extracting attributes from descriptions...")

    all_colors = []
    all_garments = []
    all_styles = []
    all_materials = []

    for desc in df['description']:
        attrs = extract_clothing_attributes(desc)
        all_colors.extend(attrs['colors'])
        all_garments.extend(attrs['garment_types'])
        all_styles.extend(attrs['styles'])
        all_materials.extend(attrs['materials'])

    # Color analysis
    print(f"\n{'─'*80}")
    print("TOP COLORS")
    print(f"{'─'*80}")
    color_counts = Counter(all_colors)
    print(f"{'Color':<20s} {'Count':>8s} {'Coverage':>10s}")
    print(f"{'-'*20} {'-'*8} {'-'*10}")
    for color, count in color_counts.most_common(15):
        pct = (count / len(df)) * 100
        print(f"{color:<20s} {count:>8,} {pct:>9.1f}%")

    # Garment type analysis
    print(f"\n{'─'*80}")
    print("TOP GARMENT TYPES")
    print(f"{'─'*80}")
    garment_counts = Counter(all_garments)
    print(f"{'Garment Type':<20s} {'Count':>8s} {'Coverage':>10s}")
    print(f"{'-'*20} {'-'*8} {'-'*10}")
    for garment, count in garment_counts.most_common(15):
        pct = (count / len(df)) * 100
        print(f"{garment:<20s} {count:>8,} {pct:>9.1f}%")

    # Style analysis
    print(f"\n{'─'*80}")
    print("TOP STYLE ATTRIBUTES")
    print(f"{'─'*80}")
    style_counts = Counter(all_styles)
    print(f"{'Style':<20s} {'Count':>8s} {'Coverage':>10s}")
    print(f"{'-'*20} {'-'*8} {'-'*10}")
    for style, count in style_counts.most_common(15):
        pct = (count / len(df)) * 100
        print(f"{style:<20s} {count:>8,} {pct:>9.1f}%")

    # Material analysis
    print(f"\n{'─'*80}")
    print("TOP MATERIALS")
    print(f"{'─'*80}")
    material_counts = Counter(all_materials)
    print(f"{'Material':<20s} {'Count':>8s} {'Coverage':>10s}")
    print(f"{'-'*20} {'-'*8} {'-'*10}")
    for material, count in material_counts.most_common(15):
        pct = (count / len(df)) * 100
        print(f"{material:<20s} {count:>8,} {pct:>9.1f}%")

    # Sample descriptions by popular combinations
    print(f"\n{'─'*80}")
    print("SAMPLE SEARCH QUERIES")
    print(f"{'─'*80}\n")

    # Create sample queries from popular attributes
    top_colors = [c for c, _ in color_counts.most_common(5)]
    top_garments = [g for g, _ in garment_counts.most_common(5)]
    top_styles = [s for s, _ in style_counts.most_common(5) if s in ['fitted', 'loose', 'slim', 'oversized', 'elegant']]

    suggestions = []

    # Color + garment queries
    for i, (color, garment) in enumerate(zip(top_colors[:3], top_garments[:3]), 1):
        suggestions.append({
            'type': 'Text-in-text search',
            'query': f"{color} {garment}",
            'description': f"Search for {color} {garment} in descriptions"
        })

    # Style + garment queries
    for i, (style, garment) in enumerate(zip(top_styles[:2], top_garments[3:5]), 1):
        suggestions.append({
            'type': 'Text-in-image search (CLIP)',
            'query': f"{style} {garment}",
            'description': f"Semantic image search for {style} {garment}"
        })

    print("Try these search queries with the API:\n")
    for i, sugg in enumerate(suggestions[:5], 1):
        print(f"{i}. {sugg['type']}: '{sugg['query']}'")
        print(f"   Description: {sugg['description']}")

        if 'text-in-image' in sugg['type'].lower():
            print(f"   Example curl command:")
            print(f"     curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \\")
            print(f"       -H 'Content-Type: application/json' \\")
            print(f"       -H 'Authorization: your-api-key-here' \\")
            print(f"       -d '{{")
            print(f"         \"text_in_image_search\": \"{sugg['query']}\",")
            print(f"         \"image_weight\": 1.0,")
            print(f"         \"limit\": 5")
            print(f"       }}'")
        else:
            print(f"   Example curl command:")
            print(f"     curl -X POST http://localhost:8080/api/v1/search/hm_clothing_search \\")
            print(f"       -H 'Content-Type: application/json' \\")
            print(f"       -H 'Authorization: your-api-key-here' \\")
            print(f"       -d '{{")
            print(f"         \"text_search\": \"{sugg['query']}\",")
            print(f"         \"description_weight\": 1.0,")
            print(f"         \"limit\": 5")
            print(f"       }}'")
        print()

    # Sample items
    print(f"\n{'─'*80}")
    print("SAMPLE CLOTHING ITEMS")
    print(f"{'─'*80}\n")

    sample_items = df.head(5)
    for idx, row in sample_items.iterrows():
        desc = row['description'][:150] + "..." if len(row['description']) > 150 else row['description']
        image_size_kb = len(row['image']) / 1024
        print(f"Item {row['item_id']}:")
        print(f"  Description: {desc}")
        print(f"  Image size: {image_size_kb:.1f} KB")
        print()

    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze H&M fashion clothing data to understand attributes and patterns"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Input Parquet file path (default: auto-select based on USE_TEST_DATA)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=None,
        help="Analyze only first N items (default: all)",
    )

    args = parser.parse_args()

    # Auto-select file based on USE_TEST_DATA env variable
    if args.input:
        input_file = Path(args.input)
    else:
        use_test_data = os.environ.get('USE_TEST_DATA', '0') == '1'
        if use_test_data:
            input_file = Path("data/processed_hm_clothing_1k.parquet")
        else:
            input_file = Path("data/processed_hm_clothing.parquet")

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    analyze_parquet(input_file, sample_size=args.sample)


if __name__ == "__main__":
    main()
