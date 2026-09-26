"""SQLAlchemy engine, session factory, and FastAPI database dependency."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

try:
    from .config import DATABASE_URL
except ImportError:  # Supports `uvicorn main:app` from the backend directory.
    from config import DATABASE_URL


sqlite_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=sqlite_connect_args,
    future=True,
)
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
)


def _sqlite_table_columns(connection: object, table_name: str) -> dict[str, tuple]:
    """Return SQLite column metadata keyed by column name."""

    result = connection.exec_driver_sql(f"PRAGMA table_info({table_name})")  # type: ignore[attr-defined]
    return {row[1]: row for row in result.fetchall()}


def run_sqlite_migrations() -> None:
    """Apply idempotent migrations for databases created by older builds.

    ``Base.metadata.create_all`` only creates missing tables; it does not alter
    existing SQLite columns. Older builds required a district on every
    complaint and stored proposal district IDs, so those tables are rebuilt
    before the current ORM models accept map-only submissions. Legacy
    complaints without coordinates are retained, while new submissions are
    validated by the complaints endpoint.
    """

    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")

        complaint_columns = _sqlite_table_columns(connection, "complaints")
        district_metadata = complaint_columns.get("district_id")
        if complaint_columns and (
            district_metadata is not None
            and district_metadata[3] == 1
            or "latitude" not in complaint_columns
            or "longitude" not in complaint_columns
            or "formatted_address" not in complaint_columns
        ):
            connection.exec_driver_sql(
                """
                CREATE TABLE complaints_migrated (
                    id INTEGER PRIMARY KEY,
                    raw_text TEXT NOT NULL,
                    language_detected VARCHAR(50) NOT NULL,
                    problem TEXT,
                    category VARCHAR(100) NOT NULL,
                    urgency_score FLOAT NOT NULL,
                    location_hint VARCHAR(255),
                    latitude FLOAT,
                    longitude FLOAT,
                    formatted_address VARCHAR(500),
                    district_id INTEGER,
                    evidence_file_path VARCHAR(500),
                    evidence_uploaded_at DATETIME,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (district_id) REFERENCES districts(id)
                )
                """
            )

            def column_or_null(name: str) -> str:
                return name if name in complaint_columns else "NULL"

            connection.exec_driver_sql(
                f"""
                INSERT INTO complaints_migrated (
                    id, raw_text, language_detected, problem, category,
                    urgency_score, location_hint, latitude, longitude,
                    formatted_address, district_id, evidence_file_path,
                    evidence_uploaded_at, created_at
                )
                SELECT
                    id, raw_text, language_detected, problem, category,
                    urgency_score, location_hint,
                    {column_or_null('latitude')},
                    {column_or_null('longitude')},
                    {column_or_null('formatted_address')},
                    {column_or_null('district_id')},
                    {column_or_null('evidence_file_path')},
                    {column_or_null('evidence_uploaded_at')},
                    {column_or_null('created_at')}
                FROM complaints
                """
            )
            connection.exec_driver_sql("DROP TABLE complaints")
            connection.exec_driver_sql(
                "ALTER TABLE complaints_migrated RENAME TO complaints"
            )
            connection.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_complaints_district_id "
                "ON complaints (district_id)"
            )

        proposal_columns = _sqlite_table_columns(connection, "proposals")
        if proposal_columns and "cluster_id" not in proposal_columns:
            connection.exec_driver_sql(
                """
                CREATE TABLE proposals_migrated (
                    id INTEGER PRIMARY KEY,
                    cluster_id VARCHAR(128) NOT NULL,
                    project_name VARCHAR(255) NOT NULL,
                    requested_amount FLOAT NOT NULL
                )
                """
            )
            connection.exec_driver_sql(
                """
                INSERT INTO proposals_migrated (
                    id, cluster_id, project_name, requested_amount
                )
                SELECT
                    id,
                    'legacy-district-' || CAST(district_id AS TEXT),
                    project_name,
                    requested_amount
                FROM proposals
                """
            )
            connection.exec_driver_sql("DROP TABLE proposals")
            connection.exec_driver_sql(
                "ALTER TABLE proposals_migrated RENAME TO proposals"
            )
            connection.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_proposals_cluster_id "
                "ON proposals (cluster_id)"
            )

        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for a request and close it afterward."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
