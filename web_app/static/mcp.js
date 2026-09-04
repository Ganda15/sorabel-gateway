/*
 * Panneau « Catalogue MCP ».
 *
 * Chaque bouton de ce panneau déclenche un VRAI échange MCP : le serveur Web
 * lance `python -m mcp_server.server` en sous-processus avec le profil choisi
 * et parle le protocole sur stdio. Rien n'est simulé côté navigateur — c'est
 * pour cela qu'un appel prend environ une seconde.
 *
 * Fichier séparé de app.js à dessein : le panneau du chantier 2 ne doit pas
 * dépendre de celui-ci, ni casser si celui-ci change.
 */

const mcpProfile = document.querySelector("#mcp-profile");
const mcpCatalogueButton = document.querySelector("#mcp-catalogue-button");
const mcpCatalogue = document.querySelector("#mcp-catalogue");
const mcpTool = document.querySelector("#mcp-tool");
const mcpArgument = document.querySelector("#mcp-argument");
const mcpArgumentLabel = document.querySelector("#mcp-argument-label");
const mcpCallButton = document.querySelector("#mcp-call-button");
const mcpCallResult = document.querySelector("#mcp-call-result");
const mcpJournal = document.querySelector("#mcp-journal");
const mcpJournalButton = document.querySelector("#mcp-journal-button");

/* Nom de l'argument principal de chaque tool, et un exemple qui existe
 * réellement dans les données chargées. Une démonstration qui renvoie zéro
 * ligne ne prouve rien. */
const ARGUMENT_PAR_TOOL = {
  answer_question: ["question", "Quel est le délai d’un échange standard ?"],
  search_docs: ["query", "retour d’un produit défectueux sous garantie"],
  get_document: ["doc_id", ""],
  list_sources: [null, ""],
  ask_database: ["question", "combien de commandes en avril 2026 ?"],
  get_schema: [null, ""],
  check_stock: ["reference", "REF-8842"],
  order_status: ["order_id", "CMD-2025-0005"],
};

function noeud(balise, classe, texte) {
  const n = document.createElement(balise);
  if (classe) n.className = classe;
  if (texte !== undefined) n.textContent = texte;
  return n;
}

function premiereLigne(description) {
  return (description || "").split("\n")[0];
}

async function poster(url, corps) {
  const reponse = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps),
  });
  return reponse.json();
}

function occuper(bouton, occupe, libelle) {
  bouton.disabled = occupe;
  bouton.textContent = occupe ? "Le serveur MCP démarre…" : libelle;
}

/* ---------------------------------------------------------------- catalogue */

function afficherCatalogue(payload) {
  mcpCatalogue.replaceChildren();

  const titre = noeud(
    "p",
    "mcp-titre",
    `tools/list — ${payload.nombre} tools sur ${payload.catalogue_officiel} annoncés au profil ${payload.profil}`,
  );
  mcpCatalogue.append(titre);

  const liste = noeud("ul", "mcp-liste");
  payload.tools.forEach((outil) => {
    const item = noeud("li", "mcp-outil mcp-autorise");
    item.append(noeud("span", "mcp-marque", "✓"));
    const bloc = noeud("div");
    bloc.append(noeud("strong", "", outil.nom));
    bloc.append(noeud("small", "", premiereLigne(outil.description)));
    item.append(bloc);
    liste.append(item);
  });
  payload.absents.forEach((outil) => {
    const item = noeud("li", "mcp-outil mcp-refuse");
    item.append(noeud("span", "mcp-marque", "✕"));
    const bloc = noeud("div");
    bloc.append(noeud("strong", "", outil.nom));
    bloc.append(
      noeud("small", "", "absent du catalogue de ce profil — la matrice le refuse"),
    );
    item.append(bloc);
    liste.append(item);
  });
  mcpCatalogue.append(liste);
}

async function chargerCatalogue() {
  occuper(mcpCatalogueButton, true);
  mcpCatalogue.replaceChildren(noeud("p", "mcp-attente", "tools/list en cours…"));
  try {
    const enveloppe = await poster("/api/mcp/catalogue", { profile: mcpProfile.value });
    if (enveloppe.status !== "ok") {
      mcpCatalogue.replaceChildren(noeud("p", "mcp-erreur", enveloppe.message || "Échec."));
      return;
    }
    afficherCatalogue(enveloppe.payload);
  } catch (erreur) {
    mcpCatalogue.replaceChildren(noeud("p", "mcp-erreur", `Serveur injoignable : ${erreur}`));
  } finally {
    occuper(mcpCatalogueButton, false, "Voir le catalogue");
  }
}

/* --------------------------------------------------------------------- appel */

function majArgument() {
  const [nom, exemple] = ARGUMENT_PAR_TOOL[mcpTool.value] || [null, ""];
  const sansArgument = nom === null;
  mcpArgument.hidden = sansArgument;
  mcpArgumentLabel.hidden = sansArgument;
  if (!sansArgument) {
    mcpArgumentLabel.textContent = nom;
    mcpArgument.value = exemple;
    mcpArgument.placeholder = exemple;
  }
}

function afficherAppel(enveloppe) {
  mcpCallResult.replaceChildren();

  const code = enveloppe.payload?.error_code;
  const statut = enveloppe.status;
  const classe =
    statut === "ok" ? "mcp-verdict mcp-ok" : "mcp-verdict mcp-ko";

  const ligne = noeud("p", classe);
  ligne.append(noeud("strong", "", statut));
  if (code) ligne.append(noeud("span", "mcp-code", code));
  ligne.append(noeud("span", "mcp-duree", `${enveloppe.duree_ms} ms`));
  if (enveloppe.payload?.annonce_au_catalogue === false) {
    ligne.append(
      noeud("span", "mcp-hors", "appelé alors qu’il est HORS catalogue — refusé quand même"),
    );
  }
  mcpCallResult.append(ligne);

  if (enveloppe.message) {
    mcpCallResult.append(noeud("p", "mcp-message", enveloppe.message));
  }

  const utile = { ...(enveloppe.payload || {}) };
  delete utile.annonce_au_catalogue;
  if (Object.keys(utile).length > 0) {
    const pre = noeud("pre", "mcp-json", JSON.stringify(utile, null, 2).slice(0, 4000));
    mcpCallResult.append(pre);
  }
}

async function appelerTool() {
  const [nom] = ARGUMENT_PAR_TOOL[mcpTool.value] || [null];
  const arguments_ = nom ? { [nom]: mcpArgument.value } : {};

  occuper(mcpCallButton, true);
  mcpCallResult.replaceChildren(noeud("p", "mcp-attente", "tools/call en cours…"));
  try {
    const enveloppe = await poster("/api/mcp/call", {
      profile: mcpProfile.value,
      tool: mcpTool.value,
      arguments: arguments_,
    });
    afficherAppel(enveloppe);
    await chargerJournal();
  } catch (erreur) {
    mcpCallResult.replaceChildren(noeud("p", "mcp-erreur", `Serveur injoignable : ${erreur}`));
  } finally {
    occuper(mcpCallButton, false, "Appeler · tools/call");
  }
}

/* ------------------------------------------------------------------- journal */

async function chargerJournal() {
  try {
    const reponse = await fetch("/api/mcp/journal?limit=10");
    const entrees = (await reponse.json()).payload.entrees || [];
    mcpJournal.replaceChildren();

    if (entrees.length === 0) {
      mcpJournal.append(noeud("p", "mcp-attente", "Journal vide."));
      return;
    }
    entrees.reverse().forEach((entree) => {
      const ligne = noeud("li", "mcp-ligne");
      ligne.append(noeud("span", `mcp-canal mcp-canal-${entree.channel}`, entree.channel));
      ligne.append(noeud("span", "mcp-profil", entree.profile));
      ligne.append(noeud("span", "mcp-tool", entree.tool));
      ligne.append(
        noeud("span", entree.status === "ok" ? "mcp-statut-ok" : "mcp-statut-ko", entree.status),
      );
      if (entree.error_code) ligne.append(noeud("span", "mcp-code", entree.error_code));
      if (entree.duration_ms !== null && entree.duration_ms !== undefined) {
        ligne.append(noeud("span", "mcp-duree", `${entree.duration_ms} ms`));
      }
      mcpJournal.append(ligne);
    });
  } catch (erreur) {
    mcpJournal.replaceChildren(noeud("p", "mcp-erreur", `Journal illisible : ${erreur}`));
  }
}

mcpCatalogueButton.addEventListener("click", chargerCatalogue);
mcpCallButton.addEventListener("click", appelerTool);
mcpJournalButton.addEventListener("click", chargerJournal);
mcpTool.addEventListener("change", majArgument);
mcpProfile.addEventListener("change", chargerCatalogue);

majArgument();
chargerCatalogue();
chargerJournal();
