from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    id: str
    email: EmailStr


class UserResponse(BaseModel):
    id: str
    email: str

    class Config:
        from_attributes = True
