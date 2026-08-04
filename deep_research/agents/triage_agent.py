"""Agente que decide se a consulta precisa de esclarecimento."""

import asyncio
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from deep_research.models import TriageResult
from deep_research.services.llm_service import get_llm


TRIAGE_PROMPT = """Você faz a triagem de pesquisas em um documento enviado.

Decida se a consulta precisa de esclarecimento antes da pesquisa.

Precisa de esclarecimento quando:
- o objetivo ou escopo é vago;
- faltam critérios essenciais para a análise solicitada;
- existem interpretações muito diferentes da mesma solicitação.

Não precisa de esclarecimento quando a pergunta é factual, específica ou já
contém contexto suficiente. Não responda à pesquisa e não use a web.
"""


def new_triage_agent() -> Any:
    """Cria a cadeia com saída validada como ``TriageResult``."""
    prompt = ChatPromptTemplate.from_messages(
        [("system", TRIAGE_PROMPT), ("human", "Consulta: {query}")]
    )
    return prompt | get_llm().with_structured_output(TriageResult)


async def check_needs_clarification(query: str) -> bool:
    agent = new_triage_agent()
    result = await asyncio.to_thread(agent.invoke, {"query": query})
    return TriageResult.model_validate(result).needs_clarification
