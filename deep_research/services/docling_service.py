"""Conversão e fragmentação estrutural de PDFs com Docling."""

from functools import lru_cache
from io import BytesIO

from docling.chunking import HybridChunker
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.huggingface import (
    HuggingFaceTokenizer,
)
from langchain_core.documents import Document

from deep_research.config import (
    DOCLING_MAX_TOKENS,
    DOCLING_TOKENIZER_MODEL,
)
from deep_research.errors import ApplicationError


@lru_cache(maxsize=1)
def get_document_converter() -> DocumentConverter:
    return DocumentConverter()


@lru_cache(maxsize=1)
def get_docling_chunker() -> HybridChunker:
    tokenizer = HuggingFaceTokenizer.from_pretrained(
        model_name=DOCLING_TOKENIZER_MODEL,
        max_tokens=DOCLING_MAX_TOKENS,
        truncation=True,
    )
    return HybridChunker(tokenizer=tokenizer, merge_peers=True)


def create_chunks(content: bytes, filename: str) -> tuple[list[Document], int]:
    try:
        conversion = get_document_converter().convert(
            DocumentStream(name=filename, stream=BytesIO(content))
        )
        document = conversion.document
    except Exception as exc:
        raise ApplicationError(
            "Não foi possível processar o PDF com o Docling.", 400
        ) from exc

    chunker = get_docling_chunker()
    chunks: list[Document] = []
    for chunk in chunker.chunk(dl_doc=document):
        text = chunker.contextualize(chunk=chunk).strip()
        if not text:
            continue
        pages = sorted(
            {
                provenance.page_no
                for item in chunk.meta.doc_items
                for provenance in item.prov
            }
        )
        first_page = pages[0] if pages else 1
        chunks.append(
            Document(
                page_content=text,
                metadata={
                    "source": filename,
                    "page": max(first_page - 1, 0),
                    "pages": pages,
                    "chunking": "docling_hybrid",
                },
            )
        )

    if not chunks:
        raise ApplicationError(
            "O Docling não encontrou conteúdo utilizável no PDF.", 422
        )
    return chunks, len(document.pages)


def count_chunk_tokens(chunks: list[Document]) -> list[int]:
    tokenizer = get_docling_chunker().tokenizer
    return [
        tokenizer.count_tokens(text=chunk.page_content)
        for chunk in chunks
    ]
