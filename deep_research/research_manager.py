"""Orquestra planejamento, buscas no documento e redação."""

import asyncio
from threading import Lock
from uuid import uuid4

from langchain_chroma import Chroma

from deep_research.agents import (
    check_needs_clarification,
    check_research_sufficiency,
    create_refinement_plan,
    create_search_plan,
    deduplicate_sources,
    execute_searches,
    generate_clarification_questions,
    review_findings,
    write_report,
)
from deep_research.errors import ApplicationError
from deep_research.models import (
    DocumentSearchItem,
    ReportData,
    ResearchFinding,
    ResearchRequest,
    ResearchResponse,
    ResearchState,
    SufficiencyResult,
)
from deep_research.services.vectorstore_service import get_vectorstore


class ResearchManager:
    def __init__(self) -> None:
        self._sessions: dict[str, ResearchState] = {}
        self._lock = Lock()

    def get_session(self, session_id: str) -> ResearchState | None:
        with self._lock:
            return self._sessions.get(session_id)

    async def start_research(self, request: ResearchRequest) -> ResearchState:
        if get_vectorstore(request.document_id) is None:
            raise ApplicationError(
                "Documento não encontrado. Faça o upload novamente.", 404
            )

        session = ResearchState(
            session_id=str(uuid4()),
            document_id=request.document_id,
            original_query=request.question,
            depth=request.depth,
            status="pending",
        )
        with self._lock:
            self._sessions[session.session_id] = session

        try:
            needs_clarification = await check_needs_clarification(
                request.question
            )
        except Exception:
            needs_clarification = False

        if needs_clarification:
            try:
                session.clarification_questions = (
                    await generate_clarification_questions(request.question)
                )
            except Exception:
                session.clarification_questions = [
                    "Qual é o objetivo principal desta pesquisa?",
                    "Quais partes do documento devem receber mais atenção?",
                    "Quais critérios devem orientar a análise?",
                ]
            session.status = "awaiting_clarification"
            return session

        await self._complete_session(session, request.question)
        return session

    async def provide_clarification(
        self,
        session_id: str,
        answer: str,
    ) -> ResearchState:
        session = self.get_session(session_id)
        if session is None:
            raise ApplicationError("Sessão de pesquisa não encontrada.", 404)
        if session.status != "awaiting_clarification":
            raise ApplicationError(
                "A sessão não está aguardando esclarecimento.", 409
            )

        if session.answer_question(answer):
            return session

        clarifications = "\n".join(
            f"- {question}: {response}"
            for question, response in zip(
                session.clarification_questions,
                session.clarification_responses,
            )
        )
        enriched_query = (
            f"{session.original_query}\n\n"
            f"Esclarecimentos do usuário:\n{clarifications}"
        )
        await self._complete_session(session, enriched_query)
        return session

    async def _complete_session(
        self,
        session: ResearchState,
        query: str,
    ) -> None:
        session.status = "researching"
        response = await self.run_research(
            session.document_id,
            query,
            session.depth,
        )
        session.findings = response.findings
        session.sources = response.sources
        session.rounds_completed = response.rounds_completed
        session.sufficiency_check = response.sufficiency_check
        session.report_data = ReportData(
            short_summary=response.answer.split("\n\n", maxsplit=1)[0][:500],
            markdown_report=response.answer,
            follow_up_questions=response.review.follow_up_questions,
        )
        session.status = "completed"

    async def run_research(
        self,
        document_id: str,
        question: str,
        depth: int,
    ) -> ResearchResponse:
        vectorstore = get_vectorstore(document_id)
        if vectorstore is None:
            raise ApplicationError(
                "Documento não encontrado. Faça o upload novamente.", 404
            )
        return await self._run_pipeline(vectorstore, question, depth)

    async def _run_pipeline(
        self,
        vectorstore: Chroma,
        question: str,
        depth: int,
    ) -> ResearchResponse:
        try:
            plan = await asyncio.to_thread(create_search_plan, question)
        except Exception:
            plan = None

        initial_searches = (
            plan.searches
            if plan and plan.searches
            else [
                DocumentSearchItem(
                    query=question,
                    reason="Responder diretamente à pesquisa principal.",
                )
            ]
        )
        pending = initial_searches
        seen: set[str] = set()
        findings: list[ResearchFinding] = []
        rounds_completed = 0
        sufficiency = SufficiencyResult(
            is_sufficient=False,
            reason="A pesquisa ainda não foi avaliada.",
            missing_information=[],
        )

        while pending and rounds_completed < depth:
            current = [search for search in pending if search.query not in seen]
            if not current:
                break
            seen.update(search.query for search in current)
            findings.extend(await execute_searches(vectorstore, current))
            rounds_completed += 1

            sufficiency = await self._check_sufficiency(question, findings)
            if sufficiency.is_sufficient or rounds_completed >= depth:
                break

            refinement = await self._create_refinement(
                question,
                findings,
                sufficiency,
            )
            pending = [
                search
                for search in refinement
                if search.query not in seen
            ]

        answer = await asyncio.to_thread(
            write_report,
            question,
            findings,
            sufficiency,
        )
        return ResearchResponse(
            answer=answer,
            findings=findings,
            review=review_findings(findings),
            sources=deduplicate_sources(findings),
            rounds_completed=rounds_completed,
            sufficiency_check=sufficiency,
        )

    @staticmethod
    async def _check_sufficiency(
        question: str,
        findings: list[ResearchFinding],
    ) -> SufficiencyResult:
        try:
            return await check_research_sufficiency(question, findings)
        except Exception:
            unsupported = [
                finding.subquestion
                for finding in findings
                if finding.error or not finding.sources
            ]
            sufficient = bool(findings) and not unsupported
            return SufficiencyResult(
                is_sufficient=sufficient,
                reason=(
                    "Todos os achados possuem evidências no documento."
                    if sufficient
                    else "Há achados sem evidências verificáveis no documento."
                ),
                missing_information=unsupported[:4],
            )

    @staticmethod
    async def _create_refinement(
        question: str,
        findings: list[ResearchFinding],
        sufficiency: SufficiencyResult,
    ) -> list[DocumentSearchItem]:
        try:
            plan = await create_refinement_plan(
                question,
                findings,
                sufficiency,
            )
            if plan.searches:
                return plan.searches
        except Exception:
            pass

        missing = sufficiency.missing_information or [question]
        return [
            DocumentSearchItem(
                query=f"Localize evidências específicas para: {item}",
                reason="Preencher lacuna apontada pela avaliação de suficiência.",
            )
            for item in missing[:4]
        ]


research_manager = ResearchManager()
