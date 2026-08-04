"""Agente planejador de consultas no documento."""

import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from deep_research.config import MAX_SUBQUESTIONS
from deep_research.models import DocumentSearchItem, DocumentSearchPlan
from deep_research.services.llm_service import get_llm


def parse_subquestions(output: str, original_question: str) -> list[str]:
    questions: list[str] = []
    for line in output.splitlines():
        item = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        if not item or item.lower().startswith(("subperguntas", "perguntas:")):
            continue
        if item not in questions:
            questions.append(item)
        if len(questions) == MAX_SUBQUESTIONS:
            break
    return questions or [original_question]


def create_search_plan(question: str) -> DocumentSearchPlan:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Planeje uma pesquisa em um único documento. Divida o tema em "
                f"no máximo {MAX_SUBQUESTIONS} subperguntas objetivas. Retorne "
                "somente uma pergunta por linha. Não responda e não use a web.",
            ),
            ("human", "Tema: {question}"),
        ]
    )
    output = (prompt | get_llm() | StrOutputParser()).invoke({"question": question})
    return DocumentSearchPlan(
        searches=[
            DocumentSearchItem(
                query=item,
                reason="Localizar evidências relevantes no documento.",
            )
            for item in parse_subquestions(output, question)
        ]
    )
