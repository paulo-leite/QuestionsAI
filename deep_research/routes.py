"""Rotas HTTP da API de documentos e pesquisa."""

from fastapi import APIRouter, File, UploadFile, status

from deep_research.config import MAX_FILE_SIZE
from deep_research.errors import ApplicationError
from deep_research.models import (
    ClarificationAnswer,
    QuestionRequest,
    QuestionResponse,
    ResearchRequest,
    ResearchResponse,
    ResearchState,
    UploadResponse,
)
from deep_research.research_manager import research_manager
from deep_research.services.document_service import prepare_document
from deep_research.services.rag_service import answer_from_vectorstore
from deep_research.services.vectorstore_service import get_vectorstore


router = APIRouter()


def require_vectorstore(document_id: str):
    vectorstore = get_vectorstore(document_id)
    if vectorstore is None:
        raise ApplicationError(
            "Documento não encontrado. Faça o upload novamente.", 404
        )
    return vectorstore


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    filename = file.filename or "documento.pdf"
    if not filename.lower().endswith(".pdf"):
        raise ApplicationError("Envie um arquivo PDF.", 415)

    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise ApplicationError("O PDF deve ter no máximo 20 MB.", 413)
    return prepare_document(content, filename)


@router.post("/questions", response_model=QuestionResponse)
def ask_question(request: QuestionRequest) -> QuestionResponse:
    vectorstore = require_vectorstore(request.document_id)
    return answer_from_vectorstore(vectorstore, request.question)


@router.post("/research", response_model=ResearchResponse)
async def deep_research(request: ResearchRequest) -> ResearchResponse:
    return await research_manager.run_research(
        request.document_id,
        request.question,
        request.depth,
    )


@router.post(
    "/research/sessions",
    response_model=ResearchState,
    status_code=status.HTTP_201_CREATED,
)
async def start_research_session(request: ResearchRequest) -> ResearchState:
    return await research_manager.start_research(request)


@router.post(
    "/research/sessions/{session_id}/clarifications",
    response_model=ResearchState,
)
async def provide_research_clarification(
    session_id: str,
    request: ClarificationAnswer,
) -> ResearchState:
    return await research_manager.provide_clarification(
        session_id,
        request.answer,
    )


@router.get("/research/sessions/{session_id}", response_model=ResearchState)
def get_research_session(session_id: str) -> ResearchState:
    session = research_manager.get_session(session_id)
    if session is None:
        raise ApplicationError("Sessão de pesquisa não encontrada.", 404)
    return session
