from sqlalchemy import Column, String
from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    image_id = Column(String, nullable=True)
    face_embedding = Column(String, nullable=True)  # Store as encrypted base64/pickle

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.first_name} {self.last_name})>"
