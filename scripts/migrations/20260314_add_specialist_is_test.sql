-- US-AD-10: explicit test specialist marking.
-- Online migration strategy:
-- 1) Add nullable column first (metadata-only).
-- 2) Backfill NULL -> FALSE in batches handled by a single statement for existing data volume.
-- 3) Set DEFAULT FALSE and NOT NULL.
-- 4) Add index concurrently.
-- 5) Add CHECK constraint as NOT VALID, then VALIDATE.

ALTER TABLE specialist
ADD COLUMN IF NOT EXISTS is_test BOOLEAN;

UPDATE specialist
SET is_test = FALSE
WHERE is_test IS NULL;

ALTER TABLE specialist
ALTER COLUMN is_test SET DEFAULT FALSE;

ALTER TABLE specialist
ALTER COLUMN is_test SET NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_specialist_is_test
ON specialist (is_test);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'specialist_test_system_exclusive'
    ) THEN
        ALTER TABLE specialist
        ADD CONSTRAINT specialist_test_system_exclusive
        CHECK NOT (is_system AND is_test) NOT VALID;
    END IF;
END
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'specialist_test_system_exclusive'
          AND convalidated = FALSE
    ) THEN
        ALTER TABLE specialist
        VALIDATE CONSTRAINT specialist_test_system_exclusive;
    END IF;
END
$$;

-- Verification queries:
-- 1) Should use idx_specialist_is_test
--    EXPLAIN SELECT COUNT(*) FROM specialist WHERE is_test = TRUE;
-- 2) Existing specialists remain non-test
--    SELECT COUNT(*) FROM specialist WHERE is_test IS NULL;  -- expect 0
--    SELECT COUNT(*) FROM specialist WHERE is_test = TRUE;
--    SELECT COUNT(*) FROM specialist WHERE is_test = FALSE;
