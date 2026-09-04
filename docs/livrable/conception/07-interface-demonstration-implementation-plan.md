# Sorabel Trainer Demonstration Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformer l’interface Web locale Sorabel en une démonstration claire du routage RAG/Text-to-SQL, des profils, des preuves et des refus, sans modifier les services métier.

**Architecture:** La page FastAPI existante reste une application HTML/CSS/JavaScript sans framework. Le navigateur sélectionne l’une des quatre routes existantes selon le profil et le domaine ; le rendu présente exclusivement l’enveloppe `status`, `payload`, `message` renvoyée par le serveur. Les améliorations portent sur la hiérarchie visuelle, les exemples guidés, le contexte d’autorisation et les preuves de sortie.

**Tech Stack:** Python 3.11, FastAPI, pytest, HTML5, CSS3, JavaScript navigateur, UI UX Pro Max comme référence de conception sans dépendance d’exécution.

## Global Constraints

- Conserver FastAPI et les routes `/api/answer`, `/api/search`, `/api/database`, `/api/schema`.
- Ne modifier ni le RAG, ni Text-to-SQL, ni PostgreSQL, ni les règles MCP/RBAC.
- Ne pas ajouter Gradio, React, Tailwind ou une dépendance frontale.
- Le navigateur ne fabrique aucune réponse, aucun code de refus et aucune preuve.
- Afficher un code uniquement quand `payload.error_code` le fournit.
- Préserver le français dans l’interface et les noms techniques officiels dans le code.
- Information accessible au clavier, contraste suffisant et mise en page robuste de 375 à 1440 px.
- Développer en TDD et ne pas modifier les tests d’acceptance fournis pour les faire passer.

---

## File Map

| File | Responsibility |
| --- | --- |
| `tests/integration/test_web_app.py` | Contrat statique de la page, des assets et des enveloppes Web |
| `web_app/static/index.html` | Structure sémantique de la démonstration |
| `web_app/static/app.js` | Contexte profil/mode, exemples, appels API et rendu typé |
| `web_app/static/styles.css` | Design system, états, responsive et accessibilité |

### Task 0: Install the design reference outside the repository

**Files:**
- Install outside the project: `C:/Users/kanda/.codex/skills/ui-ux-pro-max/`
- Do not modify: repository dependency files or runtime code.

**Interfaces:**
- Consumes: public repository `nextlevelbuilder/ui-ux-pro-max-skill`, path `.claude/skills/ui-ux-pro-max`.
- Produces: a Codex design-reference skill available from the next Codex turn.

- [ ] **Step 1: Install the skill with the official Codex installer**

Run with network permission:

```powershell
.\.venv\Scripts\python.exe C:\Users\kanda\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py --repo nextlevelbuilder/ui-ux-pro-max-skill --path .claude/skills/ui-ux-pro-max
```

Expected: the installer reports `ui-ux-pro-max` under `C:/Users/kanda/.codex/skills/`.

- [ ] **Step 2: Verify installation without copying it into Sorabel**

```powershell
Get-Content C:\Users\kanda\.codex\skills\ui-ux-pro-max\SKILL.md -TotalCount 20
git status --short
```

Expected: the skill header is readable and Git shows no new skill files inside the Sorabel repository. Start the implementation in the next Codex turn so the installed skill is available.

### Task 1: Create the governed demonstration shell

**Files:**
- Modify: `tests/integration/test_web_app.py`
- Modify: `web_app/static/index.html`

**Interfaces:**
- Consumes: `GET /`, `#profile`, `#mode`, `#question-form`, `#result`.
- Produces: `#governed-flow`, `#active-context`, `#tool-name`, `#scope-description`, `#examples`, `#examples-list` for `app.js`.

- [ ] **Step 1: Write the failing semantic-shell test**

Add this test to `tests/integration/test_web_app.py`:

```python
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
        'id="examples"',
        'id="examples-list"',
    ):
        assert marker in response.text
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_web_app.py::test_root_exposes_the_governed_demo_structure -q --basetemp .test-tmp\ui-shell-red
```

Expected: `FAIL` because `class="skip-link"` and the new IDs are absent.

- [ ] **Step 3: Add the semantic shell**

In `web_app/static/index.html`, add immediately after `<body>`:

```html
<a class="skip-link" href="#question">Aller à la question</a>
```

Replace the current introductory principles with this governed flow:

```html
<ol id="governed-flow" class="governed-flow" aria-label="Parcours gouverné">
  <li><span>1</span><strong>Profil</strong><small>détermine le périmètre</small></li>
  <li><span>2</span><strong>Outil</strong><small>RAG ou SQL</small></li>
  <li><span>3</span><strong>Contrôle</strong><small>preuves et droits</small></li>
  <li><span>4</span><strong>Résultat</strong><small>vérifiable ou refusé</small></li>
</ol>
```

Inside `.workspace`, after `.workspace-heading`, add:

```html
<aside id="active-context" class="active-context" aria-live="polite">
  <div>
    <span class="context-label">Outil appelé</span>
    <strong id="tool-name">answer_question</strong>
  </div>
  <p id="scope-description">Documents autorisés avec réponse citée ou refus hors corpus.</p>
</aside>
```

Inside `#question-form`, between the textarea and `.form-actions`, add:

```html
<section id="examples" class="examples" aria-labelledby="examples-title">
  <div class="examples-heading">
    <strong id="examples-title">Questions de démonstration</strong>
    <small>Cliquez pour remplir, puis lancez la requête.</small>
  </div>
  <div id="examples-list" class="example-list"></div>
</section>
```

Keep the existing selectors, form action, loading region and result region unchanged.

- [ ] **Step 4: Run the shell tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_web_app.py::test_root_serves_the_browser_application tests\integration\test_web_app.py::test_root_exposes_the_governed_demo_structure -q --basetemp .test-tmp\ui-shell-green
```

Expected: `2 passed`.

- [ ] **Step 5: Commit the shell**

```powershell
git add tests/integration/test_web_app.py web_app/static/index.html
git commit -m "feat(ui): add governed demonstration shell"
```

### Task 2: Add profile-aware examples and explicit output evidence

**Files:**
- Modify: `tests/integration/test_web_app.py`
- Modify: `web_app/static/app.js`

**Interfaces:**
- Consumes: DOM IDs created by Task 1 and the common response envelope.
- Produces: `EXAMPLES_BY_CONTEXT`, `updateContext()`, `renderExamples()`, and explicit refusal-code rendering.

- [ ] **Step 1: Write the failing JavaScript-contract tests**

Add these tests to `tests/integration/test_web_app.py`:

```python
def test_browser_script_contains_profile_aware_demo_scenarios():
    with TestClient(app) as client:
        script = client.get("/static/app.js").text

    assert "EXAMPLES_BY_CONTEXT" in script
    assert "Quelle est la tension assignée du produit REF-8842 ?" in script
    assert "Combien de commandes en avril ?" in script
    assert "Supprime les commandes de test." in script
    assert "Quelle est la marge du produit REF-8842 ?" in script
    assert "Quel est le bilan carbone de REF-8842 ?" in script


def test_browser_script_renders_server_refusal_codes_without_inventing_them():
    with TestClient(app) as client:
        script = client.get("/static/app.js").text

    assert "payload.error_code" in script
    assert "Aucune donnée métier n’a été produite." in script
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_web_app.py::test_browser_script_contains_profile_aware_demo_scenarios tests\integration\test_web_app.py::test_browser_script_renders_server_refusal_codes_without_inventing_them -q --basetemp .test-tmp\ui-script-red
```

Expected: both tests fail because the configuration and refusal evidence do not exist.

- [ ] **Step 3: Define the exact contexts and examples**

At the top of `web_app/static/app.js`, after the DOM lookups, add:

```javascript
const toolName = document.querySelector("#tool-name");
const scopeDescription = document.querySelector("#scope-description");
const examples = document.querySelector("#examples");
const examplesList = document.querySelector("#examples-list");

const EXAMPLES_BY_CONTEXT = {
  "support:rag": [
    { label: "Réponse citée", question: "Quelle est la tension assignée du produit REF-8842 ?" },
    { label: "Refus hors corpus", question: "Quelle est la politique de télétravail chez Sorabel ?" },
  ],
  "commercial:rag": [
    { label: "Fiche produit", question: "Quelle est la tension assignée du produit REF-8842 ?" },
    { label: "Notice", question: "Comment installer le produit REF-8842 ?" },
  ],
  "developer:rag": [
    { label: "Recherche exacte", question: "REF-8842" },
    { label: "Recherche métier", question: "disjoncteur triphasé" },
  ],
  "support:sql": [
    { label: "Stock autorisé", question: "Quel est le stock de la référence REF-8842 ?" },
    { label: "Donnée sensible", question: "Quelle est la marge du produit REF-8842 ?" },
  ],
  "commercial:sql": [
    { label: "Analyse autorisée", question: "Combien de commandes en avril ?" },
    { label: "Écriture interdite", question: "Supprime les commandes de test." },
    { label: "Hors schéma", question: "Quel est le bilan carbone de REF-8842 ?" },
  ],
  "developer:sql": [],
};

const CONTEXT_BY_MODE = {
  "support:rag": ["answer_question", "Documents Support : réponse citée ou refus hors corpus."],
  "commercial:rag": ["answer_question", "Documents commerciaux : réponse citée ou refus hors corpus."],
  "developer:rag": ["search_docs", "Recherche de passages classés sans génération de réponse."],
  "support:sql": ["ask_database", "Vues Support en lecture seule ; marges et prix d’achat interdits."],
  "commercial:sql": ["ask_database", "Vues commerciales autorisées en lecture seule."],
  "developer:sql": ["get_schema", "Catalogue SQL filtré et versionné, sans accès aux lignes métier."],
};
```

- [ ] **Step 4: Render the context and example buttons**

Add these functions before `renderEnvelope`:

```javascript
function contextKey() {
  return `${profileField.value}:${modeField.value}`;
}

function renderExamples() {
  const items = EXAMPLES_BY_CONTEXT[contextKey()] || [];
  examplesList.replaceChildren();
  examples.hidden = items.length === 0;
  items.forEach((item) => {
    const button = element("button", "example-chip");
    button.type = "button";
    button.dataset.question = item.question;
    button.append(element("strong", "", item.label));
    button.append(element("span", "", item.question));
    examplesList.append(button);
  });
}

function updateContext() {
  const [tool, description] = CONTEXT_BY_MODE[contextKey()];
  toolName.textContent = tool;
  scopeDescription.textContent = description;
  renderExamples();
}
```

Add this event handler after the existing form listener:

```javascript
examplesList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-question]");
  if (!button || questionField.disabled) return;
  questionField.value = button.dataset.question;
  questionField.focus();
});
```

Call `updateContext()` at the end of `updateMode()` immediately before `clearResult()`.

- [ ] **Step 5: Render refusals as policy decisions, not answers**

Replace the refusal branch in `renderEnvelope` with:

```javascript
const isRefusal = ["hors_corpus", "invalid_request", "refused", "clarification"].includes(status);
const card = element("article", `result-card ${isRefusal ? "refusal" : "error"}`);
card.append(element("p", "status", isRefusal ? "Décision contrôlée" : "Erreur technique"));
if (payload.error_code) {
  card.append(element("code", "error-code", payload.error_code));
}
card.append(
  element("h3", "", isRefusal ? "Le système ne peut pas répondre" : "Erreur technique contrôlée"),
);
card.append(element("p", "answer", message));
if (isRefusal) {
  card.append(element("p", "no-result", "Aucune donnée métier n’a été produite."));
}
result.append(card);
```

- [ ] **Step 6: Run the script-contract and endpoint tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_web_app.py -q --basetemp .test-tmp\ui-script-green
```

Expected: all tests in `test_web_app.py` pass.

- [ ] **Step 7: Commit interaction and evidence rendering**

```powershell
git add tests/integration/test_web_app.py web_app/static/app.js
git commit -m "feat(ui): guide demo scenarios and typed evidence"
```

### Task 3: Apply the accessible trainer-demo visual system

**Files:**
- Modify: `tests/integration/test_web_app.py`
- Modify: `web_app/static/styles.css`

**Interfaces:**
- Consumes: class names introduced in Tasks 1 and 2.
- Produces: responsive, focus-visible and reduced-motion presentation styling.

- [ ] **Step 1: Write the failing CSS-contract test**

Add this test to `tests/integration/test_web_app.py`:

```python
def test_stylesheet_supports_demo_components_and_accessibility_preferences():
    with TestClient(app) as client:
        stylesheet = client.get("/static/styles.css").text

    for selector in (
        ".skip-link",
        ".governed-flow",
        ".active-context",
        ".example-chip",
        ".error-code",
        ".no-result",
        ":focus-visible",
        "prefers-reduced-motion",
    ):
        assert selector in stylesheet
```

- [ ] **Step 2: Run the CSS test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_web_app.py::test_stylesheet_supports_demo_components_and_accessibility_preferences -q --basetemp .test-tmp\ui-css-red
```

Expected: `FAIL` because `.skip-link` is absent.

- [ ] **Step 3: Add component styles**

Append these rules before the existing media queries in `web_app/static/styles.css`:

```css
.skip-link {
  position: fixed;
  left: 16px;
  top: 12px;
  z-index: 20;
  padding: 10px 14px;
  color: white;
  background: var(--ink);
  border-radius: 8px;
  transform: translateY(-160%);
}
.skip-link:focus { transform: translateY(0); }

.governed-flow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 32px 0 0;
  padding: 0;
  list-style: none;
}
.governed-flow li {
  min-width: 0;
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
}
.governed-flow span,
.context-label { color: var(--teal-dark); font-size: 0.68rem; font-weight: 850; text-transform: uppercase; }
.governed-flow strong,
.governed-flow small { display: block; }
.governed-flow small { margin-top: 3px; color: var(--muted); font-size: 0.7rem; }

.active-context {
  display: grid;
  grid-template-columns: minmax(140px, 0.4fr) minmax(220px, 1fr);
  gap: 18px;
  align-items: center;
  margin-bottom: 24px;
  padding: 15px 17px;
  border: 1px solid #b9ddd5;
  border-radius: 12px;
  background: var(--mint);
}
.active-context strong { display: block; margin-top: 3px; font-family: ui-monospace, monospace; }
.active-context p { margin: 0; color: var(--muted); font-size: 0.82rem; line-height: 1.45; }

.examples { margin-top: 15px; }
.examples-heading { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); font-size: 0.72rem; }
.example-list { display: grid; gap: 8px; margin-top: 9px; }
.example-chip {
  width: 100%;
  padding: 10px 12px;
  color: var(--ink);
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: white;
  cursor: pointer;
}
.example-chip:hover { border-color: var(--teal); background: #f2fbf8; }
.example-chip strong,
.example-chip span { display: block; }
.example-chip strong { color: var(--teal-dark); font-size: 0.72rem; }
.example-chip span { margin-top: 2px; font-size: 0.78rem; line-height: 1.35; }

.error-code {
  display: inline-block;
  margin-bottom: 10px;
  padding: 4px 7px;
  color: #7a251d;
  background: #ffe6e1;
  border-radius: 6px;
  font-weight: 800;
}
.no-result { margin: 12px 0 0; color: var(--muted); font-size: 0.78rem; font-weight: 700; }

button:focus-visible,
select:focus-visible,
textarea:focus-visible,
a:focus-visible {
  outline: 3px solid var(--amber);
  outline-offset: 3px;
}
```

- [ ] **Step 4: Add responsive and reduced-motion behavior**

Inside the existing `@media (max-width: 940px)` block add:

```css
.governed-flow { grid-template-columns: repeat(2, 1fr); text-align: left; }
```

Inside the existing `@media (max-width: 640px)` block add:

```css
.governed-flow { grid-template-columns: 1fr; }
.active-context { grid-template-columns: 1fr; }
.examples-heading { flex-direction: column; }
```

Append:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 5: Run the complete Web integration file**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\integration\test_web_app.py -q --basetemp .test-tmp\ui-css-green
```

Expected: every test in `test_web_app.py` passes.

- [ ] **Step 6: Commit the visual system**

```powershell
git add tests/integration/test_web_app.py web_app/static/styles.css
git commit -m "style(ui): apply accessible trainer demo system"
```

### Task 4: Verify the complete product demonstration

**Files:**
- Modify only if verification reveals a demonstrated defect: the smallest file responsible for that defect, preceded by a failing regression test.
- Verify: `tests/`, `web_app/`, `docs/livrable/VERIFICATION-REPORT.md`.

**Interfaces:**
- Consumes: complete RAG, SQL, MCP and Web implementation.
- Produces: reproducible evidence that the redesign did not change business behavior.

- [ ] **Step 1: Run formatting, typing and all tests**

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe ingest retrieval sql mcp_server application web_app
.\.venv\Scripts\python.exe -m pytest -q --basetemp .test-tmp\ui-full-suite
```

Expected: Ruff passes, mypy reports success, and the complete pytest suite passes with no failed test.

- [ ] **Step 2: Start the local UI**

```powershell
.\.venv\Scripts\python.exe -m uvicorn web_app.server:app --host 127.0.0.1 --port 8780
```

Expected: `Uvicorn running on http://127.0.0.1:8780`.

- [ ] **Step 3: Verify the seven visible demonstration decisions**

At `http://127.0.0.1:8780`, execute:

| Profile | Mode | Question | Expected visible decision |
| --- | --- | --- | --- |
| Support | RAG | `Quelle est la tension assignée du produit REF-8842 ?` | `230/400 V AC` plus title, reference, date |
| Support | RAG | `Quelle est la politique de télétravail chez Sorabel ?` | controlled out-of-corpus refusal |
| Developer | RAG | `REF-8842` | ranked passages without generated answer |
| Commercial | SQL | `Combien de commandes en avril ?` | structured count plus generated SQL and versions |
| Support | SQL | `Quel est le stock de la référence REF-8842 ?` | authorized warehouse rows plus SQL |
| Support | SQL | `Quelle est la marge du produit REF-8842 ?` | authorization refusal and no business result |
| Commercial | SQL | `Supprime les commandes de test.` | write refusal and no business result |

- [ ] **Step 4: Verify responsive behavior**

Use browser responsive mode at 375, 768, 1024 and 1440 px. Expected at every width: no horizontal page overflow, no clipped label or code, reachable controls, visible focus, readable result table through its local horizontal scroller.

- [ ] **Step 5: Review the public diff**

```powershell
git status --short --branch
git diff --check HEAD~3..HEAD
git diff --stat HEAD~3..HEAD
```

Expected: only the approved static UI, Web tests, design and plan are present; no environment file, journal, database, index or private study/oral note is staged.

- [ ] **Step 6: Record final verification in a focused commit only if a tracked report changed**

If `docs/livrable/VERIFICATION-REPORT.md` is updated with actual command outputs, commit it alone:

```powershell
git add docs/livrable/VERIFICATION-REPORT.md
git commit -m "docs(ui): record demonstration verification"
```

If the report is unchanged, do not create an empty commit.
