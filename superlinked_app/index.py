from superlinked import framework as sl


class ProductSchema(sl.Schema):
    item_id: sl.IdField
    item_name: sl.String
    brand: sl.String | None
    product_type: sl.String | None
    color: sl.String | None
    product_description: sl.String | None
    item_keywords: sl.String | None
    main_image_id: sl.String | None
    country: sl.String | None
    domain_name: sl.String | None


product_schema = ProductSchema()

# Text similarity spaces for different product attributes
model_name = "sentence-transformers/all-MiniLM-L6-v2"

name_space = sl.TextSimilaritySpace(
    text=product_schema.item_name,
    model=model_name
)

description_space = sl.TextSimilaritySpace(
    text=product_schema.product_description,
    model=model_name
)

keywords_space = sl.TextSimilaritySpace(
    text=product_schema.item_keywords,
    model=model_name
)

# Categorical space for product type filtering
category_space = sl.CategoricalSimilaritySpace(
    category_input=product_schema.product_type,
    categories=["SHOES", "DRINKING_CUP", "CLOTHING", "ELECTRONICS"],
    uncategorized_as_category=True
)

index = sl.Index([name_space, description_space, keywords_space, category_space])
