"""Agente que transforma lacunas em novas consultas ao documento."""

import asyncio
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from deep_research.config import MAX_SUBQUESTIONS
from deep_research.models import (
    DocumentSearchPlan,
    ResearchFinding,
    SufficiencyResult,
)
from deep_research.services.llm_service import get_llm


REFINEMENT_PROMPT = f"""Você refina uma pesquisa insuficiente em um único
documento.

Crie consultas novas, específicas e complementares para localizar as informações
ausentes apontadas pela avaliação. Não repita consultas já executadas. Gere no
máximo {MAX_SUBQUESTIONS} consultas. Não responda à pesquisa e não use a web.
"""


def _executed_queries(findings: list[ResearchFinding]) -> str:
    return "\n".join(f"- {finding.subquestion}" for finding in findings)


def new_refinement_agent() -> Any:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", REFINEMENT_PROMPT),
            (
                "human",
                "Consulta principal: {question}\n"
                "Motivo da insuficiência: {reason}\n"
                "Informações ausentes: {missing}\n\n"
                "Consultas já executadas:\n{executed}",
            ),
        ]
    )
    return prompt | get_llm().with_structured_output(DocumentSearchPlan)


async def create_refinement_plan(
    question: str,
    findings: list[ResearchFinding],
    sufficiency: SufficiencyResult,
) -> DocumentSearchPlan:
    agent = new_refinement_agent()
    inputs = {
        "question": question,
        "reason": sufficiency.reason,
        "missing": "\n".join(
            f"- {item}" for item in sufficiency.missing_information
        ) or "- Cobertura insuficiente não detalhada.",
        "executed": _executed_queries(findings),
    }
    result = await asyncio.to_thread(lambda: agent.invoke(inputs))
    plan = DocumentSearchPlan.model_validate(result)
    executed = {finding.subquestion.casefold() for finding in findings}
    unique = []
    for search in plan.searches:
        if search.query.casefold() not in executed and all(
            item.query.casefold() != search.query.casefold() for item in unique
        ):
            unique.append(search)
        if len(unique) == MAX_SUBQUESTIONS:
            break
    return DocumentSearchPlan(searches=unique)
