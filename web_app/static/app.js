const form = document.querySelector("#question-form");
const questionField = document.querySelector("#question");
const profileField = document.querySelector("#profile");
const modeField = document.querySelector("#mode");
const submitButton = document.querySelector("#submit-button");
const submitLabel = document.querySelector("#submit-label");
const queryLabel = document.querySelector("#query-label");
const scopeNote = document.querySelector("#scope-note");
const loading = document.querySelector("#loading");
const result = document.querySelector("#result");
const workspaceEyebrow = document.querySelector("#workspace-eyebrow");
const toolName = document.querySelector("#tool-name");
const scopeDescription = document.querySelector("#scope-description");

const CONTEXT_BY_MODE = {
  "support:rag": ["answer_question", "Documents Support : réponse citée ou refus hors corpus."],
  "commercial:rag": [
    "answer_question",
    "Documents commerciaux : réponse citée ou refus hors corpus.",
  ],
  "developer:rag": [
    "search_docs",
    "Recherche de passages classés sans génération de réponse.",
  ],
  "support:sql": [
    "ask_database",
    "Vues Support en lecture seule ; marges et prix d’achat interdits.",
  ],
  "commercial:sql": ["ask_database", "Vues commerciales autorisées en lecture seule."],
  "developer:sql": [
    "get_schema",
    "Catalogue SQL filtré et versionné, sans accès aux lignes métier.",
  ],
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function clearResult() {
  result.replaceChildren();
}

function renderSources(container, sources) {
  if (!Array.isArray(sources) || sources.length === 0) return;

  container.append(element("p", "sources-title", "Sources utilisées"));
  const list = element("div", "source-list");
  sources.forEach((source) => {
    const card = element("article", "source");
    card.append(element("strong", "", source.titre || "Document Sorabel"));
    const metadata = [source.reference, source.date].filter(Boolean).join(" · ");
    card.append(element("span", "", metadata));
    list.append(card);
  });
  container.append(list);
}

function renderHits(container, hits) {
  container.append(element("p", "sources-title", `${hits.length} passages classés`));
  const list = element("div", "hit-list");
  hits.forEach((hit, index) => {
    const metadata = hit.metadata || {};
    const card = element("article", "hit");
    card.append(element("span", "hit-rank", `#${index + 1}`));
    card.append(element("strong", "", metadata.reference || "Document Sorabel"));
    card.append(element("p", "", hit.text || "Passage indisponible."));
    card.append(
      element(
        "small",
        "",
        [metadata.doc_type, metadata.version, metadata.date].filter(Boolean).join(" · "),
      ),
    );
    list.append(card);
  });
  container.append(list);
}

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

  if (payload.sql) {
    const details = element("details", "technical-details");
    details.append(element("summary", "", "Détails techniques"));
    details.append(element("p", "technical-label", "SQL exécuté"));
    details.append(element("code", "sql-code", payload.sql));
    if (payload.parameters && Object.keys(payload.parameters).length > 0) {
      details.append(element("p", "technical-label", "Paramètres"));
      details.append(element("code", "sql-code", JSON.stringify(payload.parameters, null, 2)));
    }
    evidence.append(details);
  }
  container.append(evidence);
}

function renderSql(container, payload) {
  const cardTitle = element("p", "status", "Requête PostgreSQL validée · lecture seule");
  container.append(cardTitle);
  container.append(element("h3", "", "Résultat structuré"));

  const table = element("table", "data-table");
  const head = element("thead");
  const headRow = element("tr");
  (payload.columns || []).forEach((column) => headRow.append(element("th", "", column)));
  head.append(headRow);
  table.append(head);

  const body = element("tbody");
  (payload.rows || []).forEach((row) => {
    const tr = element("tr");
    row.forEach((value) => tr.append(element("td", "", String(value ?? ""))));
    body.append(tr);
  });
  table.append(body);
  const tableWrap = element("div", "table-wrap");
  tableWrap.append(table);
  container.append(tableWrap);
  renderSqlEvidence(container, payload);
}

function renderSchema(container, payload) {
  container.append(element("p", "status", "Catalogue sémantique filtré"));
  container.append(element("h3", "", `Schéma visible · ${payload.profile || "profil"}`));
  container.append(element("p", "no-result", "Aucune question métier n’a été exécutée."));
  container.append(
    element("p", "no-result", "Aucune ligne de données métier n’a été retournée."),
  );
  const list = element("div", "schema-list");
  Object.entries(payload.views || {}).forEach(([name, definition]) => {
    const card = element("article", "source");
    card.append(element("strong", "", name));
    card.append(element("span", "", Object.keys(definition.columns || {}).join(" · ")));
    list.append(card);
  });
  container.append(list);
  container.append(
    element("small", "trace", payload.semantic_schema_version || "Version indisponible"),
  );
}

function contextKey() {
  return `${profileField.value}:${modeField.value}`;
}

function updateContext() {
  const [tool, description] = CONTEXT_BY_MODE[contextKey()];
  toolName.textContent = tool;
  scopeDescription.textContent = description;
}

function renderEnvelope(envelope) {
  clearResult();
  const status = envelope?.status || "execution_error";
  const payload = envelope?.payload || {};
  const message = envelope?.message || "Une erreur contrôlée est survenue.";

  if (status === "ok") {
    const card = element("article", "result-card success");
    if (Array.isArray(payload.hits)) {
      card.append(element("p", "status", "Recherche décomposée · sans génération"));
      card.append(element("h3", "", "Passages documentaires"));
      renderHits(card, payload.hits);
    } else if (Array.isArray(payload.rows)) {
      renderSql(card, payload);
    } else if (payload.views) {
      renderSchema(card, payload);
    } else {
      card.append(element("p", "status", "Réponse vérifiée"));
      card.append(element("h3", "", "Résultat documentaire"));
      card.append(element("p", "answer", payload.answer || "Aucune réponse disponible."));
      renderSources(card, payload.sources);
    }
    result.append(card);
    return;
  }

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
    card.append(element("p", "no-result", "Aucune exécution n’a été lancée."));
    card.append(element("p", "no-result", "Aucune donnée métier n’a été produite."));
  }
  result.append(card);
}

async function askQuestion(event) {
  event.preventDefault();
  clearResult();
  loading.hidden = false;
  submitButton.disabled = true;

  try {
    const developerMode = profileField.value === "developer";
    const sqlMode = modeField.value === "sql";
    const endpoint = developerMode
      ? sqlMode
        ? "/api/schema"
        : "/api/search"
      : sqlMode
        ? "/api/database"
        : "/api/answer";
    const body = developerMode
      ? sqlMode
        ? { profile: "developer" }
        : { query: questionField.value, profile: "developer", limit: 3 }
      : { question: questionField.value, profile: profileField.value };
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const envelope = await response.json();
    renderEnvelope(envelope);
  } catch (_error) {
    renderEnvelope({
      status: "execution_error",
      payload: {},
      message: "Le serveur local est indisponible. Vérifiez qu'il est toujours démarré.",
    });
  } finally {
    loading.hidden = true;
    submitButton.disabled = false;
  }
}

function updateMode() {
  const developerMode = profileField.value === "developer";
  const sqlMode = modeField.value === "sql";
  const schemaMode = developerMode && sqlMode;

  workspaceEyebrow.textContent = sqlMode ? "DONNÉES STRUCTURÉES" : "QUESTION DOCUMENTAIRE";
  queryLabel.textContent = developerMode && !sqlMode ? "Votre recherche" : "Votre question";
  submitLabel.textContent = schemaMode
    ? "Afficher le schéma autorisé"
    : developerMode
      ? "Rechercher sans générer"
      : sqlMode
        ? "Interroger la base"
        : "Interroger le corpus";
  scopeNote.textContent = schemaMode
    ? "Mode IDE : catalogue filtré et versionné, sans exécution SQL."
    : developerMode
      ? "Mode IDE : passages classés, sans réponse générée."
      : sqlMode
        ? "SQL validé par AST puis exécuté en transaction READ ONLY."
        : "Le profil filtre les collections documentaires visibles.";
  questionField.placeholder = developerMode
    ? sqlMode
      ? "Aucune question nécessaire pour consulter le catalogue."
      : "Ex. REF-8842"
    : sqlMode
      ? "Ex. Combien de commandes en avril ?"
      : "Ex. Quelle est la tension assignée du produit REF-8842 ?";
  questionField.required = !schemaMode;
  questionField.disabled = schemaMode;
  if (schemaMode) questionField.value = "";
  updateContext();
  clearResult();
}

form.addEventListener("submit", askQuestion);
profileField.addEventListener("change", updateMode);
modeField.addEventListener("change", updateMode);
updateMode();
