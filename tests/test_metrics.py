import pytest
import asyncio
import uuid
from datetime import datetime, date
from unittest.mock import patch
from quart import Quart
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient
from app.main import app as quart_app
from app.models.base_model import Base
from app.models.user import User, UserStatus
from app.models.warehouse import Warehouse, WarehouseStatus
from app.models.agent import Agent, AgentStatus
from app.models.order import Order, OrderStatus
from app.models.assignment import Assignment, AssignmentStatus
from app.config.settings import Config
from app.core.jwt import JWTConfig

# Test configuration
@pytest.fixture(scope="session")
def config():
    class TestConfig(Config):
        def __init__(self):
            self.FLASK_ENV = "testing"
            self.DEBUG = True
            self.PORT = 5000
            self.HOST = "127.0.0.1"
            self.SECRET_KEY = "test-secret-key"
            self.JWT_ALGORITHM = "HS256"
            self.JWT_EXPIRATION_TIME = 3600
            self.DB_HOST = "sqlite+aiosqlite:///:memory:"
            self.DB_PORT = None
            self.DB_NAME = None
            self.DB_USER = None
            self.DB_PASSWORD = None
            self.LOG_LEVEL = "DEBUG"
            self.LOG_FILE = "test.log"
            self.ALLOWED_ORIGINS = "*"
            self.SCHEDULER_API_ENABLED = False

        def _validate(self):
            pass  # Skip validation for in-memory SQLite

    return TestConfig()

@pytest.fixture(scope="session")
async def test_app(config):
    app = Quart(__name__)
    app.config.from_object(config)
    return app

@pytest.fixture(scope="session")
async def async_session(config):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield session_factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(test_app):
    async with AsyncClient(app=test_app, base_url="http://127.0.0.1:5000") as client:
        yield client

@pytest.fixture
async def setup_test_data(async_session):
    async with async_session() as session:
        # Create test user
        user = User(
            id=uuid.uuid4(),
            username="arjun_sharma",
            email="arjun.sharma@example.com",
            password_hash="$2b$12$fakehash1234567890abcdef",  # Mocked bcrypt hash
            status=UserStatus.ACTIVE
        )
        session.add(user)

        # Create 10 warehouses
        warehouses = [
            Warehouse(
                id=uuid.uuid4(),
                name=f"Delhi Warehouse {i+1}",
                latitude=28.7041 + (i * 0.01),
                longitude=77.1025 + (i * 0.01),
                status=WarehouseStatus.OPERATIONAL
            ) for i in range(10)
        ]
        session.add_all(warehouses)

        # Create 20 agents per warehouse (200 total)
        agents = []
        for w in warehouses:
            for i in range(20):
                agent = Agent(
                    id=uuid.uuid4(),
                    name=f"Agent {i+1} W{w.name}",
                    warehouse_id=w.id,
                    latitude=w.latitude + 0.001,
                    longitude=w.longitude + 0.001,
                    status=AgentStatus.CHECKED_IN,
                    daily_check_in=datetime.utcnow()
                )
                agents.append(agent)
        session.add_all(agents)

        # Create 60 orders per agent (12,000 total)
        orders = []
        for agent in agents:
            for i in range(60):
                order = Order(
                    id=uuid.uuid4(),
                    warehouse_id=agent.warehouse_id,
                    customer_name=f"Customer {i+1} A{agent.name}",
                    address=f"{i+1} MG Road, Delhi",
                    latitude=agent.latitude + 0.002,
                    longitude=agent.longitude + 0.002,
                    status=OrderStatus.PENDING
                )
                orders.append(order)
        session.add_all(orders)

        await session.commit()
        return {"user": user, "warehouses": warehouses, "agents": agents, "orders": orders}

@pytest.fixture
def mock_jwt():
    with patch("app.services.auth.AuthService.generate_token") as mock_generate:
        mock_generate.return_value = "mocked-jwt-token"
        with patch("app.services.auth.AuthService.validate_token") as mock_validate:
            mock_validate.return_value = {"user_id": str(uuid.uuid4()), "username": "arjun_sharma"}
            yield

# Test cases
@pytest.mark.asyncio
async def test_signup(client, async_session):
    response = await client.post("/api/v1/auth/signup", json={
        "username": "priya_mehta",
        "email": "priya.mehta@example.com",
        "password": "password123"
    })
    assert response.status_code == 201
    data = await response.json()
    assert "access_token" in data
    assert "user_id" in data

@pytest.mark.asyncio
async def test_login(client, setup_test_data):
    response = await client.post("/api/v1/auth/login", json={
        "username": "arjun_sharma",
        "password": "password123"
    })
    assert response.status_code == 200
    data = await response.json()
    assert "access_token" in data
    assert "user_id" in data

@pytest.mark.asyncio
async def test_deactivate_user(client, setup_test_data, mock_jwt):
    user_id = str(setup_test_data["user"].id)
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == 200
    data = await response.json()
    assert data["message"] == "User account deactivated"

@pytest.mark.asyncio
async def test_create_warehouse(client, setup_test_data, mock_jwt):
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.post("/api/v1/warehouses", json={
        "name": "Delhi Warehouse 11",
        "latitude": 28.8141,
        "longitude": 77.2025
    }, headers=headers)
    assert response.status_code == 201
    data = await response.json()
    assert data["name"] == "Delhi Warehouse 11"
    assert data["status"] == "operational"

@pytest.mark.asyncio
async def test_get_warehouses(client, setup_test_data, mock_jwt):
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.get("/api/v1/warehouses", headers=headers)
    assert response.status_code == 200
    data = await response.json()
    assert len(data["warehouses"]) == 10
    assert data["warehouses"][0]["name"].startswith("Delhi Warehouse")

@pytest.mark.asyncio
async def test_deactivate_warehouse(client, setup_test_data, mock_jwt):
    warehouse_id = str(setup_test_data["warehouses"][0].id)
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.delete(f"/api/v1/warehouses/{warehouse_id}", headers=headers)
    assert response.status_code == 200
    data = await response.json()
    assert data["message"] == "Warehouse deactivated"

@pytest.mark.asyncio
async def test_create_agent(client, setup_test_data, mock_jwt):
    warehouse_id = str(setup_test_data["warehouses"][0].id)
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.post("/api/v1/agents", json={
        "name": "Agent New",
        "warehouse_id": warehouse_id,
        "latitude": 28.7041,
        "longitude": 77.1025
    }, headers=headers)
    assert response.status_code == 201
    data = await response.json()
    assert data["name"] == "Agent New"
    assert data["status"] == "available"

@pytest.mark.asyncio
async def test_get_checked_in_agents(client, setup_test_data, mock_jwt):
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.get("/api/v1/agents/checked-in", headers=headers)
    assert response.status_code == 200
    data = await response.json()
    assert len(data["agents"]) == 200  # 20 agents per 10 warehouses
    assert data["agents"][0]["status"] == "checked_in"

@pytest.mark.asyncio
async def test_check_in_agent(client, setup_test_data, mock_jwt):
    agent_id = str(setup_test_data["agents"][0].id)
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.post("/api/v1/agents/check-in", json={
        "agent_id": agent_id,
        "latitude": 28.7041,
        "longitude": 77.1025
    }, headers=headers)
    assert response.status_code == 200
    data = await response.json()
    assert data["message"] == "Agent checked in successfully"

@pytest.mark.asyncio
async def test_create_order(client, setup_test_data, mock_jwt):
    warehouse_id = str(setup_test_data["warehouses"][0].id)
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.post("/api/v1/orders", json={
        "warehouse_id": warehouse_id,
        "customer_name": "Priya Sharma",
        "address": "123 MG Road, Delhi",
        "latitude": 28.7041,
        "longitude": 77.1025
    }, headers=headers)
    assert response.status_code == 201
    data = await response.json()
    assert data["customer_name"] == "Priya Sharma"
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_allocate_orders(client, setup_test_data, mock_jwt, async_session):
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    response = await client.post("/api/v1/orders/allocate", headers=headers)
    assert response.status_code == 200
    data = await response.json()
    assert data["message"] == "Order allocation completed"
    assert data["assignments_created"] > 0  # Should assign at least some orders
    assert data["total_cost"] > 0

    # Verify database state
    async with async_session() as session:
        result = await session.execute(
            select(Assignment).where(Assignment.status == AssignmentStatus.ASSIGNED)
        )
        assignments = result.scalars().all()
        assert len(assignments) == data["assignments_created"]
        result = await session.execute(
            select(Order).where(Order.status == OrderStatus.ASSIGNED)
        )
        assigned_orders = result.scalars().all()
        assert len(assigned_orders) == data["assignments_created"]

@pytest.mark.asyncio
async def test_get_assignments(client, setup_test_data, mock_jwt, async_session):
    # First, run allocation to create assignments
    headers = {"Authorization": "Bearer mocked-jwt-token"}
    await client.post("/api/v1/orders/allocate", headers=headers)

    response = await client.get("/api/v1/assignments", headers=headers)
    assert response.status_code == 200
    data = await response.json()
    assert len(data["assignments"]) > 0
    assert data["total_assignments"] > 0
    assert data["assignments"][0]["status"] == "assigned"
    assert "agent_name" in data["assignments"][0]
    assert "warehouse_name" in data["assignments"][0]
    assert "customer_name" in data["assignments"][0]