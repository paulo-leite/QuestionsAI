"""Modelos usados nas rotas e no pipeline de pesquisa."""

from pydantic import BaseModel, Field

from .config import MAX_RESEARCH_ROUNDS


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks: int
    chunking_method: str
    max_tokens_per_chunk: int
    minimum_chunk_tokens: int
    average_chunk_tokens: int
    maximum_chunk_tokens: int
    average_chunk_characters: int


class QuestionRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=3)


class Source(BaseModel):
    page: int
    excerpt: str


class QuestionResponse(BaseModel):
    answer: str
    sources: list[Source]


class ResearchRequest(BaseModel):
    document_id: str
    question: str = Field(min_length=3)
    depth: int = Field(default=2, ge=1, le=MAX_RESEARCH_ROUNDS)


class DocumentSearchItem(BaseModel):
    query: str
    reason: str


class DocumentSearchPlan(BaseModel):
    searches: list[DocumentSearchItem]


class ResearchFinding(BaseModel):
    subquestion: str
    answer: str
    sources: list[Source]
    evidence_count: int
    error: str | None = None


class ResearchReview(BaseModel):
    unsupported_subquestions: list[str]
    conflicting_subquestions: list[str]
    follow_up_questions: list[str]


class SufficiencyResult(BaseModel):
    is_sufficient: bool
    reason: str
    missing_information: list[str] = Field(default_factory=list, max_length=4)


class ResearchResponse(BaseModel):
    answer: str
    findings: list[ResearchFinding]
    review: ResearchReview
    sources: list[Source]
    rounds_completed: int
    sufficiency_check: SufficiencyResult


class ReportData(BaseModel):
    short_summary: str
    markdown_report: str
    follow_up_questions: list[str]


class TriageResult(BaseModel):
    needs_clarification: bool
    reason: str


class ClarificationQuestions(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=3)


class ClarificationAnswer(BaseModel):
    answer: str = Field(min_length=1)


class ResearchState(BaseModel):
    session_id: str
    document_id: str
    original_query: str
    depth: int
    status: str = "pending"
    clarification_questions: list[str] = Field(default_factory=list)
    clarification_responses: list[str] = Field(default_factory=list)
    report_data: ReportData | None = None
    findings: list[ResearchFinding] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    rounds_completed: int = 0
    sufficiency_check: SufficiencyResult | None = None

    def answer_question(self, answer: str) -> bool:
        """Registra a resposta e indica se ainda existem perguntas pendentes."""
        self.clarification_responses.append(answer)
        return len(self.clarification_responses) < len(self.clarification_questions)
