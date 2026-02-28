from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from uuid import UUID


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    """Get user by UUID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def get_all_users(db: Session) -> list[User]:
    """Get all users."""
    return db.query(User).all()


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user."""
    db_user = User(email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: UUID) -> bool:
    """Delete a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True
