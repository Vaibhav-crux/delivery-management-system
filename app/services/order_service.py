from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.order import Order, OrderStatus
from models.warehouse import Warehouse, WarehouseStatus
from services.auth import AuthService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self, session_factory, auth_service: AuthService):
        self.session_factory = session_factory
        self.auth_service = auth_service

    async def create_order(self, warehouse_id: str, customer_name: str, address: str, latitude: float, longitude: float, token: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Validate user token
                auth_result = await self.auth_service.validate_user_token(token)
                if "error" in auth_result:
                    return auth_result

                # Check if warehouse exists and is operational
                warehouse_result = await session.execute(
                    select(Warehouse).where(Warehouse.id == warehouse_id)
                )
                warehouse = warehouse_result.scalars().first()
                if not warehouse or warehouse.status != WarehouseStatus.OPERATIONAL:
                    logger.warning(f"Order creation attempt for non-operational warehouse: {warehouse_id}")
                    return {"error": "Warehouse not found or not operational", "status": 400}

                # Create new order
                order = Order(
                    warehouse_id=warehouse_id,
                    customer_name=customer_name,
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                    status=OrderStatus.PENDING
                )
                session.add(order)
                await session.commit()
                await session.refresh(order)
                logger.info(f"Order created successfully: {order.id}")
                return {
                    "id": str(order.id),
                    "warehouse_id": str(order.warehouse_id),
                    "customer_name": order.customer_name,
                    "address": order.address,
                    "latitude": order.latitude,
                    "longitude": order.longitude,
                    "status": order.status.value
                }
            except Exception as e:
                await session.rollback()
                logger.error(f"Order creation failed: {str(e)}", exc_info=True)
                return {"error": f"Failed to create order: {str(e)}", "status": 500}

    async def get_pending_orders(self) -> list:
        async with self.session_factory() as session:
            try:
                # Fetch pending orders from operational warehouses
                result = await session.execute(
                    select(Order, Warehouse)
                    .join(Warehouse, Order.warehouse_id == Warehouse.id)
                    .where(Order.status == OrderStatus.PENDING)
                    .where(Warehouse.status == WarehouseStatus.OPERATIONAL)
                )
                rows = result.all()
                orders = [
                    {
                        "id": str(order.id),
                        "warehouse_id": str(order.warehouse_id),
                        "customer_name": order.customer_name,
                        "address": order.address,
                        "latitude": order.latitude,
                        "longitude": order.longitude
                    }
                    for order, _ in rows
                ]
                logger.info(f"Retrieved {len(orders)} pending orders: {orders}")
                return orders
            except Exception as e:
                logger.error(f"Failed to retrieve pending orders: {str(e)}", exc_info=True)
                return []

    async def update_order_status(self, order_id: str, status: OrderStatus) -> None:
        async with self.session_factory() as session:
            try:
                result = await session.execute(
                    select(Order).where(Order.id == order_id)
                )
                order = result.scalars().first()
                if order:
                    order.status = status
                    await session.commit()
                    logger.info(f"Order {order_id} status updated to {status.value}")
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to update order status for {order_id}: {str(e)}", exc_info=True)

    async def defer_order(self, order_id: str) -> None:
        async with self.session_factory() as session:
            try:
                result = await session.execute(
                    select(Order).where(Order.id == order_id)
                )
                order = result.scalars().first()
                if order:
                    order.status = OrderStatus.DEFERRED
                    await session.commit()
                    logger.info(f"Order {order_id} deferred to next day")
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to defer order {order_id}: {str(e)}", exc_info=True)