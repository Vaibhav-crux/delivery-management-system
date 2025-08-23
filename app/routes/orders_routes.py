from quart import Blueprint, request, jsonify
from sqlalchemy.ext.asyncio import AsyncSession
from services.order_service import OrderService
from services.auth import AuthService
from services.allocation_service import AllocationService
from services.agents_service import AgentService
import logging

order_bp = Blueprint('orders', __name__, url_prefix='/api/v1')
logger = logging.getLogger(__name__)

def init_order_routes(session_factory, auth_service: AuthService):
    order_service = OrderService(session_factory, auth_service)
    allocation_service = AllocationService(session_factory, AgentService(session_factory, auth_service), order_service)

    @order_bp.route('/orders', methods=['POST'])
    async def create_order():
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            data = await request.get_json()
            if not data or not all(key in data for key in ['warehouse_id', 'customer_name', 'address', 'latitude', 'longitude']):
                logger.warning("Invalid create order request: missing required fields")
                return jsonify({"error": "Missing required fields"}), 400

            result = await order_service.create_order(
                warehouse_id=data['warehouse_id'],
                customer_name=data['customer_name'],
                address=data['address'],
                latitude=data['latitude'],
                longitude=data['longitude'],
                token=token
            )
            if "error" in result:
                return jsonify(result), result.get("status", 500)
            return jsonify(result), 201
        except ValueError as e:
            logger.warning(f"Invalid create order request: {str(e)}")
            return jsonify({"error": "Invalid JSON format"}), 400
        except Exception as e:
            logger.error(f"Create order endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @order_bp.route('/orders/allocate', methods=['POST'])
    async def trigger_allocation():
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            # Validate user token
            auth_result = await auth_service.validate_user_token(token)
            if "error" in auth_result:
                return jsonify(auth_result), auth_result.get("status", 401)

            result = await allocation_service.allocate_orders()
            return jsonify(result), result.get("status", 200)
        except Exception as e:
            logger.error(f"Trigger allocation endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    return order_bp