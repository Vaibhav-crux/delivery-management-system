from sqlalchemy import Column, String, Boolean, Enum
from enum import Enum as PyEnum
from models.base_model import Base, BaseModel

class UserStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"

class User(BaseModel):
    __tablename__ = 'users'
    
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.ACTIVE, index=True)