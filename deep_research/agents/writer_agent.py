"""Revisão e redação final dos achados verificados."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from deep_research.models import (
    ResearchFinding,
    ResearchReview,
    Source,
    SufficiencyResult,
)
from deep_research.services.llm_service import get_llm


def review_findings(findings: list[ResearchFinding]) -> ResearchReview:
    unsupported = [
        finding.subquestion
        for finding in findings
        if finding.error or not finding.sources
    ]
    answers: dict[str, list[str]] = {}
    for finding in findings:
        normalized = " ".join(finding.answer.lower().split())
        if len(normalized) > 20:
            answers.setdefault(normalized, []).append(finding.subquestion)
    return ResearchReview(
        unsupported_subquestions=unsupported,
        conflicting_subquestions=[
            "; ".join(questions)
            for questions in answers.values()
            if len(questions) > 1
        ],
        follow_up_questions=[
            f"Localize no documento evidências específicas para: {question}"
            for question in unsupported
        ],
    )


def deduplicate_sources(findings: list[ResearchFinding]) -> list[Source]:
    seen: set[tuple[int, str]] = set()
    sources: list[Source] = []
    for finding in findings:
        for source in finding.sources:
            key = (source.page, source.excerpt)
            if key not in seen:
                seen.add(key)
                sources.append(source)
    return sources


def write_report(
    question: str,
    findings: list[ResearchFinding],
    sufficiency: SufficiencyResult,
) -> str:
    supported = [finding for finding in findings if finding.sources]
    if not supported:
        return "Não encontrei evidências suficientes no documento para responder."

    evidence = "\n\n".join(
        f"Subpergunta: {finding.subquestion}\n"
        f"Conclusão: {finding.answer}\n"
        f"Fontes: {', '.join(f'página {s.page}' for s in finding.sources)}"
        for finding in supported
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Redija em português usando somente os achados e fontes recebidos. "
                "Inclua as páginas, não invente informações e não use a web. "
                "Quando a avaliação indicar insuficiência, declare claramente "
                "as limitações e não apresente lacunas como fatos.",
            ),
            (
                "human",
                "Pergunta: {question}\n\nAchados:\n{evidence}\n\n"
                "Suficiente: {is_sufficient}\n"
                "Avaliação: {sufficiency_reason}\n"
                "Lacunas: {missing_information}",
            ),
        ]
    )
    try:
        return (prompt | get_llm() | StrOutputParser()).invoke(
            {
                "question": question,
                "evidence": evidence,
                "is_sufficient": sufficiency.is_sufficient,
                "sufficiency_reason": sufficiency.reason,
                "missing_information": "; ".join(
                    sufficiency.missing_information
                ) or "nenhuma",
            }
        )
    except Exception:
        answer = "\n\n".join(
            f"{finding.subquestion}: {finding.answer}" for finding in supported
        )
        if not sufficiency.is_sufficient:
            gaps = "; ".join(sufficiency.missing_information) or sufficiency.reason
            answer += f"\n\nLimitações da pesquisa: {gaps}"
        return answer
