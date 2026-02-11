-- Enforce strict NULL/NULL model for weekly availability intervals.
ALTER TABLE weekly_availability
    ADD CONSTRAINT ck_weekly_availability_interval_1_pair
    CHECK (
        (interval_1_start IS NULL AND interval_1_end IS NULL)
        OR (interval_1_start IS NOT NULL AND interval_1_end IS NOT NULL AND interval_1_start < interval_1_end)
    );

ALTER TABLE weekly_availability
    ADD CONSTRAINT ck_weekly_availability_interval_2_pair
    CHECK (
        (interval_2_start IS NULL AND interval_2_end IS NULL)
        OR (interval_2_start IS NOT NULL AND interval_2_end IS NOT NULL AND interval_2_start < interval_2_end)
    );

ALTER TABLE weekly_availability
    ADD CONSTRAINT ck_weekly_availability_interval_3_pair
    CHECK (
        (interval_3_start IS NULL AND interval_3_end IS NULL)
        OR (interval_3_start IS NOT NULL AND interval_3_end IS NOT NULL AND interval_3_start < interval_3_end)
    );
