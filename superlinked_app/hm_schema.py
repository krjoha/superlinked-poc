from superlinked import framework as sl


class HMClothingSchema(sl.Schema):
    """
    Schema for H&M fashion/clothing products with image support.

    Fields:
    - item_id: Unique identifier for each product
    - description: Text description of the clothing item
    - image: Image data (base64-encoded string for DataLoader, PIL Image for REST API)
    """
    item_id: sl.IdField
    description: sl.String
    image: sl.Blob  # Accepts base64 strings (DataLoader) or PIL Images (REST)


hm_clothing_schema = HMClothingSchema()
