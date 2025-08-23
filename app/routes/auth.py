from quart import Blueprint, request, jsonify
from sqlalchemy.ext.asyncio import AsyncSession
from core.jwt import JWTConfig
from services.auth import AuthService
import logging
import traceback

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1')
logger = logging.getLogger(__name__)

def init_auth_routes(session_factory, jwt_config: JWTConfig):
    auth_service = AuthService(session_factory, jwt_config)

    async def require_auth():
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("Missing or invalid Authorization header")
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(' ')[1]
        result = await auth_service.validate_user_token(token)
        if "error" in result:
            return jsonify(result), result.get("status", 500)
        return None

    @auth_bp.route('/signup', methods=['POST'])
    async def signup():
        try:
            data = await request.get_json()
            if not data or not all(key in data for key in ['username', 'email', 'password']):
                logger.warning("Invalid signup request: missing required fields")
                return jsonify({"error": "Missing required fields"}), 400

            result = await auth_service.signup(
                username=data['username'],
                email=data['email'],
                password=data['password']
            )
            if "error" in result:
                return jsonify(result), 400
            return jsonify(result), 201
        except ValueError as e:
            logger.warning(f"Invalid signup request: {str(e)}")
            return jsonify({"error": "Invalid JSON format"}), 400
        except Exception as e:
            logger.error(f"Signup endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @auth_bp.route('/login', methods=['POST'])
    async def login():
        try:
            data = await request.get_json()
            if not data or not all(key in data for key in ['username', 'password']):
                logger.warning("Invalid login request: missing required fields")
                return jsonify({"error": "Missing required fields"}), 400

            result = await auth_service.login(
                username=data['username'],
                password=data['password']
            )
            if "error" in result:
                return jsonify(result), 401
            return jsonify(result), 200
        except ValueError as e:
            logger.warning(f"Invalid login request: {str(e)}")
            return jsonify({"error": "Invalid JSON format"}), 400
        except Exception as e:
            logger.error(f"Login endpoint error: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    @auth_bp.route('/users/<user_id>', methods=['DELETE'])
    async def delete_user(user_id):
        try:
            # Validate JWT token and user status
            auth_result = await require_auth()
            if auth_result:
                return auth_result

            result = await auth_service.delete_user(user_id, request.headers.get('Authorization').split(' ')[1])
            if "error" in result:
                return jsonify(result), result.get("status", 500)
            return jsonify(result), 200
        except Exception as e:
            logger.error(f"Delete user endpoint error for {user_id}: {str(e)}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    return auth_bp