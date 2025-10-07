from superlinked import framework as sl

from superlinked_app.index import index, name_space, description_space, keywords_space, product_schema, category_space

query = (
    sl.Query(index)
    .find(product_schema)
    .similar(
        name_space.text,
        sl.Param("query_text"),
        weight=3.0  # Product name most important
    )
    .similar(
        keywords_space.text,
        sl.Param("query_text"),
        weight=2.0  # Keywords second priority
    )
    .similar(
        description_space.text,
        sl.Param("query_text"),
        weight=1.0  # Description lowest priority
    )
    .similar(
        category_space.category,
        sl.Param("product_type"),
        weight=1.0
    )
    .limit(sl.Param("limit"))
    .select_all()
)
