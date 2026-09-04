CREATE SCHEMA IF NOT EXISTS sorabel_semantic;

CREATE OR REPLACE VIEW sorabel_semantic.produits_support
WITH (security_barrier = true)
AS
SELECT ref, nom, categorie, fabricant, unite, prix_vente_ht, actif
FROM sorabel_source.produits;

CREATE OR REPLACE VIEW sorabel_semantic.stocks_support
WITH (security_barrier = true)
AS
SELECT id, ref, entrepot, quantite, seuil_reappro
FROM sorabel_source.stocks;

CREATE OR REPLACE VIEW sorabel_semantic.clients_support
WITH (security_barrier = true)
AS
SELECT id, raison_sociale, segment, ville, email
FROM sorabel_source.clients;

CREATE OR REPLACE VIEW sorabel_semantic.commandes_support
WITH (security_barrier = true)
AS
SELECT id, client_id, date_commande, statut, montant_ht
FROM sorabel_source.commandes;

CREATE OR REPLACE VIEW sorabel_semantic.produits_commercial
WITH (security_barrier = true)
AS
SELECT
    ref,
    nom,
    categorie,
    fabricant,
    unite,
    prix_vente_ht,
    prix_achat_ht,
    marge_pct,
    actif
FROM sorabel_source.produits;

CREATE OR REPLACE VIEW sorabel_semantic.stocks_commercial
WITH (security_barrier = true)
AS
SELECT id, ref, entrepot, quantite, seuil_reappro
FROM sorabel_source.stocks;

CREATE OR REPLACE VIEW sorabel_semantic.clients_commercial
WITH (security_barrier = true)
AS
SELECT id, raison_sociale, segment, ville, email
FROM sorabel_source.clients;

CREATE OR REPLACE VIEW sorabel_semantic.commandes_commercial
WITH (security_barrier = true)
AS
SELECT id, client_id, date_commande, statut, montant_ht
FROM sorabel_source.commandes;

CREATE OR REPLACE VIEW sorabel_semantic.ventes_commercial
WITH (security_barrier = true)
AS
SELECT id, commande_id, ref, quantite, prix_unitaire_ht, remise_pct, marge_ht
FROM sorabel_source.ventes;

COMMENT ON SCHEMA sorabel_semantic IS
    'Authorized business-facing views queried by the governed Text-to-SQL service.';

