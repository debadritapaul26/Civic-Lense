-- Run once against an existing civic.db database.
-- SQLite does not support ADD COLUMN IF NOT EXISTS, so do not rerun these
-- statements after the columns have already been added.
ALTER TABLE complaints
ADD COLUMN latitude FLOAT NULL;

ALTER TABLE complaints
ADD COLUMN longitude FLOAT NULL;

ALTER TABLE complaints
ADD COLUMN formatted_address VARCHAR(500) NULL;
