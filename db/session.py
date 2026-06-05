"""SQLAlchemy engine and session management."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base

_engine = None
_SessionLocal = None

DEFAULT_SQLITE = "sqlite:///./data/aureon.db"


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_SQLITE)
    # Railway/Heroku use postgres:// — SQLAlchemy 2 needs postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = get_database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        pool_kwargs = {}
        if url.startswith("postgresql"):
            pool_kwargs = {"pool_size": 5, "max_overflow": 10, "pool_recycle": 1800}
        _engine = create_engine(
            url, pool_pre_ping=True, connect_args=connect_args, **pool_kwargs
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def init_db() -> None:
    from pathlib import Path

    from sqlalchemy import inspect, text

    url = get_database_url()
    if url.startswith("sqlite"):
        Path("data").mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _apply_additive_migrations(engine, inspect(engine))


def _apply_additive_migrations(engine, insp) -> None:
    """Add micro-subdomain columns and rebuild micro_agents unique scope if needed."""
    from sqlalchemy import text

    tables = set(insp.get_table_names())
    alters: list[str] = []
    if "micro_agents" in tables:
        cols = {c["name"] for c in insp.get_columns("micro_agents")}
        if "micro_subdomain_id" not in cols:
            alters.append("ALTER TABLE micro_agents ADD COLUMN micro_subdomain_id INTEGER")
    if "documents" in tables:
        cols = {c["name"] for c in insp.get_columns("documents")}
        if "micro_subdomain_id" not in cols:
            alters.append("ALTER TABLE documents ADD COLUMN micro_subdomain_id INTEGER")
    if alters:
        with engine.begin() as conn:
            for stmt in alters:
                conn.execute(text(stmt))

    if "micro_agents" in tables:
        _rebuild_micro_agents_unique_scope(engine, insp)


def _rebuild_micro_agents_unique_scope(engine, insp) -> None:
    """SQLite/old DBs used UNIQUE(region, domain_id, subdomain_id) — rebuild for micro scope."""
    from sqlalchemy import text

    try:
        uniques = insp.get_unique_constraints("micro_agents")
    except NotImplementedError:
        return
    needs_rebuild = True
    for uc in uniques:
        if uc.get("name") == "uq_agent_region_scope":
            cols = set(uc.get("column_names") or [])
            if "micro_subdomain_id" in cols:
                needs_rebuild = False
            break
    if not needs_rebuild:
        return

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM agent_runs"))
        conn.execute(text("DELETE FROM micro_agents"))
        conn.execute(
            text(
                """
                CREATE TABLE micro_agents_new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    region VARCHAR(32) NOT NULL,
                    domain_id INTEGER NOT NULL,
                    subdomain_id INTEGER,
                    micro_subdomain_id INTEGER,
                    status VARCHAR(32) NOT NULL,
                    config JSON,
                    last_run_at DATETIME,
                    FOREIGN KEY(domain_id) REFERENCES knowledge_domains (id),
                    FOREIGN KEY(subdomain_id) REFERENCES knowledge_subdomains (id),
                    FOREIGN KEY(micro_subdomain_id) REFERENCES knowledge_micro_subdomains (id),
                    CONSTRAINT uq_agent_region_scope UNIQUE (region, domain_id, subdomain_id, micro_subdomain_id)
                )
                """
            )
        )
        conn.execute(text("DROP TABLE micro_agents"))
        conn.execute(text("ALTER TABLE micro_agents_new RENAME TO micro_agents"))
        conn.execute(text("CREATE INDEX ix_micro_agents_region ON micro_agents (region)"))
        conn.execute(text("CREATE INDEX ix_micro_agents_domain_id ON micro_agents (domain_id)"))
        conn.execute(text("CREATE INDEX ix_micro_agents_subdomain_id ON micro_agents (subdomain_id)"))
        conn.execute(
            text("CREATE INDEX ix_micro_agents_micro_subdomain_id ON micro_agents (micro_subdomain_id)")
        )


@contextmanager
def get_session() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        get_engine()
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_available() -> bool:
    return bool(os.environ.get("DATABASE_URL")) or True  # sqlite always available locally
