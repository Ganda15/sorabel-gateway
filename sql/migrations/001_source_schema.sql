CREATE SCHEMA IF NOT EXISTS sorabel_source;

CREATE TABLE IF NOT EXISTS sorabel_source.produits (
    ref text PRIMARY KEY,
    nom text NOT NULL,
    categorie text NOT NULL,
    fabricant text NOT NULL,
    unite text NOT NULL,
    prix_vente_ht numeric(12, 2) NOT NULL,
    prix_achat_ht numeric(12, 2) NOT NULL,
    marge_pct numeric(7, 2) NOT NULL,
    actif boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS sorabel_source.clients (
    id text PRIMARY KEY,
    raison_sociale text NOT NULL,
    segment text NOT NULL,
    ville text NOT NULL,
    email text NOT NULL
);

CREATE TABLE IF NOT EXISTS sorabel_source.commandes (
    id text PRIMARY KEY,
    client_id text NOT NULL REFERENCES sorabel_source.clients(id),
    date_commande date NOT NULL,
    statut text NOT NULL,
    montant_ht numeric(14, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS sorabel_source.stocks (
    id bigint PRIMARY KEY,
    ref text NOT NULL REFERENCES sorabel_source.produits(ref),
    entrepot text NOT NULL,
    quantite integer NOT NULL,
    seuil_reappro integer NOT NULL
);

CREATE TABLE IF NOT EXISTS sorabel_source.ventes (
    id bigint PRIMARY KEY,
    commande_id text NOT NULL REFERENCES sorabel_source.commandes(id),
    ref text NOT NULL REFERENCES sorabel_source.produits(ref),
    quantite integer NOT NULL,
    prix_unitaire_ht numeric(12, 2) NOT NULL,
    remise_pct numeric(7, 2) NOT NULL,
    marge_ht numeric(14, 2) NOT NULL
);

COMMENT ON SCHEMA sorabel_source IS
    'Private reconciliation layer imported from the received SQLite source.';

