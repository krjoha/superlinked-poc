from superlinked import framework as sl


class AmazonGrocerySchema(sl.Schema):
    item_id: sl.IdField
    description: sl.String
    price: sl.Float


amazon_grocery_schema = AmazonGrocerySchema()

# Text similarity space for product descriptions
model_name = "sentence-transformers/all-MiniLM-L6-v2"

description_space = sl.TextSimilaritySpace(
    text=amazon_grocery_schema.description,
    model=model_name
)

# Number space for price-based filtering and similarity
# Using Mode.SIMILAR to find products with similar prices
# Range covers typical Amazon product prices ($0-$10,000)
price_space = sl.NumberSpace(
    number=amazon_grocery_schema.price,
    min_value=0.0,
    max_value=10000.0,
    mode=sl.Mode.SIMILAR
)

index = sl.Index([description_space, price_space])
