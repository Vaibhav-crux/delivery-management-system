from sqlalchemy import Column, String, Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum as PyEnum
from models.base_model import Base, BaseModel

class OrderStatus(PyEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    DELIVERED = "delivered"
    DEFERRED = "deferred"

class Order(BaseModel):
    __tablename__ = 'orders'
    
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey('warehouses.id'), nullable=False, index=True)
    customer_name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=True, index=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING, index=True)