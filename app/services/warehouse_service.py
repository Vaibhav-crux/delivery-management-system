from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.warehouse import Warehouse, WarehouseStatus
from services.auth import AuthService
import logging
import traceback

logger = logging.getLogger(__name__)

class WarehouseService:
    def __init__(self, session_factory, auth_service: AuthService):
        self.session_factory = session_factory
        self.auth_service = auth_service

    async def create_warehouse(self, name: str, latitude: float, longitude: float, token: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Validate user token and status
                auth_result = await self.auth_service.validate_user_token(token)
                if "error" in auth_result:
                    return auth_result

                # Check if warehouse name already exists
                existing_warehouse = await session.execute(
                    select(Warehouse).where(Warehouse.name == name)
                )
                warehouse = existing_warehouse.scalars().first()

                if warehouse:
                    if warehouse.status == WarehouseStatus.OPERATIONAL:
                        logger.warning(f"Warehouse creation attempt with existing operational warehouse: {name}")
                        return {"error": "Warehouse name already exists and is operational", "status": 400}
                    elif warehouse.status == WarehouseStatus.INACTIVE:
                        # Update existing inactive warehouse to operational
                        warehouse.status = WarehouseStatus.OPERATIONAL
                        warehouse.latitude = latitude
                        warehouse.longitude = longitude
                        await session.commit()
                        await session.refresh(warehouse)
                        logger.info(f"Warehouse reactivated successfully: {name}")
                        return {
                            "id": str(warehouse.id),
                            "name": warehouse.name,
                            "latitude": warehouse.latitude,
                            "longitude": warehouse.longitude,
                            "status": warehouse.status.value
                        }
                
                # Create new warehouse if none exists
                warehouse = Warehouse(
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    status=WarehouseStatus.OPERATIONAL
                )
                session.add(warehouse)
                await session.commit()
                await session.refresh(warehouse)
                logger.info(f"Warehouse created successfully: {name}")
                return {
                    "id": str(warehouse.id),
                    "name": warehouse.name,
                    "latitude": warehouse.latitude,
                    "longitude": warehouse.longitude,
                    "status": warehouse.status.value
                }
            except Exception as e:
                await session.rollback()
                logger.error(f"Warehouse creation failed for {name}: {str(e)}", exc_info=True)
                return {"error": f"Failed to create warehouse: {str(e)}", "status": 500}

    async def get_warehouses(self, token: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Validate user token and status
                auth_result = await self.auth_service.validate_user_token(token)
                if "error" in auth_result:
                    return auth_result

                # Retrieve operational warehouses
                result = await session.execute(
                    select(Warehouse).where(Warehouse.status == WarehouseStatus.OPERATIONAL)
                )
                warehouses = result.scalars().all()
                logger.info("Operational warehouses retrieved successfully")
                return {
                    "warehouses": [
                        {
                            "id": str(w.id),
                            "name": w.name,
                            "latitude": w.latitude,
                            "longitude": w.longitude,
                            "status": w.status.value
                        } for w in warehouses
                    ]
                }
            except Exception as e:
                logger.error(f"Failed to retrieve warehouses: {str(e)}", exc_info=True)
                return {"error": f"Failed to retrieve warehouses: {str(e)}", "status": 500}

    async def delete_warehouse(self, warehouse_id: str, token: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Validate user token and status
                auth_result = await self.auth_service.validate_user_token(token)
                if "error" in auth_result:
                    return auth_result

                # Find warehouse
                result = await session.execute(
                    select(Warehouse).where(Warehouse.id == warehouse_id)
                )
                warehouse = result.scalars().first()
                if not warehouse:
                    logger.warning(f"Delete attempt for non-existent warehouse_id: {warehouse_id}")
                    return {"error": "Warehouse not found", "status": 404}

                # Set status to INACTIVE
                warehouse.status = WarehouseStatus.INACTIVE
                await session.commit()
                logger.info(f"Warehouse set to INACTIVE: {warehouse_id}")
                return {"message": "Warehouse deactivated"}
            except Exception as e:
                await session.rollback()
                logger.error(f"Delete warehouse failed for {warehouse_id}: {str(e)}", exc_info=True)
                return {"error": f"Failed to deactivate warehouse: {str(e)}", "status": 500}