from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ingest.models import CollectionName, DocumentType, normalize_reference


class SearchHit(BaseModel):
    """Ranked passage returned by document retrieval."""

    model_config = ConfigDict(str_strip_whitespace=True)

    chunk_id: str
    doc_id: str
    score: float
    text: str
    title: str
    reference: str = ""
    version: str
    date: str
    doc_type: DocumentType
    collection: CollectionName
    source_path: str
    is_primary: bool = True

    dense_score: float | None = None
    lexical_score: float | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None

    @field_validator("reference", mode="before")
    @classmethod
    def normalize_product_reference(cls, value: str | None) -> str:
        return normalize_reference(value)

    def to_payload(self) -> dict:
        """Serialize the hit using the DSI search_docs contract."""
        return {
            "doc_id": self.doc_id,
            "score": self.score,
            "text": self.text,
            "metadata": {
                "reference": self.reference,
                "doc_type": self.doc_type,
                "version": self.version,
                "date": self.date,
            },
        }


class CitationSource(BaseModel):
    """Source metadata required by the answer_question contract."""

    model_config = ConfigDict(str_strip_whitespace=True)

    titre: str
    reference: str
    date: str

    @field_validator("reference", mode="before")
    @classmethod
    def normalize_product_reference(cls, value: str | None) -> str:
        return normalize_reference(value)


class AnswerResult(BaseModel):
    """Documentary answer or explicit outside-corpus refusal."""

    status: Literal["ok", "hors_corpus"]
    answer: str = ""
    sources: list[CitationSource] = Field(default_factory=list)
    message: str = ""

    def to_envelope(self) -> dict:
        """Serialize the result using the common gateway envelope."""
        payload = {}

        if self.status == "ok":
            payload = {
                "answer": self.answer,
                "sources": [source.model_dump() for source in self.sources],
            }

        return {
            "status": self.status,
            "payload": payload,
            "message": self.message,
        }