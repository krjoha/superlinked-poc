#!/usr/bin/env python3
"""
Analyze Amazon product data to understand product categories and price ranges.
Helps determine what to search for when testing the API.
"""
import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from collections import Counter
import re


def extract_category_keywords(description):
    """
    Extract potential product category keywords from description.
    Looks for common product type words.
    """
    # Common product category keywords
    category_patterns = [
        r'\b(laptop|computer|tablet|phone|electronics?)\b',
        r'\b(shirt|pants|dress|clothing|apparel|shoes?|boots?)\b',
        r'\b(book|novel|magazine|publication)\b',
        r'\b(toy|game|puzzle|doll)\b',
        r'\b(kitchen|cookware|utensil|appliance)\b',
        r'\b(furniture|chair|table|desk|bed)\b',
        r'\b(food|snack|cookie|sauce|beverage|drink)\b',
        r'\b(beauty|cosmetic|makeup|skincare)\b',
        r'\b(tool|hardware|equipment)\b',
        r'\b(jewelry|watch|accessory|accessories)\b',
        r'\b(sports?|fitness|exercise|outdoor)\b',
        r'\b(pet|dog|cat|animal)\b',
        r'\b(baby|infant|toddler|kids?)\b',
        r'\b(health|vitamin|supplement|medical)\b',
        r'\b(home|garden|decor|decoration)\b',
    ]

    categories = []
    desc_lower = description.lower()

    for pattern in category_patterns:
        matches = re.findall(pattern, desc_lower)
        categories.extend(matches)

    return categories


def analyze_parquet(file_path, sample_size=None):
    """
    Analyze the parquet file and generate statistics.

    Args:
        file_path: Path to parquet file
        sample_size: Number of rows to analyze (None = all)
    """
    print(f"\n{'='*80}")
    print(f"Amazon Product Data Analysis")
    print(f"{'='*80}\n")

    # Read parquet file
    print(f"Reading data from {file_path}...")
    table = pq.read_table(file_path)
    df = table.to_pandas()

    if sample_size:
        print(f"Analyzing sample of {sample_size} products...")
        df = df.head(sample_size)
    else:
        print(f"Analyzing all {len(df)} products...")

    # Basic statistics
    print(f"\n{'─'*80}")
    print("BASIC STATISTICS")
    print(f"{'─'*80}")
    print(f"Total products: {len(df):,}")
    print(f"Products with images: {(df['image_path'] != '').sum():,}")
    print(f"Products without images: {(df['image_path'] == '').sum():,}")

    # Price statistics
    print(f"\n{'─'*80}")
    print("PRICE STATISTICS")
    print(f"{'─'*80}")
    print(f"Min price:    ${df['price'].min():.2f}")
    print(f"Max price:    ${df['price'].max():.2f}")
    print(f"Mean price:   ${df['price'].mean():.2f}")
    print(f"Median price: ${df['price'].median():.2f}")

    # Price ranges
    print(f"\n{'─'*80}")
    print("PRICE DISTRIBUTION")
    print(f"{'─'*80}")
    price_ranges = [
        ("Under $10", 0, 10),
        ("$10 - $25", 10, 25),
        ("$25 - $50", 25, 50),
        ("$50 - $100", 50, 100),
        ("$100 - $250", 100, 250),
        ("$250 - $500", 250, 500),
        ("$500 - $1000", 500, 1000),
        ("Over $1000", 1000, float('inf'))
    ]

    for label, min_price, max_price in price_ranges:
        count = ((df['price'] >= min_price) & (df['price'] < max_price)).sum()
        pct = (count / len(df)) * 100
        print(f"{label:20s}: {count:6,} products ({pct:5.1f}%)")

    # Extract categories from descriptions
    print(f"\n{'─'*80}")
    print("CATEGORY ANALYSIS (based on description keywords)")
    print(f"{'─'*80}")
    print("Extracting categories from descriptions...")

    all_categories = []
    for desc in df['description']:
        categories = extract_category_keywords(desc)
        all_categories.extend(categories)

    category_counts = Counter(all_categories)

    print(f"\nTop 20 Product Categories:")
    print(f"{'Category':<20s} {'Count':>8s} {'Avg Price':>12s}")
    print(f"{'-'*20} {'-'*8} {'-'*12}")

    for category, count in category_counts.most_common(20):
        # Calculate average price for this category
        mask = df['description'].str.lower().str.contains(category, na=False)
        avg_price = df[mask]['price'].mean()
        print(f"{category:<20s} {count:>8,} ${avg_price:>10.2f}")

    # Sample products by category
    print(f"\n{'─'*80}")
    print("SAMPLE PRODUCTS BY CATEGORY")
    print(f"{'─'*80}\n")

    for category, count in category_counts.most_common(10):
        mask = df['description'].str.lower().str.contains(category, na=False)
        category_products = df[mask].head(3)

        print(f"\n{category.upper()} ({count} products):")
        print(f"{'-'*80}")

        for idx, row in category_products.iterrows():
            # Truncate description
            desc = row['description'][:100] + "..." if len(row['description']) > 100 else row['description']
            print(f"  ID: {row['item_id']}")
            print(f"  Price: ${row['price']:.2f}")
            print(f"  Description: {desc}")
            print()

    # Description length statistics
    print(f"\n{'─'*80}")
    print("DESCRIPTION LENGTH STATISTICS")
    print(f"{'─'*80}")
    desc_lengths = df['description'].str.len()
    print(f"Min length:    {desc_lengths.min()} characters")
    print(f"Max length:    {desc_lengths.max()} characters")
    print(f"Mean length:   {desc_lengths.mean():.0f} characters")
    print(f"Median length: {desc_lengths.median():.0f} characters")

    # Sample search queries
    print(f"\n{'─'*80}")
    print("SUGGESTED SEARCH QUERIES")
    print(f"{'─'*80}\n")

    suggestions = []
    for category, count in category_counts.most_common(10):
        mask = df['description'].str.lower().str.contains(category, na=False)
        avg_price = df[mask]['price'].mean()
        suggestions.append({
            'query': category,
            'count': count,
            'avg_price': avg_price
        })

    print("Try these search queries with the API:\n")
    for i, sugg in enumerate(suggestions[:5], 1):
        print(f"{i}. Search for '{sugg['query']}'")
        print(f"   - {sugg['count']} products available")
        print(f"   - Average price: ${sugg['avg_price']:.2f}")
        print(f"   - Example curl command:")
        print(f"     curl -X POST http://localhost:8080/api/v1/search/product_search \\")
        print(f"       -H 'Content-Type: application/json' \\")
        print(f"       -d '{{")
        print(f"         \"query_text\": \"{sugg['query']}\",")
        print(f"         \"query_price\": {sugg['avg_price']:.2f},")
        print(f"         \"description_weight\": 1.0,")
        print(f"         \"price_weight\": 0.3,")
        print(f"         \"limit\": 5")
        print(f"       }}'\n")

    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Amazon product data to understand categories and price ranges"
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
        help="Analyze only first N products (default: all)",
    )

    args = parser.parse_args()

    # Auto-select file based on USE_TEST_DATA env variable
    if args.input:
        input_file = Path(args.input)
    else:
        use_test_data = os.environ.get('USE_TEST_DATA', '0') == '1'
        if use_test_data:
            input_file = Path("data/processed_amazon_grocery_1k.parquet")
        else:
            input_file = Path("data/processed_amazon_grocery.parquet")

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    analyze_parquet(input_file, sample_size=args.sample)


if __name__ == "__main__":
    main()
