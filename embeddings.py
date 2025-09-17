# embeddings.py
from sentence_transformers import SentenceTransformer

# Load embedding model once
_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text: str):
    """
    Generate embedding for a given text string.
    Returns a list[float].
    """
    return _model.encode(text).tolist()