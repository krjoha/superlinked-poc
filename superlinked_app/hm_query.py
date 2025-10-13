from superlinked import framework as sl

from superlinked_app.hm_index import hm_index, image_space, description_space, hm_clothing_schema

# Multi-modal query for H&M clothing items
# Supports three types of similarity search:
# 1. Text-in-text: Search with text in descriptions
# 2. Text-in-image: Search with text query in image embeddings (semantic image search)
# 3. Image-in-image: Search with reference image in image embeddings

hm_query = (
    sl.Query(
        hm_index,
        weights={
            description_space: sl.Param("description_weight"),  # Weight for text similarity
            image_space: sl.Param("image_weight"),  # Weight for image similarity
        },
    )
    .find(hm_clothing_schema)
    # Search with text in the description field
    .similar(
        description_space.text,
        sl.Param("text_search"),
    )
    # Search with text in the image embedding space (CLIP text-to-image)
    .similar(
        image_space.description,
        sl.Param("text_in_image_search"),
    )
    # Search with image in the image embedding space
    .similar(
        image_space.image,
        sl.Param("image_search"),
    )
    .limit(sl.Param("limit"))
    .select_all()
)
