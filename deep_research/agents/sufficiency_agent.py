"""Agente que avalia se as evidências respondem à consulta principal."""

import asyncio
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from deep_research.models import ResearchFinding, SufficiencyResult
from deep_research.services.llm_service import get_llm


SUFFICIENCY_PROMPT = """Você avalia a suficiência de uma pesquisa baseada em um
único documento.

Determine se os achados com fontes cobrem todos os aspectos relevantes da
consulta principal. Considere insuficiente quando houver partes importantes sem
evidência, respostas com erro, conclusões genéricas ou fontes que não sustentem
claramente a resposta.

Liste em missing_information somente lacunas que possam orientar novas buscas no
mesmo documento. Não responda à consulta, não invente fatos e não use a web.
"""


def _format_findings(findings: list[ResearchFinding]) -> str:
    return "\n\n".join(
        f"Subpergunta: {finding.subquestion}\n"
        f"Resposta: {finding.answer}\n"
        f"Páginas: {', '.join(str(s.page) for s in finding.sources) or 'nenhuma'}\n"
        f"Erro: {finding.error or 'nenhum'}"
        for finding in findings
    ) or "Nenhum achado disponível."


def new_sufficiency_agent() -> Any:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SUFFICIENCY_PROMPT),
            (
                "human",
                "Consulta principal: {question}\n\nAchados:\n{findings}",
            ),
        ]
    )
    return prompt | get_llm().with_structured_output(SufficiencyResult)


async def check_research_sufficiency(
    question: str,
    findings: list[ResearchFinding],
) -> SufficiencyResult:
    agent = new_sufficiency_agent()
    result = await asyncio.to_thread(
        agent.invoke,
        {"question": question, "findings": _format_findings(findings)},
    )
    return SufficiencyResult.model_validate(result)
