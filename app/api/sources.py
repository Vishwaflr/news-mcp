from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models import Source
# from app.schemas import SourceCreate, SourceResponse
from typing import Any
SourceCreate = Any
SourceResponse = Any
CategoryCreate = Any
CategoryResponse = Any

router = APIRouter(prefix="/sources", tags=["sources"])

@router.get("/", response_model=List[SourceResponse])
def list_sources(session: Session = Depends(get_session)):
    sources = session.exec(select(Source)).all()
    return sources

@router.get("/{source_id}", response_model=SourceResponse)
def get_source(source_id: int, session: Session = Depends(get_session)):
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source

@router.post("/", response_model=SourceResponse)
def create_source(source: SourceCreate, session: Session = Depends(get_session)):
    db_source = Source(**source.model_dump())
    session.add(db_source)
    session.commit()
    session.refresh(db_source)
    return db_source

@router.delete("/{source_id}")
def delete_source(source_id: int, session: Session = Depends(get_session)):
    source = session.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    session.delete(source)
    session.commit()
    return {"message": "Source deleted successfully"}