"""Indexação e armazenamento em memória das coleções Chroma."""

from threading import Lock
from uuid import uuid4

from langchain_chroma import Chroma
from langchain_core.documents import Document

from .embedding_service import get_embeddings


vectorstores: dict[str, Chroma] = {}
_lock = Lock()


def index_chunks(chunks: list[Document]) -> str:
    document_id = str(uuid4())
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=f"document_{document_id.replace('-', '')}",
    )
    with _lock:
        vectorstores[document_id] = vectorstore
    return document_id


def get_vectorstore(document_id: str) -> Chroma | None:
    with _lock:
        return vectorstores.get(document_id)
