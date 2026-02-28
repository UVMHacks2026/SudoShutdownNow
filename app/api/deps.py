from collections.abc import Generator
from sqlalchemy.orm import Session
from fastapi import Header, HTTPException, status, Depends
from app.db import SessionLocal
from app.core.config import get_settings


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_auth(Authorization: str = Header(...)) -> None:
    settings = get_settings()
    if Authorization != settings.MASTER_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
