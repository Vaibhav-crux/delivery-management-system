import asyncio
import logging
from quart import Quart
from quart_cors import cors
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config.settings import Config
from core.db_config import DatabaseConfig
from core.jwt import JWTConfig
from middleware.logger import setup_logger
from middleware.gzip import GzipMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.lifespan import LifespanMiddleware
from routes.auth import init_auth_routes
from routes.warehouse_routes import init_warehouse_routes
from routes.orders_routes import init_order_routes
from routes.agents_routes import init_agent_routes
from routes.assignments_routes import init_assignment_routes
from services.auth import AuthService
from services.agents_service import AgentService
from services.order_service import OrderService
from services.allocation_service import AllocationService
from models.base_model import Base
from models.user import User
from models.agent import Agent
from models.warehouse import Warehouse
from models.order import Order
from models.assignment import Assignment

# Initialize Quart app
app = Quart(__name__)

# Load configuration
config = Config()
app.config["RATE_LIMIT"] = config.RATE_LIMIT  # Load RATE_LIMIT into app config

# Apply CORS settings
app = cors(app, allow_origin=config.ALLOWED_ORIGINS)

# Setup logging
setup_logger(config.LOG_LEVEL, config.LOG_FILE)
logger = logging.getLogger(__name__)

# Apply middleware
app.asgi_app = LifespanMiddleware(app.asgi_app)  # Apply lifespan middleware first
app.asgi_app = RateLimitMiddleware(app.asgi_app)  # Apply rate limiting second
app.asgi_app = GzipMiddleware(app.asgi_app)  # Apply gzip compression last

# Initialize database
db_config = DatabaseConfig(config)
jwt_config = JWTConfig(config)
engine = None
async_session = None

async def init_db():
    global engine, async_session
    try:
        engine = create_async_engine(
            db_config.get_db_url(),
            echo=False,
            future=True
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async_session = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("Database connected and tables created")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}", exc_info=True)
        raise

@app.route('/api/v1/health', methods=['GET'])
async def health_check():
    try:
        async with async_session() as session:
            await session.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}, 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {"status": "unhealthy", "database": "disconnected"}, 500

async def main():
    # Initialize database connection
    await init_db()
    
    # Initialize services
    auth_service = AuthService(async_session, jwt_config)
    agent_service = AgentService(async_session, auth_service)
    order_service = OrderService(async_session, auth_service)
    allocation_service = AllocationService(async_session, agent_service, order_service)
    
    # Start background allocation job
    asyncio.create_task(allocation_service.run_daily_allocation())
    
    # Register blueprints after session initialization
    app.register_blueprint(init_auth_routes(async_session, jwt_config))
    app.register_blueprint(init_warehouse_routes(async_session, auth_service))
    app.register_blueprint(init_order_routes(async_session, auth_service))
    app.register_blueprint(init_agent_routes(async_session, auth_service))
    app.register_blueprint(init_assignment_routes(async_session, auth_service))
    
    # Start Quart server
    logger.info(f"Quart server starting on {config.HOST}:{config.PORT}")
    from hypercorn.config import Config as HypercornConfig
    from hypercorn.asyncio import serve
    
    hypercorn_config = HypercornConfig()
    hypercorn_config.bind = [f"{config.HOST}:{config.PORT}"]
    hypercorn_config.loglevel = config.LOG_LEVEL.lower()
    
    await serve(app, hypercorn_config)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown initiated")
    except Exception as e:
        logger.error(f"Server failed to start: {str(e)}", exc_info=True)
        raise