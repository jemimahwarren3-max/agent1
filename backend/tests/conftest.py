import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import Base


def _can_connect(url: str) -> bool:
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def test_database_url():
    """Prefers a real, already-running Postgres at settings.DATABASE_URL (e.g.
    `docker compose up postgres`). Falls back to a disposable embedded Postgres
    (via the `pgserver` dev dependency) so these tests run for real even without
    Docker. Yields None if neither is available, and dependent tests skip."""

    if _can_connect(settings.DATABASE_URL):
        yield settings.DATABASE_URL
        return

    try:
        import pgserver
    except ImportError:
        yield None
        return

    import tempfile

    with tempfile.TemporaryDirectory(prefix="haki_test_pg_") as tmp_dir:
        server = pgserver.get_server(tmp_dir)
        try:
            yield server.get_uri()
        finally:
            server.cleanup()


@pytest.fixture()
def db_session(test_database_url):
    if test_database_url is None:
        pytest.skip(
            "No reachable Postgres and `pgserver` isn't installed — "
            "run `pip install -r requirements-dev.txt`, or start Postgres yourself."
        )

    engine = create_engine(test_database_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
