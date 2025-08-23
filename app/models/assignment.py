from sqlalchemy import Column, Date, Integer, Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum as PyEnum
from models.base_model import Base, BaseModel

class AssignmentStatus(PyEnum):
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Assignment(BaseModel):
    __tablename__ = 'assignments'
    
    date = Column(Date, nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey('orders.id'), nullable=False, index=True)
    delivery_time_minutes = Column(Integer, nullable=False)
    travel_distance_km = Column(Float, nullable=False)
    status = Column(Enum(AssignmentStatus), nullable=False, default=AssignmentStatus.ASSIGNED, index=True)