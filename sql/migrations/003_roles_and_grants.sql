DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sorabel_support') THEN
        CREATE ROLE sorabel_support NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sorabel_commercial') THEN
        CREATE ROLE sorabel_commercial NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sorabel_schema_reader') THEN
        CREATE ROLE sorabel_schema_reader NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sorabel_support_login') THEN
        CREATE ROLE sorabel_support_login LOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sorabel_commercial_login') THEN
        CREATE ROLE sorabel_commercial_login LOGIN;
    END IF;
END
$$;

GRANT sorabel_support TO sorabel_support_login;
GRANT sorabel_commercial TO sorabel_commercial_login;

ALTER ROLE sorabel_support_login SET default_transaction_read_only = on;
ALTER ROLE sorabel_commercial_login SET default_transaction_read_only = on;

REVOKE ALL ON SCHEMA sorabel_source FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA sorabel_source FROM PUBLIC;
REVOKE ALL ON SCHEMA sorabel_source
FROM sorabel_support, sorabel_commercial, sorabel_schema_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA sorabel_source
FROM sorabel_support, sorabel_commercial, sorabel_schema_reader;

REVOKE ALL ON SCHEMA sorabel_semantic FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA sorabel_semantic FROM PUBLIC;

GRANT USAGE ON SCHEMA sorabel_semantic TO sorabel_support, sorabel_commercial;

GRANT SELECT ON
    sorabel_semantic.produits_support,
    sorabel_semantic.stocks_support,
    sorabel_semantic.clients_support,
    sorabel_semantic.commandes_support
TO sorabel_support;

GRANT SELECT ON
    sorabel_semantic.produits_commercial,
    sorabel_semantic.stocks_commercial,
    sorabel_semantic.clients_commercial,
    sorabel_semantic.commandes_commercial,
    sorabel_semantic.ventes_commercial
TO sorabel_commercial;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA sorabel_semantic
FROM sorabel_support, sorabel_commercial, sorabel_schema_reader;
