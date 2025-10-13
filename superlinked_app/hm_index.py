from superlinked import framework as sl

from superlinked_app.hm_schema import hm_clothing_schema

# Multi-modal Vision Transformer for image embeddings
# Uses OpenCLIP model that embeds both text and images in the same space
VIT_MODEL_ID = "hf-hub:laion/CLIP-ViT-H-14-laion2B-s32B-b79K"

# ImageSpace for encoding images using Vision Transformer
# This space can handle both image similarity and text-to-image search
image_space = sl.ImageSpace(
    image=hm_clothing_schema.image,
    model=VIT_MODEL_ID,
    model_handler=sl.ModelHandler.OPEN_CLIP
)

# TextSimilaritySpace for encoding descriptions
# Uses same powerful model as ESCI example for consistency
description_space = sl.TextSimilaritySpace(
    text=hm_clothing_schema.description,
    model="Alibaba-NLP/gte-large-en-v1.5"
)

# Composite index combining both image and text search capabilities
# Enables multi-modal search: text-in-text, text-in-image, image-in-image
hm_index = sl.Index([image_space, description_space])
