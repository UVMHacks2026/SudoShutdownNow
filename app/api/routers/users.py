from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, verify_auth
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    _: None = Depends(verify_auth)
):
    """Create a new user."""
    # Check if user with same id already exists
    existing_user_id = db.query(User).filter(User.id == user.id).first()
    if existing_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this ID already exists"
        )

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    db_user = User(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/email/{email}", response_model=UserResponse)
def get_user_by_email(
    email: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_auth)
):
    """Get a user by email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_auth)
):
    """Get a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/{user_id}/exists")
def user_exists(
    user_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_auth)
):
    """Return whether a user exists by ID."""
    exists = db.query(User).filter(User.id == user_id).first() is not None
    return {"exists": exists}


@router.post("/{user_id}/loggedin")
def user_logged_in(
    user_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_auth)
):
    """Compatibility endpoint used by frontend login flow."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"ok": True}


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: None = Depends(verify_auth)
):
    """List all users."""
    users = db.query(User).all()
    return users


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_auth)
):
    """Delete a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    db.delete(user)
    db.commit()
    return None
