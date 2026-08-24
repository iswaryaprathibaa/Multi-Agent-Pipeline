"""ChromaDB-backed knowledge base used by the Researcher (and Validator) agents."""
import glob
import os
from typing import Any, Dict, List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config

_embeddings: Optional[OpenAIEmbeddings] = None
_vectorstore: Optional[Chroma] = None


def get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        if not config.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and fill in your key."
            )
        _embeddings = OpenAIEmbeddings(
            model=config.OPENAI_EMBEDDING_MODEL, api_key=config.OPENAI_API_KEY
        )
    return _embeddings


def get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            collection_name=config.CHROMA_COLLECTION,
            embedding_function=get_embeddings(),
            persist_directory=config.CHROMA_PERSIST_DIR,
        )
    return _vectorstore


def ingest_texts(texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> int:
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    metadatas = metadatas or [{} for _ in texts]
    docs: List[Document] = []
    for text, meta in zip(texts, metadatas):
        for chunk in splitter.split_text(text):
            docs.append(Document(page_content=chunk, metadata=meta))
    if docs:
        get_vectorstore().add_documents(docs)
    return len(docs)


def ingest_directory(directory: str = "data") -> int:
    total = 0
    paths = sorted(glob.glob(os.path.join(directory, "*.txt")) + glob.glob(os.path.join(directory, "*.md")))
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        total += ingest_texts([text], [{"source": os.path.basename(path)}])
    return total


def retrieve(query: str, k: int = 6) -> List[Document]:
    return get_vectorstore().similarity_search(query, k=k)


def collection_count() -> int:
    try:
        return get_vectorstore()._collection.count()
    except Exception:
        return 0
