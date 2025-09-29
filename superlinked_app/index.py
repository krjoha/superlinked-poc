from superlinked import framework as sl

class YourSchema(sl.Schema):
    id: sl.IdField
    attribute: sl.String

your_schema = YourSchema()

model_name = "sentence-transformers/all-MiniLM-L6-v2"
text_space = sl.TextSimilaritySpace(text=your_schema.attribute, model=model_name)

index = sl.Index(text_space)