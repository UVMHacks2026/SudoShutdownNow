from sqlalchemy import Column, String
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
