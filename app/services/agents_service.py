from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.agent import Agent, AgentStatus
from models.warehouse import Warehouse, WarehouseStatus
from services.auth import AuthService
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, session_factory, auth_service: AuthService):
        self.session_factory = session_factory
        self.auth_service = auth_service

    async def create_agent(self, name: str, phone: str, warehouse_id: str, token: str) -> dict:
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
                    logger.warning(f"Agent creation attempt for non-operational warehouse: {warehouse_id}")
                    return {"error": "Warehouse not found or not operational", "status": 400}

                # Create new agent
                agent = Agent(
                    name=name,
                    phone=phone,
                    warehouse_id=warehouse_id,
                    status=AgentStatus.INACTIVE
                )
                session.add(agent)
                await session.commit()
                await session.refresh(agent)
                logger.info(f"Agent created successfully: {name}")
                return {
                    "id": str(agent.id),
                    "name": agent.name,
                    "phone": agent.phone,
                    "warehouse_id": str(agent.warehouse_id),
                    "status": agent.status.value
                }
            except Exception as e:
                await session.rollback()
                logger.error(f"Agent creation failed for {name}: {str(e)}", exc_info=True)
                return {"error": f"Failed to create agent: {str(e)}", "status": 500}

    async def check_in_agent(self, agent_id: str, token: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Validate user token
                auth_result = await self.auth_service.validate_user_token(token)
                if "error" in auth_result:
                    return auth_result

                # Find agent
                result = await session.execute(
                    select(Agent).where(Agent.id == agent_id)
                )
                agent = result.scalars().first()
                if not agent:
                    logger.warning(f"Check-in attempt for non-existent agent_id: {agent_id}")
                    return {"error": "Agent not found", "status": 404}

                # Check if agent's warehouse is operational
                warehouse_result = await session.execute(
                    select(Warehouse).where(Warehouse.id == agent.warehouse_id)
                )
                warehouse = warehouse_result.scalars().first()
                if not warehouse or warehouse.status != WarehouseStatus.OPERATIONAL:
                    logger.warning(f"Check-in attempt for agent {agent_id} at non-operational warehouse")
                    return {"error": "Warehouse is not operational", "status": 400}

                # Update agent status and check-in time
                agent.status = AgentStatus.CHECKED_IN
                agent.daily_check_in = datetime.utcnow()
                await session.commit()
                logger.info(f"Agent checked in successfully: {agent_id}")
                return {
                    "message": "Agent checked in",
                    "agent_id": str(agent.id),
                    "status": agent.status.value
                }
            except Exception as e:
                await session.rollback()
                logger.error(f"Agent check-in failed for {agent_id}: {str(e)}", exc_info=True)
                return {"error": f"Failed to check in agent: {str(e)}", "status": 500}

    async def get_checked_in_agents(self) -> list:
        async with self.session_factory() as session:
            try:
                # Fetch agents who are checked in and belong to operational warehouses
                result = await session.execute(
                    select(Agent, Warehouse)
                    .join(Warehouse, Agent.warehouse_id == Warehouse.id)
                    .where(Agent.status == AgentStatus.CHECKED_IN)
                    .where(Warehouse.status == WarehouseStatus.OPERATIONAL)
                )
                rows = result.all()
                logger.info(f"Retrieved {len(rows)} checked-in agents from query")
                agents = [
                    {
                        "id": str(agent.id),
                        "name": agent.name,
                        "warehouse_id": str(agent.warehouse_id),
                        "latitude": warehouse.latitude,
                        "longitude": warehouse.longitude,
                        "daily_check_in": agent.daily_check_in.isoformat() if agent.daily_check_in else None
                    }
                    for agent, warehouse in rows
                ]
                if not agents:
                    logger.warning("No checked-in agents found in operational warehouses")
                else:
                    logger.debug(f"Checked-in agents: {agents}")
                return agents
            except Exception as e:
                logger.error(f"Failed to retrieve checked-in agents: {str(e)}", exc_info=True)
                return []

    async def get_all_checked_in_agents(self, token: str) -> dict:
        async with self.session_factory() as session:
            try:
                # Validate user token
                auth_result = await self.auth_service.validate_user_token(token)
                if "error" in auth_result:
                    return auth_result

                # Fetch checked-in agents
                agents = await self.get_checked_in_agents()
                if not agents:
                    logger.info("No checked-in agents found for listing")
                    return {"message": "No checked-in agents available", "agents": [], "status": 200}

                logger.info(f"Returning {len(agents)} checked-in agents")
                return {"agents": agents, "status": 200}
            except Exception as e:
                logger.error(f"Failed to retrieve all checked-in agents: {str(e)}", exc_info=True)
                return {"error": f"Failed to retrieve checked-in agents: {str(e)}", "status": 500}