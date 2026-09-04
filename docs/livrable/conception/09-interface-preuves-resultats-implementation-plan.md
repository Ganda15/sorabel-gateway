# Result Evidence Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove prefilled demonstration questions and make every RAG result, SQL result, and refusal visibly verifiable in the existing local Web interface.

**Architecture:** FastAPI and the business services remain unchanged. The static HTML removes the examples container; JavaScript renders only evidence received from the common response envelope or deterministically derived from returned SQL; CSS adds a compact proof summary and a native expandable details block.

**Tech Stack:** FastAPI TestClient, HTML5, CSS, browser JavaScript, pytest, Ruff, mypy.

## Global Constraints

- Do not modify RAG, SQL, MCP, authentication, or authorization business logic.
- Do not invent a source, version, query, parameter, error code, or result in the browser.
- Omit unavailable evidence fields.
- Keep the technical disclosure keyboard accessible with native HTML `details` and `summary`.
- Preserve the common `status`, `payload`, `message` response envelope.

---

## File Map

| File | Responsibility |
| --- | --- |
| `tests/integration/test_web_app.py` | executable UI contract for removed examples and visible proof markers |
| `web_app/static/index.html` | page structure without prefilled demonstration questions |
| `web_app/static/app.js` | RAG source rendering, SQL evidence rendering, technical disclosure, refusal rendering |
| `web_app/static/styles.css` | compact evidence grid and accessible disclosure styling |
| `docs/livrable/VERIFICATION-REPORT.md` | final test counts and browser verification record |

### Task 1: Lock the revised browser contract with failing tests

**Files:**
- Modify: `tests/integration/test_web_app.py`

**Interfaces:**
- Consumes: static assets served by FastAPI at `/`, `/static/app.js`, and `/static/styles.css`.
- Produces: tests requiring removal of `#examples`, RAG source metadata, SQL proof fields, technical details, and refusal evidence.

- [ ] **Step 1: Enrich the SQL stub payload**

Replace the SQL payload in `StubGateway.ask_database` with:

```python
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
```

- [ ] **Step 2: Replace example assertions with absence and evidence assertions**

Use these focused contracts:

```python
def test_root_omits_prefilled_demonstration_questions():
    with TestClient(app) as client:
        response = client.get("/")

    assert 'id="examples"' not in response.text
    assert 'id="examples-list"' not in response.text
    assert "Questions de démonstration" not in response.text


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


def test_stylesheet_supports_evidence_summary_and_disclosure():
    with TestClient(app) as client:
        stylesheet = client.get("/static/styles.css").text

    for selector in (
        ".evidence-grid",
        ".evidence-item",
        ".technical-details",
        ".technical-details summary",
    ):
        assert selector in stylesheet

    assert ".example-chip" not in stylesheet
```

- [ ] **Step 3: Strengthen refusal evidence wording**

Update the existing refusal test to require both server error codes and the two absence messages:

```python
assert "payload.error_code" in script
assert "Aucune exécution n’a été lancée." in script
assert "Aucune donnée métier n’a été produite." in script
```

- [ ] **Step 4: Run the Web tests and confirm the intended failure**

Run:

```powershell
uv run pytest tests/integration/test_web_app.py -q
```

Expected: failures mention the still-present examples and missing evidence renderer/styles.

- [ ] **Step 5: Commit the failing contract**

```powershell
git add tests/integration/test_web_app.py
git commit -m "test(ui): require verifiable result evidence"
```

### Task 2: Remove all prefilled demonstration questions

**Files:**
- Modify: `web_app/static/index.html`
- Modify: `web_app/static/app.js`
- Modify: `web_app/static/styles.css`

**Interfaces:**
- Consumes: existing form, profile selector, mode selector, and `CONTEXT_BY_MODE`.
- Produces: manual-only question entry with no example-specific DOM or event listeners.

- [ ] **Step 1: Remove the examples section from the form**

Delete this complete block from `index.html`:

```html
<section id="examples" class="examples" aria-labelledby="examples-title">
  <div class="examples-heading">
    <strong id="examples-title">Questions de démonstration</strong>
    <small>Cliquez pour remplir, puis lancez la requête.</small>
  </div>
  <div id="examples-list" class="example-list"></div>
</section>
```

- [ ] **Step 2: Remove example-only JavaScript**

Delete `examples`, `examplesList`, `EXAMPLES_BY_CONTEXT`, `renderExamples`, the call to
`renderExamples()` in `updateContext`, and the `examplesList` click handler. Keep
`CONTEXT_BY_MODE`, `contextKey`, and `updateContext` unchanged otherwise.

- [ ] **Step 3: Remove example-only CSS**

Delete `.examples`, `.examples-heading`, `.example-list`, `.example-chip`, its hover/child
rules, and the mobile `.examples-heading` override.

- [ ] **Step 4: Run the removal test**

```powershell
uv run pytest tests/integration/test_web_app.py::test_root_omits_prefilled_demonstration_questions -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit the focused removal**

```powershell
git add web_app/static/index.html web_app/static/app.js web_app/static/styles.css
git commit -m "refactor(ui): remove prefilled demo questions"
```

### Task 3: Render compact SQL evidence and expandable technical details

**Files:**
- Modify: `web_app/static/app.js`
- Modify: `web_app/static/styles.css`
- Test: `tests/integration/test_web_app.py`

**Interfaces:**
- Consumes: SQL payload keys `sql`, `parameters`, `columns`, `rows`, `row_count`, `backend`, `dataset_version`, `data_as_of`, `semantic_schema_version`, and `policy_version`.
- Produces: `extractSemanticResources(sql: string): string[]` and `renderSqlEvidence(container: HTMLElement, payload: object): void`.

- [ ] **Step 1: Add deterministic SQL resource extraction**

Add before `renderSql`:

```javascript
function extractSemanticResources(sql) {
  const matches = String(sql || "").match(/\bsorabel_semantic\.[a-z_][a-z0-9_]*/gi) || [];
  return [...new Set(matches)];
}

function appendEvidenceItem(grid, label, value) {
  if (value === undefined || value === null || value === "") return;
  const item = element("div", "evidence-item");
  item.append(element("span", "", label));
  item.append(element("strong", "", String(value)));
  grid.append(item);
}
```

- [ ] **Step 2: Add the SQL proof renderer**

```javascript
function renderSqlEvidence(container, payload) {
  container.append(element("p", "sources-title", "Preuve d’exécution"));
  const evidence = element("section", "execution-proof");
  evidence.setAttribute("aria-label", "Preuve d’exécution SQL");
  const grid = element("div", "evidence-grid");
  const resources = extractSemanticResources(payload.sql).join(" · ");
  const rowCount = payload.row_count ?? (Array.isArray(payload.rows) ? payload.rows.length : null);

  appendEvidenceItem(grid, "Backend", payload.backend);
  appendEvidenceItem(grid, "Vue autorisée", resources);
  appendEvidenceItem(grid, "Colonnes", (payload.columns || []).join(" · "));
  appendEvidenceItem(grid, "Nombre de lignes", rowCount);
  appendEvidenceItem(grid, "Données au", payload.data_as_of);
  appendEvidenceItem(grid, "Dataset", payload.dataset_version);
  appendEvidenceItem(grid, "Schéma sémantique", payload.semantic_schema_version);
  appendEvidenceItem(grid, "Politique", payload.policy_version);
  evidence.append(grid);

  const details = element("details", "technical-details");
  details.append(element("summary", "", "Détails techniques"));
  details.append(element("p", "technical-label", "SQL exécuté"));
  details.append(element("code", "sql-code", payload.sql || ""));
  if (payload.parameters && Object.keys(payload.parameters).length > 0) {
    details.append(element("p", "technical-label", "Paramètres"));
    details.append(element("code", "sql-code", JSON.stringify(payload.parameters, null, 2)));
  }
  evidence.append(details);
  container.append(evidence);
}
```

- [ ] **Step 3: Make `renderSql` delegate evidence rendering**

Remove the old `SQL exécuté` and `trace` block at the end of `renderSql`, then call:

```javascript
renderSqlEvidence(container, payload);
```

- [ ] **Step 4: Add compact, responsive evidence styles**

```css
.execution-proof { margin-top: 10px; }
.evidence-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}
.evidence-item {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #dce9e6;
  border-radius: 8px;
  background: white;
}
.evidence-item span,
.evidence-item strong { display: block; }
.evidence-item span { color: var(--muted); font-size: 0.68rem; font-weight: 750; }
.evidence-item strong { margin-top: 3px; overflow-wrap: anywhere; font-size: 0.78rem; }
.technical-details {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid #dce9e6;
  border-radius: 8px;
  background: white;
}
.technical-details summary { cursor: pointer; font-size: 0.78rem; font-weight: 800; }
.technical-label { margin: 12px 0 6px; color: var(--muted); font-size: 0.7rem; font-weight: 800; }
```

At the `max-width: 640px` breakpoint add:

```css
.evidence-grid { grid-template-columns: 1fr; }
```

- [ ] **Step 5: Run the evidence tests**

```powershell
uv run pytest tests/integration/test_web_app.py -q
```

Expected: all Web integration tests pass.

- [ ] **Step 6: Commit the proof rendering**

```powershell
git add web_app/static/app.js web_app/static/styles.css tests/integration/test_web_app.py
git commit -m "feat(ui): show verifiable result evidence"
```

### Task 4: Make refusals prove non-execution

**Files:**
- Modify: `web_app/static/app.js`
- Test: `tests/integration/test_web_app.py`

**Interfaces:**
- Consumes: non-`ok` envelope status, `payload.error_code`, and `message`.
- Produces: a refusal result containing the server error code and explicit absence of execution and business output.

- [ ] **Step 1: Add the non-execution statement**

In the refusal branch use:

```javascript
if (isRefusal) {
  card.append(element("p", "no-result", "Aucune exécution n’a été lancée."));
  card.append(element("p", "no-result", "Aucune donnée métier n’a été produite."));
}
```

- [ ] **Step 2: Run the refusal contract**

```powershell
uv run pytest tests/integration/test_web_app.py::test_browser_script_renders_server_refusal_codes_without_inventing_them -q
```

Expected: `1 passed`.

- [ ] **Step 3: Commit refusal evidence**

```powershell
git add web_app/static/app.js tests/integration/test_web_app.py
git commit -m "feat(ui): clarify refused requests are not executed"
```

### Task 5: Verify the complete repository and browser behavior

**Files:**
- Modify: `docs/livrable/VERIFICATION-REPORT.md`

**Interfaces:**
- Consumes: completed static UI and the existing running FastAPI app.
- Produces: current, reproducible verification evidence.

- [ ] **Step 1: Run focused quality checks**

```powershell
uv run pytest tests/integration/test_web_app.py -q
uv run ruff check web_app tests/integration/test_web_app.py
uv run mypy web_app
```

Expected: all commands pass.

- [ ] **Step 2: Run the complete test suite**

```powershell
uv run pytest -q
```

Expected: all tests pass; only already-known dependency deprecation warnings may remain.

- [ ] **Step 3: Verify manually in the browser**

At `http://127.0.0.1:8780/`, verify:

1. no prefilled questions are visible;
2. a covered RAG answer shows title, reference, and date;
3. a valid SQL answer shows PostgreSQL, authorized semantic view, columns, row count, date, and versions;
4. opening **Détails techniques** reveals exact SQL and parameters;
5. a refused write shows `UNSAFE_SQL`, no execution, and no business data;
6. keyboard focus reaches the disclosure and no horizontal overflow appears at 375 px.

- [ ] **Step 4: Update the verification report with actual results**

Record exact test counts, commands, browser scenarios, and any remaining warnings. Do not copy
the previous counts unless the commands produce them again.

- [ ] **Step 5: Commit final verification evidence**

```powershell
git add docs/livrable/VERIFICATION-REPORT.md
git commit -m "docs(ui): verify result evidence interface"
```
