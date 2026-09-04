from fastapi.testclient import TestClient

from web_app.server import app, get_gateway


class StubGateway:
    def answer_question(self, question: str, profile: str) -> dict:
        return {
            "status": "ok",
            "payload": {
                "answer": "230/400 V AC",
                "sources": [
                    {
                        "titre": "Fiche technique REF-8842",
                        "reference": "REF-8842",
                        "date": "2024-05-25",
                    }
                ],
            },
            "message": "",
        }

    def search_docs(self, query: str, profile: str, limit: int = 5) -> dict:
        return {
            "status": "ok",
            "payload": {
                "hits": [
                    {
                        "doc_id": "doc-1",
                        "score": 1.0,
                        "text": "Fiche technique REF-8842",
                        "metadata": {
                            "reference": "REF-8842",
                            "doc_type": "fiche_technique",
                            "version": "2.1",
                            "date": "2024-05-25",
                        },
                    }
                ]
            },
            "message": "",
        }

    def ask_database(self, question: str, profile: str) -> dict:
        return {
            "status": "ok",
            "payload": {
                "sql": (
                    "SELECT COUNT(*) AS nombre_commandes "
                    "FROM sorabel_semantic.commandes_commercial "
                    "WHERE date_commande >= %(date_debut)s"
                ),
                "parameters": {"date_debut": "2024-04-01"},
                "columns": ["nombre_commandes"],
                "rows": [[42]],
                "row_count": 1,
                "backend": "postgres",
                "dataset_version": "dataset-postgres-v1",
                "data_as_of": "2025-12-31",
                "semantic_schema_version": "semantic-postgres-v1",
                "policy_version": "policy-v1",
            },
            "message": "",
        }

    def get_schema(self, profile: str) -> dict:
        return {
            "status": "ok",
            "payload": {
                "profile": profile,
                "semantic_schema_version": "semantic-postgres-v1",
                "views": {"produits_commercial": {"columns": {"ref": {}}}},
            },
            "message": "",
        }


def test_root_serves_the_browser_application():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="question-form"' in response.text
    assert 'id="question"' in response.text
    assert 'id="profile"' in response.text
    assert 'value="developer"' in response.text
    assert 'id="result"' in response.text
    assert "/static/styles.css" in response.text
    assert "/static/app.js" in response.text


def test_root_exposes_the_governed_demo_structure():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    for marker in (
        'class="skip-link"',
        'id="governed-flow"',
        'id="active-context"',
        'id="tool-name"',
        'id="scope-description"',
    ):
        assert marker in response.text


def test_root_omits_prefilled_demonstration_questions():
    with TestClient(app) as client:
        response = client.get("/")

    assert 'id="examples"' not in response.text
    assert 'id="examples-list"' not in response.text
    assert "Questions de démonstration" not in response.text


def test_browser_assets_are_available():
    with TestClient(app) as client:
        stylesheet = client.get("/static/styles.css")
        script = client.get("/static/app.js")

    assert stylesheet.status_code == 200
    assert "text/css" in stylesheet.headers["content-type"]
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]


def test_browser_loads_the_current_profile_scope_script_version():
    with TestClient(app) as client:
        response = client.get("/")

    assert '/static/app.js?v=profile-scope-v2' in response.text


def test_browser_script_renders_documentary_and_sql_evidence():
    with TestClient(app) as client:
        script = client.get("/static/app.js").text

    for marker in (
        "Sources utilisées",
        "renderSqlEvidence",
        "extractSemanticResources",
        "payload.parameters",
        "payload.data_as_of",
        "payload.policy_version",
        "Détails techniques",
    ):
        assert marker in script

    assert "EXAMPLES_BY_CONTEXT" not in script


def test_browser_script_renders_server_refusal_codes_without_inventing_them():
    with TestClient(app) as client:
        script = client.get("/static/app.js").text

    assert "payload.error_code" in script
    assert "Aucune exécution n’a été lancée." in script
    assert "Aucune donnée métier n’a été produite." in script


def test_developer_sql_mode_cannot_look_like_a_business_answer():
    with TestClient(app) as client:
        script = client.get("/static/app.js").text

    assert 'questionField.value = "";' in script
    assert "Aucune question métier n’a été exécutée." in script
    assert "Aucune ligne de données métier n’a été retournée." in script


def test_stylesheet_supports_demo_components_and_accessibility_preferences():
    with TestClient(app) as client:
        stylesheet = client.get("/static/styles.css").text

    for selector in (
        ".skip-link",
        ".governed-flow",
        ".active-context",
        ".error-code",
        ".no-result",
        ":focus-visible",
        "prefers-reduced-motion",
    ):
        assert selector in stylesheet


def test_stylesheet_supports_evidence_summary_and_disclosure():
    with TestClient(app) as client:
        stylesheet = client.get("/static/styles.css").text

    for selector in (
        ".layout > *",
        ".evidence-grid",
        ".evidence-item",
        ".technical-details",
        ".technical-details summary",
    ):
        assert selector in stylesheet

    assert ".example-chip" not in stylesheet


def test_answer_endpoint_returns_the_common_envelope():
    app.dependency_overrides[get_gateway] = lambda: StubGateway()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/answer",
                json={
                    "question": "Quelle est la tension assignée de REF-8842 ?",
                    "profile": "support",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["payload"]["answer"] == "230/400 V AC"


def test_invalid_request_uses_a_typed_error_envelope():
    app.dependency_overrides[get_gateway] = lambda: StubGateway()
    try:
        with TestClient(app) as client:
            response = client.post("/api/answer", json={"question": "", "profile": "unknown"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {
        "status": "invalid_request",
        "payload": {},
        "message": "Invalid question or profile.",
    }


def test_developer_search_endpoint_returns_ranked_passages():
    app.dependency_overrides[get_gateway] = lambda: StubGateway()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/search",
                json={"query": "REF-8842", "profile": "developer", "limit": 3},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["payload"]["hits"][0]["metadata"]["reference"] == "REF-8842"


def test_database_endpoint_returns_rows_and_generated_sql():
    app.dependency_overrides[get_gateway] = lambda: StubGateway()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/database",
                json={"question": "combien de commandes en avril ?", "profile": "commercial"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["payload"]["rows"] == [[42]]
    assert "SELECT" in response.json()["payload"]["sql"]


def test_schema_endpoint_returns_only_the_profile_catalogue():
    app.dependency_overrides[get_gateway] = lambda: StubGateway()
    try:
        with TestClient(app) as client:
            response = client.post("/api/schema", json={"profile": "developer"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["payload"]["profile"] == "developer"
