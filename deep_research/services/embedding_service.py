"""Integração com o serviço externo de embeddings."""

import os
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from openai import OpenAI

from deep_research.config import EMBEDDING_MODEL, require_env


class JinaEmbeddings(Embeddings):
    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=require_env("LLM_BASE_URL"),
            api_key=require_env("LLM_API_KEY"),
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL),
            input=texts,
        )
        return [
            item.embedding
            for item in sorted(response.data, key=lambda item: item.index)
        ]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache(maxsize=1)
def get_embeddings() -> JinaEmbeddings:
    return JinaEmbeddings()
