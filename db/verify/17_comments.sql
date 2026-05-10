-- Verify churn_prediction:17_comments on pg

DO $$
DECLARE
    missing TEXT := '';
BEGIN
    -- Verifica COMMENT ON TABLE
    SELECT string_agg(relname, ', ')
      INTO missing
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0
     WHERE n.nspname = 'churn'
       AND c.relkind = 'r'
       AND d.description IS NULL;

    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'Tabelas sem COMMENT ON TABLE: %', missing;
    END IF;
END $$;
