from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

engine = create_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG"
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created")

def get_session():
    with Session(engine) as session:
        yield session