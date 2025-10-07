from superlinked import framework as sl
from superlinked.framework.dsl.source.data_loader_source import DataFormat

from superlinked_app.index import index, product_schema
from superlinked_app.query import query

# REST source for manual ingestion
product_source: sl.RestSource = sl.RestSource(product_schema)

# DataLoader source for bulk ingestion from Parquet
# Set USE_TEST_DATA=1 for 1k rows, otherwise loads full 145k dataset
import os
data_file = (
    "amazon_objects/processed_products_test.parquet"
    if os.getenv("USE_TEST_DATA")
    else "amazon_objects/processed_products.parquet"
)
data_loader_config = sl.DataLoaderConfig(
    path=data_file,
    format=DataFormat.PARQUET,
    name="amazon_products_loader"
)
data_loader_source = sl.DataLoaderSource(product_schema, data_loader_config)

product_query = sl.RestQuery(sl.RestDescriptor("product_search"), query)

executor = sl.RestExecutor(
    sources=[product_source, data_loader_source],
    indices=[index],
    queries=[product_query],
    vector_database=sl.InMemoryVectorDatabase(),
)

sl.SuperlinkedRegistry.register(executor)
