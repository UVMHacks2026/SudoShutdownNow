from pydantic import BaseModel, EmailStr

class FrameRequest(BaseModel):
    image: str


class UserCreate(BaseModel):
    id: str
    email: EmailStr


class UserResponse(BaseModel):
    id: str
    email: str

    class Config:
        from_attributes = True

class EmployeeCreate(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    image_base64: str  # For facial registration

class EmployeeResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    image_id: str | None

    class Config:
        from_attributes = True
