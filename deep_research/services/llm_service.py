"""Criação e cache do cliente de chat."""

import os
from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from deep_research.config import require_env


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=os.getenv(
            "LLM_BASE_URL",
            "https://waymodels.virtus.ufcg.edu.br:4000/v1",
        ),
        api_key=SecretStr(require_env("LLM_API_KEY")),
        model=os.getenv("LLM_MODEL", "gemma4-26b-a4b"),
        temperature=0.2,
    )
