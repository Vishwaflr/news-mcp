"""Centralized database session management."""

import logging
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, TimeoutError as SQLTimeoutError
from app.config import settings

logger = logging.getLogger(__name__)

class DatabaseSession:
    """Centralized database session factory with retry logic."""

    def __init__(self, database_url: str, pool_size: int = 5, max_overflow: int = 10):
        self.engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Validate connections
            pool_recycle=3600,   # Recycle connections hourly
            echo=False  # Set to True for SQL debugging
        )
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for transactional database sessions.
        Use for write operations.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
            logger.debug("Database transaction committed")
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction rolled back: {e}")
            raise
        finally:
            session.close()

    @contextmanager
    def read_session(self) -> Generator[Session, None, None]:
        """
        Context manager for read-only database sessions.
        Use for read operations (no commit).
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            logger.error(f"Database read error: {e}")
            raise
        finally:
            session.close()

    def execute_query(self, query: str, params: Optional[dict] = None) -> list:
        """
        Execute a read-only query with proper session handling.
        """
        with self.read_session() as session:
            try:
                result = session.execute(text(query), params or {})
                return result.fetchall()
            except SQLTimeoutError:
                logger.error(f"Query timeout: {query[:100]}...")
                raise
            except SQLAlchemyError as e:
                logger.error(f"Query error: {e}")
                raise

    def execute_insert(self, query: str, params: Optional[dict] = None):
        """
        Execute an insert/update query with transaction.
        """
        with self.session() as session:
            try:
                result = session.execute(text(query), params or {})
                return result.fetchone()
            except SQLAlchemyError as e:
                logger.error(f"Insert/Update error: {e}")
                raise

    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.read_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database session instance
db_session = DatabaseSession(settings.database_url)


def get_db_session() -> DatabaseSession:
    """Dependency injection for repositories."""
    return db_session


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for direct session access (legacy)."""
    with db_session.session() as session:
        yield session


def get_read_db() -> Generator[Session, None, None]:
    """FastAPI dependency for read-only session access."""
    with db_session.read_session() as session:
        yield session