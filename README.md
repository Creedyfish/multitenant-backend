# Multitenant Backend

A comprehensive FastAPI-based multitenant backend application for inventory and supply chain management. Designed with enterprise-grade security, tenant isolation, and role-based access control.

## Features

- **Multi-Tenancy Architecture**: Built-in support for multiple organizations with complete data isolation
- **Role-Based Access Control (RBAC)**: Three-tier permission system (Admin, Manager, Staff)
- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **Redis Integration**: Caching, session management, and rate limiting
- **PostgreSQL Database**: Robust data persistence with Alembic migrations
- **Inventory Management**: Complete stock management system with movement tracking
- **Purchase Request Workflow**: Draft, Submit, Approve, and Reject workflow
- **Background Jobs**: Scheduled tasks for cleanup and weekly reports
- **Audit Logging**: Complete audit trail for all operations
- **Rate Limiting**: API rate limiting with SlowAPI
- **Error Tracking**: Sentry integration for error monitoring
- **Email Service**: Integration with Resend for email notifications
- **Comprehensive API**: RESTful API with full CRUD operations
- **API Versioning**: Built-in API versioning (v1)
- **API Documentation**: Auto-generated Swagger UI and ReDoc

## Project Structure

```
multitenant-backend/
├── app/
│   ├── main.py                    # Application entry point with scheduler setup
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          # API v1 router
│   │       └── endpoints/         # API endpoints
│   │           ├── auth.py        # Authentication & authorization
│   │           ├── users.py       # User management
│   │           ├── organizations.py # Organization management
│   │           ├── products.py    # Product catalog
│   │           ├── purchase_requests.py # Purchase request workflow
│   │           ├── stock_movements.py # Stock/inventory tracking
│   │           ├── suppliers.py   # Supplier management
│   │           ├── warehouses.py  # Warehouse management
│   │           ├── audit_logs.py  # Audit trail
│   │           └── events.py      # Event publishing
│   ├── core/
│   │   ├── config.py              # Configuration & environment settings
│   │   ├── dependencies.py        # FastAPI dependency injection
│   │   ├── security.py            # Security utilities & JWT handling
│   │   ├── limiter.py             # Rate limiting configuration
│   │   ├── logger.py              # Centralized logging setup
│   │   └── redis.py               # Redis client setup
│   ├── middleware/
│   │   ├── tenant.py              # Multi-tenant context extraction
│   │   └── rbac.py                # Role-based access control
│   ├── models/                    # SQLAlchemy database models
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── product.py
│   │   ├── purchase_request.py
│   │   ├── stock_movement.py
│   │   ├── supplier.py
│   │   ├── warehouse.py
│   │   ├── audit_log.py
│   │   └── enums.py               # Enum definitions (Roles, Status)
│   ├── schemas/                   # Pydantic schemas for API validation
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── product.py
│   │   ├── purchase_request.py
│   │   ├── stock_movement.py
│   │   ├── supplier.py
│   │   └── warehouse.py
│   ├── services/                  # Business logic layer
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── product.py
│   │   ├── purchase_request.py
│   │   ├── stock_movement.py
│   │   ├── supplier.py
│   │   ├── warehouse.py
│   │   ├── audit_log.py
│   │   ├── email.py               # Email notification service
│   │   ├── event_publisher.py     # Event publishing
│   │   └── refresh_token.py       # Token refresh logic
│   └── jobs/                      # Background jobs
│       ├── cleanup.py             # Scheduled cleanup tasks
│       ├── low_stock.py           # Low stock alerts
│       └── weekly_report.py       # Weekly report generation
├── alembic/                       # Database migrations
│   ├── versions/
│   │   └── e1733bef0967_initial.py
│   ├── env.py
│   ├── script.py.mako
│   └── alembic.ini
├── tests/                         # Comprehensive test suite
│   ├── test_auth.py
│   ├── test_rbac.py
│   ├── test_tenant_isolation.py
│   ├── test_crud.py
│   ├── test_stock_operation.py
│   ├── test_purchase_request.py
│   ├── test_audit_log.py
│   ├── test_check_low_stock.py
│   ├── test_scheduled_cleanup.py
│   ├── test_weekly_report.py
│   └── conftest.py
├── docker-compose.yml             # Docker services configuration
├── Dockerfile                     # Application container
├── requirements.txt               # Python dependencies
├── alembic.ini                    # Alembic configuration
├── pytest.ini                     # pytest configuration
└── README.md                      # This file
```

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (for containerized deployment)
- Virtual environment (recommended)

## Installation

### Manual Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd multitenant-backend
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root with the following variables:

   ```env
   # Core Settings
   SECRET_KEY=your-secret-key-here
   ENV=development
   DEBUG=true

   # Database
   DATABASE_URL=postgresql://user:password@localhost:5432/multitenant_db
   DATABASE_URL_TESTING=postgresql://user:password@localhost:5432/multitenant_test

   # Redis
   REDIS_URL=redis://localhost:6379/0

   # External Services
   SENTRY_DSN=https://your-sentry-dsn
   RESEND_API=re_your_resend_api_key

   # JWT Configuration
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=15
   REFRESH_TOKEN_EXPIRE_DAYS=7

   # API Configuration
   PROJECT_NAME=Multitenant Backend API
   ```

5. **Set up PostgreSQL database**

   ```bash
   # Create database
   createdb multitenant_db
   createdb multitenant_test
   ```

6. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

7. **Start Redis server**

   ```bash
   redis-server
   ```

   Or use Docker:

   ```bash
   docker run -d -p 6379:6379 --name redis redis:alpine
   ```

### Docker Setup

1. **Build and run with Docker Compose**

   ```bash
   docker-compose up --build
   ```

   This will start:
   - FastAPI application (port 8000)
   - Redis (port 6379)

2. **Run database migrations in container**

   ```bash
   docker-compose exec api alembic upgrade head
   ```

## Running the Application

### Development Mode

Start the development server with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the application is running, you can access:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **Health Check**: GET http://localhost:8000/health-check

## API Endpoints

All endpoints are prefixed with `/api/v1`

### Authentication

- `POST /auth/token` - Get access token (login)
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (invalidate token)

### Users Management

- `GET /users/me` - Get current user information
- `GET /users` - List all users (Admin only)
- `GET /users/{user_id}` - Get user details
- `POST /users` - Create new user (Admin only)
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user (Admin only)

### Organizations

- `GET /organizations` - List organizations
- `GET /organizations/{org_id}` - Get organization details
- `POST /organizations` - Create new organization
- `PUT /organizations/{org_id}` - Update organization
- `DELETE /organizations/{org_id}` - Delete organization (Admin only)

### Products

- `GET /products` - List products
- `GET /products/{product_id}` - Get product details
- `POST /products` - Create product (Manager+)
- `PUT /products/{product_id}` - Update product (Manager+)
- `DELETE /products/{product_id}` - Delete product (Admin only)

### Suppliers

- `GET /suppliers` - List suppliers
- `GET /suppliers/{supplier_id}` - Get supplier details
- `POST /suppliers` - Create supplier (Manager+)
- `PUT /suppliers/{supplier_id}` - Update supplier (Manager+)
- `DELETE /suppliers/{supplier_id}` - Delete supplier (Admin only)

### Warehouses

- `GET /warehouses` - List warehouses
- `GET /warehouses/{warehouse_id}` - Get warehouse details
- `POST /warehouses` - Create warehouse (Manager+)
- `PUT /warehouses/{warehouse_id}` - Update warehouse (Manager+)
- `DELETE /warehouses/{warehouse_id}` - Delete warehouse (Admin only)

### Stock Management

- `GET /stock-movements` - List stock movements
- `GET /stock-movements/{movement_id}` - Get movement details
- `POST /stock-movements` - Record stock movement (Staff+)
- `GET /stock-movements/low-stock` - Get low stock alerts

### Purchase Requests

- `GET /purchase-requests` - List purchase requests
- `GET /purchase-requests/{request_id}` - Get request details
- `POST /purchase-requests` - Create purchase request (Staff+)
- `PUT /purchase-requests/{request_id}` - Update request
- `POST /purchase-requests/{request_id}/submit` - Submit for approval
- `POST /purchase-requests/{request_id}/approve` - Approve request (Manager+)
- `POST /purchase-requests/{request_id}/reject` - Reject request (Manager+)

### Audit Logs

- `GET /audit-logs` - List audit logs (Admin+)
- `GET /audit-logs/{log_id}` - Get audit log details

### Events

- `GET /events` - List events
- `GET /events/{event_id}` - Get event details

## Authentication & Security

### JWT Authentication

The application uses JWT (JSON Web Tokens) for authentication:

1. **Login**: Send credentials to `POST /auth/token` to get an access token
2. **Access Token**: Valid for 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
3. **Refresh Token**: Valid for 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
4. **Token Refresh**: Use the refresh token to get a new access token

### Password Security

Passwords are hashed using Argon2 via the `pwdlib` library for enhanced security.

### Rate Limiting

The API enforces rate limiting using SlowAPI to prevent abuse. Rate limit exceeded responses return HTTP 429 status.

## Multi-Tenancy

The application supports complete multi-tenant data isolation:

- **Tenant Context**: Automatically extracts tenant ID from:
  - Subdomain (e.g., `acme.example.com` → tenant: `acme`)
  - HTTP header `x-tenant-id`
- **Organization ID**: Each user belongs to an organization; all data is scoped to that org
- **Data Isolation**: Queries automatically filter by user's organization

## Role-Based Access Control (RBAC)

Three-tier role system controls access to protected endpoints:

- **Admin**: Full system access, manage users and organizations
- **Manager**: Can create/update resources, approve requests
- **Staff**: Basic operations, can create purchase requests

Example middleware usage:

```python
from app.middleware.rbac import require_role
from app.models.enums import RoleEnum

@router.post("/approve")
def approve_request(required_role: require_role([RoleEnum.ADMIN, RoleEnum.MANAGER])):
    # Only admins and managers can access
    pass
```

## Database Migrations

Use Alembic to manage database schema changes:

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new column"

# Apply all pending migrations
alembic upgrade head

# Revert one migration
alembic downgrade -1

# View migration history
alembic current
alembic history
```

## Background Jobs

The application includes scheduled background tasks:

- **Weekly Report**: Runs every Sunday at 00:00 UTC
- **Cleanup Job**: Runs daily at 02:00 UTC, removes draft purchase requests older than 30 days
- **Low Stock Alerts**: Monitors inventory levels and alerts when stock is low

Jobs are managed by APScheduler in the application lifespan events.

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_user_login

# Verbose output
pytest -v
```

### Test Coverage

The test suite covers:

- Authentication and authorization
- Multi-tenant isolation
- RBAC enforcement
- CRUD operations
- Stock movement operations
- Purchase request workflows
- Audit logging
- Scheduled cleanup
- Low stock checks
- Weekly reports

## Configuration

Key configuration settings in [app/core/config.py](app/core/config.py):

- `SECRET_KEY`: JWT signing key
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token TTL (default: 15)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token TTL (default: 7)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SENTRY_DSN`: Error tracking configuration
- `RESEND_API`: Email service API key
- `ENV`: Environment (development, testing, production)

## Development

### Project Structure Best Practices

- **Models**: SQLAlchemy ORM models in `app/models/`
- **Schemas**: Pydantic validation schemas in `app/schemas/`
- **Services**: Business logic in `app/services/`
- **Endpoints**: HTTP handlers in `app/api/v1/endpoints/`
- **Middleware**: Cross-cutting concerns in `app/middleware/`

### Adding New Features

1. **Create database model** in `app/models/`
2. **Create Pydantic schema** in `app/schemas/`
3. **Implement service logic** in `app/services/`
4. **Create API endpoints** in `app/api/v1/endpoints/`
5. **Run migrations**: `alembic revision --autogenerate -m "Add feature"`
6. **Add tests** in `tests/`

### Adding Dependencies

```bash
# Add package
pip install <package-name>

# Update requirements
pip freeze > requirements.txt
```

## Logging

Structured logging is configured using `structlog` with Sentry integration. All application events are logged with context information for debugging and monitoring.

## Email Service

Email notifications are sent via Resend API. Configure your Resend API key in the `.env` file as `RESEND_API`.

## Error Handling

The application uses Sentry for error tracking and monitoring:

- Errors are automatically reported to Sentry
- Development/Testing: Set traces_sample_rate to 1.0
- Production: Set to 0.1 for 10% sampling

## Docker Deployment

### Build Image

```bash
docker build -t multitenant-backend:latest .
```

### Run Container

```bash
docker run -p 8000:8000 --env-file .env multitenant-backend:latest
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Ensure database exists: `psql -l | grep multitenant`

### Redis Connection Issues

- Verify Redis is running: `redis-cli ping`
- Check `REDIS_URL` in `.env`
- Default: `redis://localhost:6379`

### Migration Issues

- Reset migrations: `alembic upgrade base`
- View current state: `alembic current`
- Check migration history: `alembic history`

### Authentication Issues

- Verify `SECRET_KEY` is set
- Check JWT token expiration
- Ensure user exists and is active

## Performance Considerations

- **Database Indexes**: Key fields (user_id, org_id) are indexed
- **Connection Pooling**: SQLAlchemy manages database connection pool
- **Caching**: Redis caches frequently accessed data
- **Rate Limiting**: Prevents API abuse
- **Async Jobs**: Background tasks don't block API requests

## Security Considerations

- Always use HTTPS in production
- Rotate `SECRET_KEY` regularly
- Keep dependencies updated: `pip list --outdated`
- Use strong database passwords
- Enable Sentry for error tracking
- Review audit logs regularly
- Implement API key authentication for service-to-service calls

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)

## License

This project is licensed under a **Custom Dual-License Model**:

### Personal Use (Free)

- You may freely use, modify, and distribute this code for personal, educational, and non-commercial purposes.

### Commercial Use (Requires Permission)

- If you use this code for commercial purposes, generate revenue, or use it in a business context, you must:
  1. Contact the project owner for a commercial license agreement
  2. Negotiate terms, which may include revenue sharing or licensing fees
  3. Obtain written permission before deploying commercially

For licensing inquiries, please open an issue or contact the project maintainer.

**Note:** This is a custom license. For clarity on your specific use case, please reach out before using this code commercially.

## Contributing

We welcome contributions! Here's how you can help:

### Setting Up Development Environment

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate it: `source .venv/bin/activate` (Linux/Mac) or `.venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.sample` to `.env` and configure your environment
6. Run migrations: `alembic upgrade head`
7. Start the server: `uvicorn app.main:app --reload`

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write docstrings for classes and functions
- Run tests before submitting: `pytest`
- Use meaningful commit messages

### Testing

- Write tests for new features
- Ensure all tests pass: `pytest`
- Aim for >80% code coverage
- Run linting: `pylint app/`

### Submitting Changes

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and commit with clear messages
3. Submit a pull request with:
   - Description of changes
   - Why the change is needed
   - Any related issues (#123)
4. Respond to review feedback
5. Once approved, your PR will be merged

### Reporting Issues

- Check existing issues first
- Provide clear description and reproduction steps
- Include environment details (Python version, OS, etc.)
- Attach error logs or screenshots if relevant

### License Agreement

By contributing, you agree that your contributions will be licensed under the same license as the project.

## Support

For issues and questions, please open an issue on the project repository.
