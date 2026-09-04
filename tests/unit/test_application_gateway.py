from retrieval.models import AnswerResult, CitationSource, SearchHit
from sql.models import SqlToolResult

from application.gateway import ApplicationGateway


class WorkingRagService:
    def answer_question(self, question: str, profile: str) -> AnswerResult:
        return AnswerResult(
            status="ok",
            answer="230/400 V AC",
            sources=[
                CitationSource(
                    titre="Fiche technique REF-8842",
                    reference="REF-8842",
                    date="2024-05-25",
                )
            ],
        )

    def search_docs(self, query: str, profile: str, limit: int = 5) -> list[SearchHit]:
        return [
            SearchHit(
                chunk_id="chunk-1",
                doc_id="doc-1",
                score=1.0,
                text="Fiche technique REF-8842",
                title="Fiche technique REF-8842",
                reference="REF-8842",
                version="2.1",
                date="2024-05-25",
                doc_type="fiche_technique",
                collection="fiches_techniques",
                source_path="fiches/ref-8842.pdf",
            )
        ][:limit]


class FailingRagService:
    def answer_question(self, question: str, profile: str) -> AnswerResult:
        raise RuntimeError("private diagnostic")


class WorkingSqlService:
    def ask_database(self, question: str, profile: str) -> SqlToolResult:
        return SqlToolResult(
            status="ok",
            payload={"sql": "SELECT COUNT(*)", "rows": [[12]]},
        )

    def get_schema(self, profile: str) -> SqlToolResult:
        return SqlToolResult(status="ok", payload={"profile": profile})

    def check_stock(self, reference: str, profile: str) -> SqlToolResult:
        return SqlToolResult(status="ok", payload={"reference": reference})

    def order_status(self, order_id: str, profile: str) -> SqlToolResult:
        return SqlToolResult(status="ok", payload={"order_id": order_id})


def test_valid_question_preserves_the_rag_envelope():
    result = ApplicationGateway(WorkingRagService()).answer_question(
        "Quelle est la tension assignée du produit REF-8842 ?",
        "support",
    )

    assert result["status"] == "ok"
    assert result["payload"]["answer"] == "230/400 V AC"
    assert result["payload"]["sources"][0]["reference"] == "REF-8842"


def test_empty_question_is_an_invalid_request():
    result = ApplicationGateway(WorkingRagService()).answer_question("   ", "support")

    assert result == {
        "status": "invalid_request",
        "payload": {},
        "message": "Question must not be empty.",
    }


def test_unknown_profile_is_an_invalid_request():
    result = ApplicationGateway(WorkingRagService()).answer_question("Question", "administrator")

    assert result == {
        "status": "invalid_request",
        "payload": {},
        "message": "Unknown profile.",
    }


def test_unexpected_failure_returns_a_safe_error():
    result = ApplicationGateway(FailingRagService()).answer_question("Question", "support")

    assert result == {
        "status": "execution_error",
        "payload": {},
        "message": "The RAG service could not process this request.",
    }
    assert "private diagnostic" not in result["message"]


def test_developer_can_search_documents_without_generation():
    gateway = ApplicationGateway(WorkingRagService())

    result = gateway.search_docs("REF-8842", "developer", limit=3)

    assert result["status"] == "ok"
    assert result["payload"]["hits"][0]["metadata"]["reference"] == "REF-8842"


def test_developer_cannot_generate_an_answer():
    result = ApplicationGateway(WorkingRagService()).answer_question("Question", "developer")

    assert result == {
        "status": "refused",
        "payload": {},
        "message": "answer_question is not authorized for the developer profile.",
    }


def test_commercial_question_is_delegated_to_the_sql_service():
    gateway = ApplicationGateway(WorkingRagService(), WorkingSqlService())

    result = gateway.ask_database("combien de commandes en avril ?", "commercial")

    assert result["status"] == "ok"
    assert result["payload"]["sql"] == "SELECT COUNT(*)"
    assert result["payload"]["rows"] == [[12]]


def test_support_cannot_discover_the_semantic_schema():
    gateway = ApplicationGateway(WorkingRagService(), WorkingSqlService())

    result = gateway.get_schema("support")

    assert result["status"] == "refused"
