from quart import Blueprint, request, jsonify
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.assignment import Assignment, AssignmentStatus
from models.agent import Agent
from models.order import Order
from models.warehouse import Warehouse
from services.auth import AuthService
import logging

assignment_bp = Blueprint('assignments', __name__, url_prefix='/api/v1')
logger = logging.getLogger(__name__)

def init_assignment_routes(session_factory, auth_service: AuthService):
    @assignment_bp.route('/assignments', methods=['GET'])
    async def get_assignments():
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            # Validate token
            auth_result = await auth_service.validate_user_token(token)
            if "error" in auth_result:
                return jsonify(auth_result), auth_result.get("status", 401)

            async with session_factory() as session:
                # Fetch assignments with related data
                result = await session.execute(
                    select(Assignment, Agent, Order, Warehouse)
                    .join(Agent, Assignment.agent_id == Agent.id)
                    .join(Order, Assignment.order_id == Order.id)
                    .join(Warehouse, Order.warehouse_id == Warehouse.id)
                )
                assignments = result.all()
                logger.info(f"Retrieved {len(assignments)} assignments")

                response = [
                    {
                        "assignment_id": str(assignment.id),
                        "order_id": str(assignment.order_id),
                        "agent_id": str(assignment.agent_id),
                        "agent_name": agent.name,
                        "customer_name": order.customer_name,
                        "warehouse_name": warehouse.name,
                        "travel_distance_km": assignment.travel_distance_km,
                        "delivery_time_minutes": assignment.delivery_time_minutes,
                        "status": assignment.status.value,
                        "date": assignment.date.isoformat()
                    }
                    for assignment, agent, order, warehouse in assignments
                ]

                return jsonify({
                    "assignments": response,
                    "total_assignments": len(response),
                    "status": 200
                }), 200
        except Exception as e:
            logger.error(f"Get assignments endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    return assignment_bp