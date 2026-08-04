"""Recuperação e resposta baseadas exclusivamente no documento."""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from deep_research.config import RETRIEVAL_CANDIDATES
from deep_research.models import QuestionResponse, Source

from .llm_service import get_llm
from .rerank_service import rerank_documents


def build_sources(documents: list[Document]) -> list[Source]:
    return [
        Source(
            page=document.metadata["page"] + 1,
            excerpt=" ".join(document.page_content.split())[:300],
        )
        for document in documents
    ]


def answer_from_vectorstore(
    vectorstore: Chroma,
    question: str,
) -> QuestionResponse:
    candidates = vectorstore.similarity_search(
        question,
        k=RETRIEVAL_CANDIDATES,
    )
    sources = rerank_documents(question, candidates)
    context = "\n\n".join(
        f"[Página {document.metadata['page'] + 1}]\n{document.page_content}"
        for document in sources
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Responda somente com base no contexto fornecido. Se a resposta "
                "não estiver no documento, informe isso claramente. Não use a web. "
                "Responda em português.",
            ),
            ("human", "Contexto:\n{context}\n\nPergunta: {question}"),
        ]
    )
    answer = (prompt | get_llm() | StrOutputParser()).invoke(
        {"context": context, "question": question}
    )
    return QuestionResponse(answer=answer, sources=build_sources(sources))
