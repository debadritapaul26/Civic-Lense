-- Run once against an existing civic.db database.
-- SQLite does not support ADD COLUMN IF NOT EXISTS, so do not rerun this
-- statement after the column has already been added.
ALTER TABLE complaints
ADD COLUMN evidence_uploaded_at DATETIME NULL;
