"""Agente que gera perguntas para delimitar uma pesquisa vaga."""

import asyncio
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from deep_research.models import ClarificationQuestions
from deep_research.services.llm_service import get_llm


CLARIFYING_PROMPT = """Você gera perguntas de esclarecimento antes de uma pesquisa
baseada exclusivamente em um documento enviado.

A triagem já determinou que a consulta precisa de esclarecimento. Analise a
consulta original e identifique somente as ambiguidades que impedem uma pesquisa
precisa no documento.

Gere de 1 a 3 perguntas curtas, específicas e necessárias para esclarecer o
objetivo, o escopo ou os critérios da pesquisa.

Não pergunte algo que já esteja informado na consulta. Não solicite fontes
externas, não faça perguntas genéricas, não responda à pesquisa, não pesquise no
documento e não use a web.

Priorize perguntas cuja resposta possa alterar de forma relevante quais trechos
do documento devem ser buscados ou como o resultado deve ser avaliado.
"""


def new_clarifying_agent() -> Any:
    """Cria a cadeia com saída validada como ``ClarificationQuestions``."""
    prompt = ChatPromptTemplate.from_messages(
        [("system", CLARIFYING_PROMPT), ("human", "Consulta: {query}")]
    )
    return prompt | get_llm().with_structured_output(ClarificationQuestions)


async def generate_clarification_questions(query: str) -> list[str]:
    agent = new_clarifying_agent()
    result = await asyncio.to_thread(agent.invoke, {"query": query})
    return ClarificationQuestions.model_validate(result).questions
