from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
