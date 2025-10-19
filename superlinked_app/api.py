from superlinked import framework as sl
from superlinked.framework.dsl.source.data_loader_source import DataFormat

from superlinked_app.amazon_index import index, amazon_grocery_schema
from superlinked_app.amazon_query import query
from superlinked_app.hm_index import hm_index, hm_clothing_schema
from superlinked_app.hm_query import hm_query
from superlinked_app.vector_db import get_vector_database
from superlinked_app.config import settings

# ============================================================================
# GROCERY PRODUCT SOURCES AND QUERIES (Amazon ML Challenge Dataset)
# ============================================================================

# REST source for manual grocery product ingestion
product_source: sl.RestSource = sl.RestSource(amazon_grocery_schema)

# DataLoader source for bulk grocery product ingestion from Parquet
# Uses settings.use_test_data for 1k rows, otherwise loads full 75k dataset
grocery_data_file = (
    "data/processed_amazon_grocery_1k.parquet"
    if settings.use_test_data
    else "data/processed_amazon_grocery.parquet"
)
grocery_loader_config = sl.DataLoaderConfig(
    path=grocery_data_file,
    format=DataFormat.PARQUET,
    name="amazon_grocery_loader"
)
grocery_data_loader = sl.DataLoaderSource(amazon_grocery_schema, grocery_loader_config)

# REST query endpoint for grocery products
product_query = sl.RestQuery(sl.RestDescriptor("amazon_grocery_search"), query)

# ============================================================================
# H&M CLOTHING SOURCES AND QUERIES (H&M Fashion Dataset)
# ============================================================================

# REST source for manual H&M clothing ingestion
hm_clothing_source: sl.RestSource = sl.RestSource(hm_clothing_schema)

# DataLoader source for bulk H&M clothing ingestion from CSV
# Uses settings.use_test_data for 1k rows, otherwise loads full ~20k dataset
# CSV supports chunked reading to avoid OOM with large image embeddings
hm_data_file = (
    "data/processed_hm_clothing_1k.csv"
    if settings.use_test_data
    else "data/processed_hm_clothing.csv"
)
hm_loader_config = sl.DataLoaderConfig(
    path=hm_data_file,
    format=DataFormat.CSV,
    name="hm_clothing_loader",
    pandas_read_kwargs={
        "chunksize": settings.pandas_chunksize
    }
)
hm_data_loader = sl.DataLoaderSource(hm_clothing_schema, hm_loader_config)

# REST query endpoint for H&M clothing products
hm_query_endpoint = sl.RestQuery(sl.RestDescriptor("hm_clothing_search"), hm_query)

# ============================================================================
# EXECUTOR CONFIGURATION
# ============================================================================

# Single executor managing both grocery and H&M clothing datasets
# Vector database is configured via environment variables (see vector_db.py)
executor = sl.RestExecutor(
    sources=[product_source, grocery_data_loader, hm_clothing_source, hm_data_loader],
    indices=[index, hm_index],
    queries=[product_query, hm_query_endpoint],
    vector_database=get_vector_database(),
)

sl.SuperlinkedRegistry.register(executor)
