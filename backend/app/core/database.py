"""Shared SQLAlchemy sessions for local SQLite and production PostgreSQL."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.settings import settings


def build_engine(url: str):
    options = {"pool_pre_ping": True, "echo": settings.DATABASE_ECHO}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if url in {"sqlite://", "sqlite:///:memory:"}:
            options["poolclass"] = StaticPool
    else:
        options.update(pool_recycle=3600)
    return create_engine(url, **options)


class Base(DeclarativeBase):
    pass


engine = build_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session


def init_db():
    import app.db_models  # noqa: F401

    Base.metadata.create_all(engine)


def check_db_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
