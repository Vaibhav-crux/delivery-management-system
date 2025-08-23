from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.agent import Agent, AgentStatus
from models.order import Order, OrderStatus
from models.assignment import Assignment, AssignmentStatus
from models.warehouse import Warehouse
from services.agents_service import AgentService
from services.order_service import OrderService
import logging
import math
from datetime import date, datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class AllocationService:
    def __init__(self, session_factory, agent_service: AgentService, order_service: OrderService):
        self.session_factory = session_factory
        self.agent_service = agent_service
        self.order_service = order_service

    def haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula."""
        R = 6371  # Earth's radius in km
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    async def allocate_orders(self) -> dict:
        """Run order allocation for checked-in agents and pending orders."""
        async with self.session_factory() as session:
            try:
                # Fetch checked-in agents
                agents = await self.agent_service.get_checked_in_agents()
                if not agents:
                    logger.warning("No checked-in agents found for allocation")
                    return {"message": "No checked-in agents available", "status": 200}
                logger.debug(f"Checked-in agents: {agents}")

                # Fetch pending orders
                pending_orders = await self.order_service.get_pending_orders()
                if not pending_orders:
                    logger.warning("No pending orders found for allocation")
                    return {"message": "No pending orders available", "status": 200}
                logger.debug(f"Pending orders: {pending_orders}")

                # Initialize assignments
                assignments = []
                agent_loads = {agent["id"]: {"orders": [], "total_time": 0, "total_distance": 0} for agent in agents}
                max_work_hours = 10 * 60  # 10 hours in minutes
                max_distance = 100  # 100 km
                delivery_time_per_order = 30  # Fixed delivery time per order in minutes
                travel_time_per_km = 5  # 5 minutes per km

                # Sort orders by warehouse to optimize assignment
                orders_by_warehouse = {}
                for order in pending_orders:
                    warehouse_id = str(order["warehouse_id"])
                    if warehouse_id not in orders_by_warehouse:
                        orders_by_warehouse[warehouse_id] = []
                    orders_by_warehouse[warehouse_id].append(order)
                logger.debug(f"Orders grouped by warehouse: {orders_by_warehouse}")

                # Log warehouses with orders but no agents
                agent_warehouse_ids = {agent["warehouse_id"] for agent in agents}
                order_warehouse_ids = set(orders_by_warehouse.keys())
                unmatched_warehouses = order_warehouse_ids - agent_warehouse_ids
                if unmatched_warehouses:
                    logger.warning(f"No checked-in agents for warehouses with orders: {unmatched_warehouses}")
                    for warehouse_id in unmatched_warehouses:
                        logger.warning(f"Orders in warehouse {warehouse_id} will be deferred: {[o['id'] for o in orders_by_warehouse[warehouse_id]]}")

                # Fetch warehouse names for response
                warehouse_ids = list(orders_by_warehouse.keys())
                warehouse_query = await session.execute(
                    select(Warehouse).where(Warehouse.id.in_(warehouse_ids))
                )
                warehouses = {str(w.id): w.name for w in warehouse_query.scalars().all()}
                logger.debug(f"Warehouse names: {warehouses}")

                # Fetch agent names for response
                agent_ids = [agent["id"] for agent in agents]
                agent_query = await session.execute(
                    select(Agent).where(Agent.id.in_(agent_ids))
                )
                agent_names = {str(a.id): a.name for a in agent_query.scalars().all()}
                logger.debug(f"Agent names: {agent_names}")

                # Assign orders to agents
                for agent in agents:
                    agent_id = agent["id"]
                    warehouse_id = str(agent["warehouse_id"])
                    if warehouse_id not in orders_by_warehouse:
                        logger.warning(f"No orders found for warehouse {warehouse_id} for agent {agent_id}")
                        continue

                    orders = orders_by_warehouse[warehouse_id]
                    # Sort orders by distance from warehouse to optimize
                    orders.sort(key=lambda o: self.haversine(
                        agent["latitude"], agent["longitude"], o["latitude"], o["longitude"]
                    ))

                    for order in orders:
                        distance = self.haversine(
                            agent["latitude"], agent["longitude"], order["latitude"], order["longitude"]
                        )
                        travel_time = distance * travel_time_per_km
                        total_time = travel_time + delivery_time_per_order

                        # Check compliance constraints
                        if (agent_loads[agent_id]["total_time"] + total_time <= max_work_hours and
                            agent_loads[agent_id]["total_distance"] + distance <= max_distance):
                            # Assign order to agent
                            agent_loads[agent_id]["orders"].append(order)
                            agent_loads[agent_id]["total_time"] += total_time
                            agent_loads[agent_id]["total_distance"] += distance
                            assignments.append({
                                "agent_id": agent_id,
                                "order_id": order["id"],
                                "distance": distance,
                                "time": total_time,
                                "warehouse_name": warehouses.get(warehouse_id, "Unknown"),
                                "customer_name": order["customer_name"],
                                "agent_name": agent_names.get(agent_id, "Unknown")
                            })
                            logger.info(f"Assigned order {order['id']} to agent {agent_id} (Warehouse: {warehouses.get(warehouse_id, 'Unknown')})")

                # Calculate cost and optimize for profitability
                total_cost = 0
                for agent_id, load in agent_loads.items():
                    order_count = len(load["orders"])
                    if order_count >= 50:
                        cost_per_order = 42
                    elif order_count >= 25:
                        cost_per_order = 35
                    else:
                        cost_per_order = 500 / max(1, order_count)  # Ensure minimum INR 500/day
                    total_cost += order_count * cost_per_order

                # Persist assignments
                for assignment in assignments:
                    new_assignment = Assignment(
                        date=date.today(),
                        agent_id=assignment["agent_id"],
                        order_id=assignment["order_id"],
                        delivery_time_minutes=assignment["time"],
                        travel_distance_km=assignment["distance"],
                        status=AssignmentStatus.ASSIGNED
                    )
                    session.add(new_assignment)
                    # Update order status to ASSIGNED
                    await self.order_service.update_order_status(assignment["order_id"], OrderStatus.ASSIGNED)

                # Defer unassigned orders
                assigned_order_ids = {a["order_id"] for a in assignments}
                for order in pending_orders:
                    if order["id"] not in assigned_order_ids:
                        await self.order_service.defer_order(order["id"])

                await session.commit()
                logger.info(f"Order allocation completed: {len(assignments)} assignments created, total cost INR {total_cost}")
                return {
                    "message": "Order allocation completed",
                    "assignments_created": len(assignments),
                    "total_cost": total_cost,
                    "assignments": [
                        {
                            "order_id": a["order_id"],
                            "agent_id": a["agent_id"],
                            "agent_name": a["agent_name"],
                            "warehouse_name": a["warehouse_name"],
                            "customer_name": a["customer_name"],
                            "travel_distance_km": a["distance"],
                            "delivery_time_minutes": a["time"]
                        } for a in assignments
                    ],
                    "status": 200
                }
            except Exception as e:
                await session.rollback()
                logger.error(f"Order allocation failed: {str(e)}", exc_info=True)
                return {"error": f"Failed to allocate orders: {str(e)}", "status": 500}

    async def run_daily_allocation(self):
        """Run allocation job at 7:00 AM daily."""
        while True:
            now = datetime.now()
            target_time = now.replace(hour=7, minute=0, second=0, microsecond=0)
            if now > target_time:
                target_time += timedelta(days=1)
            wait_seconds = (target_time - now).total_seconds()
            logger.info(f"Waiting {wait_seconds/3600:.2f} hours until next allocation at {target_time}")
            await asyncio.sleep(wait_seconds)
            await self.allocate_orders()