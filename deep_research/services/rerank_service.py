"""Integração HTTP com o modelo de reranking."""

import os

import requests
from langchain_core.documents import Document

from deep_research.config import RERANK_TIMEOUT_SECONDS, RERANK_TOP_N, require_env
from deep_research.errors import ApplicationError


def rerank_documents(query: str, documents: list[Document]) -> list[Document]:
    if not documents:
        return []

    base_url = require_env("LLM_BASE_URL")
    api_key = require_env("LLM_API_KEY")
    model = require_env("RERANK_MODEL")
    url = os.getenv("RERANK_URL", f"{base_url.rstrip('/')}/rerank")
    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "query": query,
                "documents": [document.page_content for document in documents],
                "top_n": min(RERANK_TOP_N, len(documents)),
            },
            timeout=RERANK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        results = response.json().get("results")
    except (requests.RequestException, ValueError) as exc:
        raise ApplicationError("Não foi possível executar o reranking.", 502) from exc

    if not isinstance(results, list):
        raise ApplicationError("O reranking retornou uma resposta inválida.", 502)

    reranked: list[Document] = []
    for result in results:
        index = result.get("index") if isinstance(result, dict) else None
        if isinstance(index, int) and 0 <= index < len(documents):
            document = documents[index]
            document.metadata["rerank_score"] = result.get("relevance_score")
            reranked.append(document)
    if not reranked:
        raise ApplicationError("O reranking não retornou documentos válidos.", 502)
    return reranked
