"""Agente de pesquisa restrito à coleção vetorial do documento."""

import asyncio

from langchain_chroma import Chroma

from deep_research.models import DocumentSearchItem, ResearchFinding
from deep_research.services.rag_service import answer_from_vectorstore


def perform_document_search(
    vectorstore: Chroma,
    query: str,
    reason: str,
) -> ResearchFinding:
    del reason
    try:
        response = answer_from_vectorstore(vectorstore, query)
        return ResearchFinding(
            subquestion=query,
            answer=response.answer,
            sources=response.sources,
            evidence_count=len(response.sources),
        )
    except Exception:
        return ResearchFinding(
            subquestion=query,
            answer="Não foi possível concluir esta subpesquisa.",
            sources=[],
            evidence_count=0,
            error="Falha ao recuperar evidências ou gerar a resposta.",
        )


async def execute_searches(
    vectorstore: Chroma,
    searches: list[DocumentSearchItem],
) -> list[ResearchFinding]:
    return list(
        await asyncio.gather(
            *(
                asyncio.to_thread(
                    perform_document_search,
                    vectorstore,
                    search.query,
                    search.reason,
                )
                for search in searches
            )
        )
    )
