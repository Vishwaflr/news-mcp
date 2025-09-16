from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG",
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created")

def get_session():
    with Session(engine) as session:
        yield session