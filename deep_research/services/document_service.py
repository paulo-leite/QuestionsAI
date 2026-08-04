"""Caso de uso de preparação e indexação de um arquivo."""

from deep_research.config import DOCLING_MAX_TOKENS
from deep_research.models import UploadResponse

from .docling_service import count_chunk_tokens, create_chunks
from .vectorstore_service import index_chunks


def prepare_document(content: bytes, filename: str) -> UploadResponse:
    chunks, page_count = create_chunks(content, filename)
    token_counts = count_chunk_tokens(chunks)
    document_id = index_chunks(chunks)
    return UploadResponse(
        document_id=document_id,
        filename=filename,
        pages=page_count,
        chunks=len(chunks),
        chunking_method="docling_hybrid",
        max_tokens_per_chunk=DOCLING_MAX_TOKENS,
        minimum_chunk_tokens=min(token_counts),
        average_chunk_tokens=round(sum(token_counts) / len(token_counts)),
        maximum_chunk_tokens=max(token_counts),
        average_chunk_characters=round(
            sum(len(chunk.page_content) for chunk in chunks) / len(chunks)
        ),
    )
