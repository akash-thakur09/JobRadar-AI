"""Integration test verifying Alembic database migration upgrade, reversibility, and head consistency."""

import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config

from app.core.config import get_settings


@pytest.mark.integration
def test_alembic_clean_migration_and_reversibility() -> None:
    """Verify that a brand new database can be cleanly upgraded to head and downgraded to base."""
    settings = get_settings()
    # Direct psycopg.connect expects postgresql:// without +psycopg dialect indicator
    base_sync = settings.database_sync_url.replace("postgresql+psycopg://", "postgresql://")
    admin_url = base_sync.rsplit("/", 1)[0] + "/postgres"
    test_db_name = f"test_migration_suite_{uuid.uuid4().hex[:8]}"

    try:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE {test_db_name};")

        test_db_url = f"{base_sync.rsplit('/', 1)[0]}/{test_db_name}"
        async_test_db_url = f"{settings.database_url.rsplit('/', 1)[0]}/{test_db_name}"

        cfg = Config(Path(__file__).parents[2] / "alembic.ini")
        cfg.set_main_option("sqlalchemy.url", async_test_db_url)

        # 1. Upgrade from clean database, including an orphan from the previous release.
        command.upgrade(cfg, "20261105_0010")
        with psycopg.connect(test_db_url) as conn:
            source = conn.execute(
                """INSERT INTO job_sources (name, source_type, base_url)
                   VALUES ('Legacy QA', 'GREENHOUSE', 'https://example.test') RETURNING id"""
            ).fetchone()
            assert source is not None
            conn.execute("INSERT INTO discovery_runs (job_source_id) VALUES (%s)", (source[0],))
        command.upgrade(cfg, "head")

        # 2. Inspect tables in newly upgraded database
        with psycopg.connect(test_db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name;
                """)
                tables = [r[0] for r in cur.fetchall()]
                assert "alembic_version" in tables
                assert "candidate_profiles" in tables
                assert "jobs" in tables
                assert "job_matches" in tables
                assert "tailored_resumes" in tables
                assert "notification_deliveries" in tables
                assert "pipeline_runs" in tables

                cur.execute("SELECT version_num FROM alembic_version;")
                head = cur.fetchone()[0]
                assert head == "20261123_0011"
                cur.execute("SELECT status, completed_at, error_summary FROM discovery_runs")
                run = cur.fetchone()
                assert run is not None and run[0] == "FAILED" and run[1] is not None
                assert "Start a new discovery run" in run[2]

        # 3. Downgrade back to base
        command.downgrade(cfg, "base")

        with psycopg.connect(test_db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name != 'alembic_version';
                """)
                remaining = cur.fetchall()
                assert len(remaining) == 0

    finally:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS {test_db_name};")
