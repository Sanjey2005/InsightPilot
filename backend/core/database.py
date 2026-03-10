from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings

# connect_args is required for SQLite to allow multi-threaded access
engine = create_engine(
    settings.database_url,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,          # wait up to 30s for a lock before raising
    },
)

# Enable WAL journal mode: allows concurrent readers + 1 writer,
# which prevents "database is locked" hangs when the pipeline background
# thread and the upload handler both need SQLite at the same time.
@event.listens_for(engine, "connect")
def _set_wal_mode(dbapi_conn, _):
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA busy_timeout=30000")   # 30s busy timeout

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
