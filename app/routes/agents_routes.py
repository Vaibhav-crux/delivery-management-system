from quart import Blueprint, request, jsonify
from sqlalchemy.ext.asyncio import AsyncSession
from services.agents_service import AgentService
from services.auth import AuthService
import logging

agent_bp = Blueprint('agents', __name__, url_prefix='/api/v1')
logger = logging.getLogger(__name__)

def init_agent_routes(session_factory, auth_service: AuthService):
    agent_service = AgentService(session_factory, auth_service)

    @agent_bp.route('/agents', methods=['POST'])
    async def create_agent():
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            data = await request.get_json()
            if not data or not all(key in data for key in ['name', 'phone', 'warehouse_id']):
                logger.warning("Invalid create agent request: missing required fields")
                return jsonify({"error": "Missing required fields"}), 400

            result = await agent_service.create_agent(
                name=data['name'],
                phone=data['phone'],
                warehouse_id=data['warehouse_id'],
                token=token
            )
            if "error" in result:
                return jsonify(result), result.get("status", 500)
            return jsonify(result), 201
        except ValueError as e:
            logger.warning(f"Invalid create agent request: {str(e)}")
            return jsonify({"error": "Invalid JSON format"}), 400
        except Exception as e:
            logger.error(f"Create agent endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @agent_bp.route('/agents/<agent_id>/check-in', methods=['POST'])
    async def check_in_agent(agent_id):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            result = await agent_service.check_in_agent(agent_id, token)
            if "error" in result:
                return jsonify(result), result.get("status", 500)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Check-in agent endpoint error for {agent_id}: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @agent_bp.route('/agents/checked-in', methods=['GET'])
    async def get_checked_in_agents():
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            result = await agent_service.get_all_checked_in_agents(token)
            if "error" in result:
                return jsonify(result), result.get("status", 500)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Get checked-in agents endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    return agent_bp