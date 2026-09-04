"""
Single place that knows how to open the (per-query, freshly wiped) Chroma DB,
so every agent uses the same embedding model + persist directory.
"""
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from config import CHROMA_DIR, EMBEDDING_MODEL

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


def get_collection(name: str) -> Chroma:
    return Chroma(
        collection_name=name,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )
