from pydantic import BaseModel, EmailStr
from uuid import UUID


class UserCreate(BaseModel):
    email: EmailStr
    is_admin: bool = False


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_admin: bool

    class Config:
        from_attributes = True
