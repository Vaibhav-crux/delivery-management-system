from sqlalchemy import Column, String, Float, Enum
from enum import Enum as PyEnum
from models.base_model import Base, BaseModel

class WarehouseStatus(PyEnum):
    OPERATIONAL = "operational"
    INACTIVE = "inactive"

class Warehouse(BaseModel):
    __tablename__ = 'warehouses'
    
    name = Column(String, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(Enum(WarehouseStatus), nullable=False, default=WarehouseStatus.OPERATIONAL, index=True)