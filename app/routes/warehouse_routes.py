from quart import Blueprint, request, jsonify
from sqlalchemy.ext.asyncio import AsyncSession
from services.warehouse_service import WarehouseService
from services.auth import AuthService
import logging
import traceback

warehouse_bp = Blueprint('warehouse', __name__, url_prefix='/api/v1')
logger = logging.getLogger(__name__)

def init_warehouse_routes(session_factory, auth_service: AuthService):
    warehouse_service = WarehouseService(session_factory, auth_service)

    @warehouse_bp.route('/warehouses', methods=['POST'])
    async def create_warehouse():
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            data = await request.get_json()
            if not data or not all(key in data for key in ['name', 'latitude', 'longitude']):
                logger.warning("Invalid create warehouse request: missing required fields")
                return jsonify({"error": "Missing required fields"}), 400

            result = await warehouse_service.create_warehouse(
                name=data['name'],
                latitude=data['latitude'],
                longitude=data['longitude'],
                token=token
            )
            if "error" in result:
                return jsonify(result), result.get("status", 500)
            return jsonify(result), 201
        except ValueError as e:
            logger.warning(f"Invalid create warehouse request: {str(e)}")
            return jsonify({"error": "Invalid JSON format"}), 400
        except Exception as e:
            logger.error(f"Create warehouse endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @warehouse_bp.route('/warehouses', methods=['GET'])
    async def get_warehouses():
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            result = await warehouse_service.get_warehouses(token)
            if "error" in result:
                return jsonify(result), result.get("status", 500)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Get warehouses endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @warehouse_bp.route('/warehouses/<warehouse_id>', methods=['DELETE'])
    async def delete_warehouse(warehouse_id):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning("Missing or invalid Authorization header")
                return jsonify({"error": "Missing or invalid Authorization header"}), 401
            token = auth_header.split(' ')[1]

            result = await warehouse_service.delete_warehouse(warehouse_id, token)
            if "error" in result:
                return jsonify(result), result.get("status", 500)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Delete warehouse endpoint error for {warehouse_id}: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    return warehouse_bp