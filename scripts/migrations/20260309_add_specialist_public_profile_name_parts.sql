ALTER TABLE specialist_public_profile
    ADD COLUMN IF NOT EXISTS first_name TEXT,
    ADD COLUMN IF NOT EXISTS middle_name TEXT,
    ADD COLUMN IF NOT EXISTS last_name TEXT;

WITH parsed AS (
    SELECT
        id,
        regexp_split_to_array(regexp_replace(btrim(display_name), '\\s+', ' ', 'g'), ' ') AS tokens
    FROM specialist_public_profile
    WHERE first_name IS NULL
      AND middle_name IS NULL
      AND last_name IS NULL
      AND COALESCE(btrim(display_name), '') <> ''
)
UPDATE specialist_public_profile AS profile
SET
    first_name = CASE
        WHEN cardinality(parsed.tokens) >= 1 THEN parsed.tokens[1]
        ELSE first_name
    END,
    middle_name = CASE
        WHEN cardinality(parsed.tokens) >= 3 THEN array_to_string(parsed.tokens[2:cardinality(parsed.tokens)-1], ' ')
        ELSE middle_name
    END,
    last_name = CASE
        WHEN cardinality(parsed.tokens) = 2 THEN parsed.tokens[2]
        WHEN cardinality(parsed.tokens) >= 3 THEN parsed.tokens[cardinality(parsed.tokens)]
        ELSE last_name
    END
FROM parsed
WHERE profile.id = parsed.id;
