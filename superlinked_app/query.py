from superlinked import framework as sl

from superlinked_app.index import index, description_space, price_space, product_schema

query = (
    sl.Query(index)
    .find(product_schema)
    .similar(
        description_space.text,
        sl.Param("query_text"),
        weight=sl.Param("description_weight")  # Default: 1.0, adjustable by client
    )
    .similar(
        price_space.number,
        sl.Param("query_price"),
        weight=sl.Param("price_weight")  # Default: 0.5, adjustable by client
    )
    .limit(sl.Param("limit"))
    .select_all()
)
