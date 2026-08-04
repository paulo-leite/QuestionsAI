"""Configurações compartilhadas da aplicação."""

import os

from dotenv import load_dotenv


load_dotenv()

MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_RESEARCH_ROUNDS = 3
MAX_SUBQUESTIONS = 4
RETRIEVAL_CANDIDATES = 10
RERANK_TOP_N = 2
RERANK_TIMEOUT_SECONDS = 30
DOCLING_MAX_TOKENS = 512
DOCLING_TOKENIZER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MODEL = "jina-embeddings-v3"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Configure {name} no arquivo .env")
    return value
