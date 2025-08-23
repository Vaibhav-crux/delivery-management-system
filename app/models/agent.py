from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum as PyEnum
from models.base_model import Base, BaseModel

class AgentStatus(PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHECKED_IN = "checked_in"

class Agent(BaseModel):
    __tablename__ = 'agents'
    
    name = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey('warehouses.id'), nullable=False, index=True)
    daily_check_in = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(AgentStatus), nullable=False, default=AgentStatus.INACTIVE, index=True)