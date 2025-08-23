<img width="895" height="240" alt="Screenshot 2025-08-23 182909" src="https://github.com/user-attachments/assets/6d8ec1ce-617d-4e05-9f0b-1ecd4bf62b0a" /># Delivery Management System

## Overview

The Delivery Management System is a web application for managing logistics operations, including warehouses, agents, orders, and assignments. Built with [Quart](https://quart.palletsprojects.com/), an async Python web framework, it provides API endpoints for user authentication, warehouse management, agent check-ins, order creation, and automated order allocation. The system includes middleware for Gzip compression, rate limiting, and ASGI lifespan event handling to ensure performance and scalability.

**GitHub Repository**: [https://github.com/Vaibhav-crux/delivery-management-system](https://github.com/Vaibhav-crux/delivery-management-system)

Key features:
- **Authentication**: JWT-based user signup and login.
- **Warehouse Management**: Create, retrieve, and deactivate warehouses.
- **Agent Management**: Register, check-in, and manage agents.
- **Order Management**: Create and allocate orders to agents.
- **Assignment Management**: View order-agent assignments.
- **Middleware**:
  - Gzip compression for responses > 1KB (JSON/text).
  - Rate limiting (100 requests/minute per IP).
  - ASGI lifespan handling for startup/shutdown.
- **Background Jobs**: Daily order allocation to optimize assignments.

The system is tested with simulated data: 10 warehouses, 200 agents (20 per warehouse), and ~12,000 orders (60 per agent).

## Setup and Build/Run Instructions

### Prerequisites
- Python 3.8+
- PostgreSQL (or SQLite for testing)
- pip for package management
- Git for version control

### Setup Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Vaibhav-crux/delivery-management-system.git
   cd delivery-management-system
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   The `requirements.txt` includes:
   ```
   quart
   quart-cors
   sqlalchemy
   asyncpg
   python-dotenv
   bcrypt
   pytest
   pytest-asyncio
   httpx
   pytest-mock
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and update with your settings:
   ```bash
   cp .env.example .env
   ```
   Example `.env`:
   ```env
   # Quart settings
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   LOG_LEVEL=INFO
   LOG_FILE=app.log
   ALLOWED_ORIGINS=*
   SCHEDULER_API_ENABLED=False

   # Database settings
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=delivery_db
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password

   # JWT settings
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_TIME=3600

   # Rate Limiting
   RATE_LIMIT="100 per minute"
   ```
   For testing, use `DB_HOST=sqlite+aiosqlite:///:memory:`.

5. **Run the Application**:
   ```bash
   python app/main.py
   ```
   Expected logs:
   ```
   2025-08-23 17:30:00 - INFO - Database connected and tables created
   2025-08-23 17:30:00 - INFO - Lifespan startup received
   2025-08-23 17:30:00 - INFO - Quart server starting on 127.0.0.1:5000
   2025-08-23 17:30:00 - INFO - Waiting X.XX hours until next allocation at 2025-08-24 07:00:00
   [2025-08-23 17:30:00 +0530] [PID] [INFO] Running on http://127.0.0.1:5000 (CTRL + C to quit)
   ```

6. **Run Tests**:
   ```bash
   pytest -v tests/test_metrics.py
   ```
   Expected output (assuming similar tests to previous `test_api.py`):
   ```
   ============================= test session starts =============================
   collected X items
   tests/test_metrics.py::test_server_startup_no_lifespan_error PASSED       [ X%]
   tests/test_metrics.py::test_signup PASSED                                [ X%]
   ...
   ========================== X passed in X.XXs ==========================
   ```

## Approach to Allocation Logic

The allocation logic, implemented in `app/services/allocation_service.py`, assigns orders to agents daily to optimize delivery operations based on proximity (Haversine distance) and agent availability within the same warehouse.

### Allocation Logic Outline
1. **Fetch Data**:
   - Retrieve operational warehouses (`WarehouseStatus.OPERATIONAL`).
   - Get checked-in agents (`AgentStatus.CHECKED_IN`) per warehouse.
   - Fetch pending orders (`OrderStatus.PENDING`) per warehouse.
2. **Calculate Distances**:
   - Compute Haversine distance between each order’s delivery location and checked-in agents in the same warehouse.
3. **Assign Orders**:
   - Sort agents by distance to the order.
   - Assign the order to the closest available agent.
   - Update agent status to `ASSIGNED`, order status to `ASSIGNED`.
   - Create an `Assignment` record with calculated cost (distance-based).
4. **Handle Unassigned Orders**:
   - Defer orders if no agents are available or warehouse IDs don’t match.
5. **Log Metrics**:
   - Record assignments created, total cost, and deferred orders.
6. **Schedule**:
   - Run daily at 07:00 AM (configurable via `.env`).

### Flow-Chart
```
[SingUp User]
        ↓
[Login User]
        ↓
[Start Daily Allocation]
        ↓
[Fetch Operational Warehouses]
        ↓
[For Each Warehouse]
    ↓
    [Get Checked-in Agents]
    ↓
    [Get Pending Orders]
    ↓
    [For Each Order]
        ↓
        [Calculate Haversine Distance to Agents]
        ↓
        [Sort Agents by Distance]
        ↓
        [Assign to Closest Available Agent]
        ↓
        [Update Agent/Order Status]
        ↓
        [Create Assignment Record]
        ↓
        [If No Agent Available, Defer Order]
        ↓
[Log Metrics: Assignments, Cost, Deferred Orders]
        ↓
[Schedule Next Run at 07:00 AM]
```

## Tech Stack

- **Quart**: Async Python web framework, chosen for Flask-like API and ASGI support, ideal for handling concurrent requests (~12,000 orders).
- **SQLAlchemy (Async)**: ORM for database operations with PostgreSQL (or SQLite for testing), managing models (`User`, `Agent`, `Warehouse`, `Order`, `Assignment`).
- **Hypercorn**: ASGI server for Quart, supporting async operations and lifespan events.
- **python-dotenv**: Loads `.env` variables for configuration (e.g., `RATE_LIMIT`, database settings).
- **bcrypt**: Secures password hashing for authentication.
- **pytest/pytest-asyncio/httpx**: For testing API endpoints and async functionality.
- **Middleware**:
  - `GzipMiddleware` (`app/middleware/gzip.py`): Compresses responses > 1KB.
  - `RateLimitMiddleware` (`app/middleware/rate_limit.py`): Enforces 100 requests/minute.
  - `LifespanMiddleware` (`app/middleware/lifespan.py`): Handles ASGI lifespan events.

**Why This Stack?**
- Quart’s async capabilities support high-concurrency workloads.
- SQLAlchemy’s async ORM ensures efficient database queries.
- Hypercorn integrates seamlessly with Quart for ASGI compliance.
- Middleware enhances performance (Gzip), security (rate limiting), and reliability (lifespan handling).

## Assumptions Made

- **Database**: PostgreSQL for production, SQLite for testing (in-memory database in `tests/test_metrics.py`).
- **Data Scale**: Handles 10 warehouses, 200 agents, ~12,000 orders, as per simulated test data.
- **Allocation**:
  - Orders are assigned to agents in the same warehouse.
  - Haversine distance determines proximity-based assignments.
  - Agents must check in daily to be eligible.
- **Rate Limiting**: In-memory storage (`defaultdict`) for testing; production may require Redis.
- **Security**: JWT tokens (`HS256`, configurable expiration) for protected endpoints.
- **Scheduling**: Allocation runs daily at 07:00 AM local time.

## Key Metrics and Outputs

The allocation service (`app/services/allocation_service.py`) tracks:
- **Agent Utilization**: Percentage of checked-in agents assigned orders.
  - Example: 180/200 agents assigned → 90% utilization.
- **Deferred Orders**: Orders unassigned due to no available agents or warehouse mismatches.
  - Example: 500/12,000 orders deferred → ~4.17% deferred rate.
- **Total Cost**: Sum of Haversine distances for assignments (delivery cost).
  - Example: 15,000 km for 11,500 assignments.
- **Assignments Created**: Number of order-agent assignments.
  - Example: 11,500 assignments.

Sample `/orders/allocate` response:
```json
{
  "message": "Order allocation completed",
  "assignments_created": 11500,
  "total_cost": 15000.0,
  "deferred_orders": 500
}
```

## Screenshots

1. **Server Startup Logs**
   <img width="895" height="240" alt="Screenshot 2025-08-23 182909" src="https://github.com/user-attachments/assets/38d524db-f1da-4000-b059-4236dd0e6bfe" />

2. **APIs**
   *Sign API*
<img width="1067" height="463" alt="image" src="https://github.com/user-attachments/assets/558dd036-5fca-4d86-bc60-4a001d82cdff" />

   *Login API*
   <img width="1048" height="507" alt="image" src="https://github.com/user-attachments/assets/a328d189-38a0-48eb-8a2b-33ca06d64643" />

   *Create Warehouse*
   <img width="1056" height="363" alt="image" src="https://github.com/user-attachments/assets/72c180a5-cb6f-434a-96dd-557059c5dbce" />

   *Fetch Warehouse*
   <img width="1064" height="382" alt="image" src="https://github.com/user-attachments/assets/788e65b4-f274-4f6d-8723-1f88c9e6fc31" />

   *Create Agents*
   <img width="1058" height="295" alt="image" src="https://github.com/user-attachments/assets/7faac195-aad1-4490-a095-084bcc982c5c" />

   *Agent CheckIn*
   <img width="1056" height="318" alt="image" src="https://github.com/user-attachments/assets/f06e0785-54df-4548-acfd-8dd10a14589f" />

   *Fetch CheckIn Agents*
   <img width="1056" height="379" alt="image" src="https://github.com/user-attachments/assets/125e0810-e55f-41ab-96fe-81c5f7240cd1" />

   *Create Order*
   <img width="1061" height="319" alt="image" src="https://github.com/user-attachments/assets/75ee9fba-ce21-4f6c-ad4e-1652a5a77b60" />

   *Auto Allocate Order to Agent*
   <img width="1060" height="445" alt="image" src="https://github.com/user-attachments/assets/500bb399-ca1d-4d36-b93e-bcb8cabef018" />

   *Fetch Agent Assignment*
   <img width="1062" height="465" alt="image" src="https://github.com/user-attachments/assets/31f35af3-3e73-4a52-9d56-09d32dac4367" />

   
## Project Structure

```
delivery-management-system/
├── app/
│   ├── auth/
│   │   ├── models.py          # Authentication models
│   │   ├── routes.py          # Authentication routes
│   │   ├── utils.py           # Authentication utilities
│   │   └── __init__.py
│   ├── config/
│   │   ├── settings.py        # Application settings
│   │   └── __init__.py
│   ├── core/
│   │   ├── db_config.py       # Database configuration
│   │   ├── jwt.py             # JWT configuration
│   │   └── __init__.py
│   ├── middleware/
│   │   ├── gzip.py            # Gzip compression middleware
│   │   ├── lifespan.py        # ASGI lifespan event handling
│   │   ├── logger.py          # Logging setup
│   │   ├── rate_limit.py      # Rate limiting middleware
│   │   └── __init__.py
│   ├── models/
│   │   ├── agent.py           # Agent model
│   │   ├── assignment.py      # Assignment model
│   │   ├── base_model.py      # SQLAlchemy base model
│   │   ├── order.py           # Order model
│   │   ├── user.py            # User model
│   │   ├── warehouse.py       # Warehouse model
│   │   └── __init__.py
│   ├── routes/
│   │   ├── agents_routes.py   # Agent routes
│   │   ├── assignments_routes.py # Assignment routes
│   │   ├── auth.py            # Authentication routes
│   │   ├── orders_routes.py   # Order routes
│   │   ├── warehouse_routes.py # Warehouse routes
│   │   └── __init__.py
│   ├── services/
│   │   ├── agents_service.py  # Agent service
│   │   ├── allocation_service.py # Allocation service
│   │   ├── auth.py            # Authentication service
│   │   ├── order_service.py   # Order service
│   │   ├── warehouse_service.py # Warehouse service
│   │   └── __init__.py
│   ├── main.py                # Main application entry point
│   └── __init__.py
├── tests/
│   ├── test_metrics.py        # Test suite
│   └── __init__.py
├── .env                       # Environment variables
├── .env.example               # Example environment variables
├── .gitignore                 # Git ignore file
├── main.py                    # Entry point (optional, if used)
├── requirements.txt           # Dependencies
└── README.md                
```
