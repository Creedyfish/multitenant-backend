# Multitenant Backend

A FastAPI-based backend application with authentication and user management capabilities.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Authentication**: Token-based authentication system
- **Redis Integration**: Redis support for caching and session management
- **Modular Architecture**: Clean separation of concerns with routers, endpoints, and services
- **API Versioning**: Built-in API versioning (v1)

## Project Structure

```
multitenant-backend/
├── app/
│   ├── main.py              # Application entry point
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # API v1 router
│   │       └── endpoints/   # API endpoints
│   │           ├── auth.py  # Authentication endpoints
│   │           ├── users.py # User management endpoints
│   │           └── items.py # Item endpoints
│   ├── core/
│   │   ├── config.py        # Configuration settings
│   │   ├── dependencies.py  # Dependency injection
│   │   └── security.py      # Security utilities
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   └── services/            # Business logic services
└── requirements.txt         # Python dependencies
```

## Prerequisites

- Python 3.8+
- Redis server
- Virtual environment (recommended)

## Installation

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

4. **Start Redis server**
   ```bash
   redis-server
   ```
   Or use Docker:
   ```bash
   docker run -d -p 6379:6379 redis
   ```

## Running the Application

Start the development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000/api/v1`

## API Documentation

Once the application is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication

- `POST /api/v1/auth/token` - Get access token

### Users

- `GET /api/v1/users/me` - Get current user information

### Items

- `GET /api/v1/items/` - Get items list

## Configuration

Key configuration settings can be found in [app/core/config.py](app/core/config.py):

- `API_PREFIX`: API prefix path (default: `/api`)
- `API_VERSION`: API version (default: `v1`)
- `PROJECT_NAME`: Project name
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiration time (default: 15 minutes)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiration time (default: 7 days)

## Development

## Notes

- I used sync SQLAlchemy with FastAPI's threadpool handling. I'm aware of the async alternative with asyncpg and AsyncSession and would migrate to that if the app needed to handle high concurrency."

### Adding New Endpoints

1. Create a new endpoint file in `app/api/v1/endpoints/`
2. Define your router and endpoints
3. Register the router in `app/api/v1/router.py`

### Adding Dependencies

```bash
pip install <package-name>
pip freeze > requirements.txt
```

## Redis Configuration

The application connects to Redis at `0.0.0.0:6379` by default. To modify the connection:

Edit the Redis client initialization in [app/main.py](app/main.py):

```python
redis_client = redis.StrictRedis(
    host="your-redis-host",
    port=6379,
    db=0,
    decode_responses=True
)
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
