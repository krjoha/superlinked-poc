# %% [markdown]
# # Image search in e-commerce
# 
# This use-case notebook shows semantic search in fashion images. 
# 
# In e-commerce, being able to serve user queries with the most relevant results is of utmost importance. Users predominantly use text to describe what they would like and that poses a problem e-commerce websites face: products generally lack extensive textual information. However, there is no better way to describe a product than an image. Luckily, researchers also realised that, and came up with multi-modal Vision Transformers that embed text and images in the same space, thereby making us able to search with text in images of products. Namely, searching for an "elegant dress" does not require the description to contain anything similar to return the actual elegant dresses.
# 
# To demonstrate that, we are going to perform search in a fashion dataset consinsting of images with short descriptions. We will be able to search:
# - with text in the descriptions,
# - with text in the images,
# - with an image in the images
# 
# or we can combine these in the following ways:
# - search with the same or different text in the descriptions and the images
# - search with text in the descriptions, and with images in the images
# 
# we will show that multi-modal search in the text embedding AND the image embedding space is the best approach to get the most relevant results.

# %%
%pip install superlinked==37.4.2

# %%
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
import PIL.Image
import requests

from datasets import load_dataset
from beartype.typing import Any, Hashable
from requests import RequestException

from superlinked import framework as sl

DATASET_ID: str = "tomytjandra/h-and-m-fashion-caption"
VIT_MODEL_ID: str = "hf-hub:laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
WATCH_IMAGE_URL: str = "https://storage.googleapis.com/superlinked-notebook-image-search/watch.jpg"
NUM_SAMPLES = 2000
SEED = 42
LIMIT = 4

# %% [markdown]
# ## Create Image embeddings

# %% [markdown]
# Let's use a state-of-the-art OpenCLIP model to embed a fashion product dataset! The dataset we are going to use are images and captions of H&M products.

# %% [markdown]
# ### Load data

# %%
# depending on your internet connection, downloading the dataset for the first time may take several minutes.
fashion_dataset = load_dataset(DATASET_ID)
fashion_sample_dataset = fashion_dataset["train"].shuffle(seed=SEED).select(range(NUM_SAMPLES))

# %% [markdown]
# ### Organize metadata

# %%
fashion_json_data = [item for i, item in enumerate(fashion_sample_dataset)]
for i, item in enumerate(fashion_json_data):
    fashion_json_data[i]["id"] = i
fashion_df = pd.DataFrame(fashion_json_data)
fashion_df["description"] = fashion_df["text"]
fashion_df.head()

# %%
json_data: list[dict[Hashable, Any]] = fashion_df.to_dict(orient="records")

# %% [markdown]
# Here is an example image of a shirt:

# %%
sample_picture = fashion_sample_dataset[0]["image"]
sample_picture.resize([int(size_dim / 5) for size_dim in sample_picture.size])

# %% [markdown]
# ## Superlinked setup
# 
# Now, let's demonstrate that text and image representations are closely aligned in the same embedding space when they refer to the same concept. As a first step, set Superlinked up to perform multi-modal vector search on our dataset!

# %%
class Image(sl.Schema):
    id: sl.IdField
    image: sl.Blob
    description: sl.String


image = Image()

# %%
# Image space utilizes the specified Vision Transformer model to encode image (and text)
image_embedding_space = sl.ImageSpace(image=image.image, model=VIT_MODEL_ID, model_handler=sl.ModelHandler.OPEN_CLIP)
# Embed descriptions using a text embedding model
description_space = sl.TextSimilaritySpace(text=image.description, model="Alibaba-NLP/gte-large-en-v1.5")

# construct an index
composite_index = sl.Index([image_embedding_space, description_space])

# %%
source: sl.InMemorySource = sl.InMemorySource(image)
executor = sl.InMemoryExecutor(sources=[source], indices=[composite_index])
app = executor.run()

# %% [markdown]
# Next step is ingesting our dataset. Embedding the 2000 images using a ViT model might take several minutes even on a GPU, feel free to browse around on [VectorHub](https://superlinked.com/vectorhub/). 

# %%
source.put(json_data)

# %%
combined_query = (
    sl.Query(
        composite_index,
        weights={
            description_space: sl.Param("description_weight"),
            image_embedding_space: sl.Param("image_embedding_weight"),
        },
    )
    .find(image)
    .similar(description_space, sl.Param("text_search"))
    .similar(image_embedding_space.image, sl.Param("image_search"))
    .similar(image_embedding_space.description, sl.Param("text_in_image_search"))
    .select_all()
    .limit(LIMIT)
)

# %% [markdown]
# ## Search images

# %%
# helper functions to plot image results
def plot_result_pictures(result_df: pd.DataFrame) -> None:
    ax = plt.subplots(1, LIMIT, figsize=(LIMIT * 3, 2))[1]
    ax = ax.flatten()
    result_num = 1
    for result_id, ax_ in zip(result_df["id"].tolist(), ax):
        ax_.imshow(fashion_sample_dataset["image"][int(result_id)])
        ax_.set_title(f"Result {result_num}", fontsize=16)
        result_num += 1
        ax_.set_axis_off()


def plot_result_picture_comparison(result_df_by_name: dict[str, pd.DataFrame]) -> None:
    num_results = len(result_df_by_name.keys())
    fig = plt.figure(constrained_layout=True, figsize=(3 * num_results, 5 * LIMIT / 2))
    fig.suptitle("Result comparison", fontsize=16)

    # create 3x1 subfigs
    subfigs = fig.subfigures(nrows=num_results, ncols=1)
    for subfig, (label, result_df) in zip(subfigs, result_df_by_name.items()):
        subfig.suptitle(f"{label}", fontsize=12)

        # create 1x3 subplots per subfig
        axs = subfig.subplots(nrows=1, ncols=LIMIT)
        for col, ax in enumerate(axs):
            ax.imshow(fashion_sample_dataset["image"][int(result_df["id"].iloc[col])])
            ax.set_title(f"Result {col+1}", fontsize=10)
            ax.set_axis_off()

# %% [markdown]
# ### Search with text in the description field
# 
# Let's first try searching only with text in the descriptions of the products. This approach requires extensive descriptions to work well.

# %%
TEXT_TO_SEARCH_WITH = "women high waist black slim fit jeans"

# %%
result_text = app.query(
    combined_query,
    description_weight=1,
    text_search=TEXT_TO_SEARCH_WITH,
)

result_text_df = sl.PandasConverter.to_pandas(result_text)
result_text_df

# %%
plot_result_pictures(result_text_df)

# %% [markdown]
# It can be spotted that the 2nd result has a wide fit at the ankle, and at least the 1st result is not particularly high-waist. Matching solely on text embeddings produces false positive results - among right ones.

# %% [markdown]
# ### Search with text in the image space

# %%
result_text_in_images = app.query(
    combined_query,
    image_embedding_weight=1,
    text_in_image_search=TEXT_TO_SEARCH_WITH,
)

result_text_in_images_df = sl.PandasConverter.to_pandas(result_text_in_images)
result_text_in_images_df

# %%
plot_result_pictures(result_text_in_images_df)

# %% [markdown]
# Searching with text in the image space definitely improves the results, but there is a false positve present in the 4th position that has low-waist design.

# %% [markdown]
# ### Search with image in image space
# 
# It is also possible to search with a reference image in the image embedding space.

# %%
# helper function to read an image from a public gcs bucket
def open_image_from_public_gcs(public_url: str) -> PIL.Image.Image:
    # Fetch the image using the public URL
    response = requests.get(public_url, timeout=5)

    # Ensure the request was successful
    if response.status_code == 200:
        # Open the image with PIL using the downloaded bytes
        downloaded_image = PIL.Image.open(BytesIO(response.content))
        return downloaded_image
    raise RequestException(
        f"Failed to fetch image. Status code: {response.status_code}",
    )

# %%
watch_image = open_image_from_public_gcs(WATCH_IMAGE_URL)
width, height = watch_image.size
watch_image.resize((int(width / 6), int(height / 6)))

# %%
result_image = app.query(
    combined_query,
    image_embedding_weight=1,
    image_search=watch_image,
)

result_image_df = sl.PandasConverter.to_pandas(result_image)
result_image_df

# %%
plot_result_pictures(result_image_df)

# %% [markdown]
# The results are indeed quite fitting in terms of style with the reference image - or we could say it swayed the results towards silver and blue colors. Of course the dataset only contains clothes, so no watches are popping up.

# %% [markdown]
# ### Search with text in the description space and image in the image space

# %%
result_text_image_combined = app.query(
    combined_query,
    description_weight=1,
    image_embedding_weight=1,
    text_search=TEXT_TO_SEARCH_WITH,
    image_search=watch_image,
)

result_text_image_combined_df = sl.PandasConverter.to_pandas(result_text_image_combined)
result_text_image_combined_df

# %%
plot_result_pictures(result_text_image_combined_df)

# %% [markdown]
# Using a reference image and text to search in descriptions seems to take little effect - there are much better hits for the description than to the reference watch, hence the image can sway the results to a quite small extent.

# %% [markdown]
# ### Search with text in the description space and image in the image space

# %%
result_text_image = app.query(
    combined_query,
    description_weight=1,
    image_embedding_weight=2,
    text_search=TEXT_TO_SEARCH_WITH,
    text_in_image_search=TEXT_TO_SEARCH_WITH,
)

result_text_image_df = sl.PandasConverter.to_pandas(result_text_image)
result_text_image_df

# %%
plot_result_pictures(result_text_image_df)

# %% [markdown]
# The utterly powerful approach is to search with the same text in the description and in the image embedding space - ensuring hits on both data sources. Resulting in the most pure result set of high-waist, black, slim fit women's jeans.

# %% [markdown]
# ## Result comparison

# %% [markdown]
# Lets compare the most promising results to the simple text search for black, slim-fit and high-waist women's jeans. Also take it into account that users rarely search with a reference image, they rather use text - therefore the compared result sets are all relevant in a real-world scenario.

# %%
result_df_map = {
    "text-in-text": result_text_df,
    "text-in-image": result_text_in_images_df,
    "text-in-text+image": result_text_image_df,
}

plot_result_picture_comparison(result_df_map)

# %% [markdown]
# ## Summary
# 
# 1. `text-in-text` search is suboptimal due to producing false positives among relevant hits due to spurious semantic similarity. The first result is not high-waist for instance.
# 1. `text-in-image` search creates a substantial improvement but arguably shows a low-waist model at `Result 4`.
# 1. `text-in-text+image` search improves upon the `text-in-image` by removing the low-waist jeans through cross-checking its description. All the results are high-waist and slim-fit, thereby arising as the most reliable approach.
# 
# In conclusion, utilizing multi-modal vector search improves upon using even the most sophisticated, in itself multi-modal image+text embedding models. The description and the image of a product can contain unique information, therefore utilising both is essential for creating high performing product search - or image search in general.
# 
# A potential different approach is to embed the descriptions and the images in the same `ImageSpace`. See [feature notebook](https://github.com/superlinked/superlinked/blob/main/notebook/feature/image_embedding.ipynb) for how to do it. The main differences are:
# - embedding separately creates the opportunity to weight descriptions and images separately, but
# - but makes the vectors longer that results in more storage need.
# Everyone should decide based on their use-case which fits their needs better.


