import os
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine
from app.core.rate_limiter import RateLimitingMiddleware
from app.api.routes import auth, products, cart, orders, ai, admin

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
)
logger = logging.getLogger("keecrochet")

# Ensure static uploads directory is created before static files are mounted at import time
os.makedirs("static/uploads", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} in '{settings.ENVIRONMENT}' environment...")
    
    # Validate production configuration fail-fast
    settings.validate_production_configuration()

    if settings.ENVIRONMENT != "production":
        # In non-production, ensure tables are available and seed initial development data
        logger.info("Non-production environment: Checking database seeding...")
        from app.core.seed import seed_data
        from app.core.database import async_session
        async with async_session() as session:
            try:
                await seed_data(session)
            except Exception as e:
                logger.error(f"Failed to seed development database: {e}")
    else:
        logger.info("Production environment: Schema is strictly managed by Alembic migrations. Auto-seeding disabled.")

    yield
    logger.info("Shutting down database connection...")
    await engine.dispose()


is_prod = settings.ENVIRONMENT == "production"
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Ready AI E-Commerce Platform for Kee Crochet",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)

# Request ID and Security Headers Middleware
@app.middleware("http")
async def security_and_request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if is_prod:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
    return response


# CORS configuration: strict explicit origins in production, preview regex only in dev
allowed_origins = settings.get_allowed_origins()
origin_regex = None if is_prod else r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)

# Rate Limiting Middleware for sensitive auth, order, and AI endpoints
app.add_middleware(
    RateLimitingMiddleware,
    limit_sec=60,
    max_requests=25
)

# Mount Static Files for product image uploads (fallback in dev/local)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(cart.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "2.0.0",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/live")
async def health_live():
    """Liveness probe to check if the HTTP service process is running."""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe verifying operational status of essential backing dependencies (DB)."""
    from sqlalchemy import text
    from app.core.database import async_session

    db_healthy = False
    try:
        async with async_session() as session:
            res = await session.execute(text("SELECT 1"))
            if res.scalar() == 1:
                db_healthy = True
    except Exception as e:
        logger.error(f"Health check DB probe failure: {e}")

    if not db_healthy:
        raise HTTPException(
            status_code=503,
            detail={"status": "unready", "database": "disconnected"}
        )

    return {
        "status": "ready",
        "database": "connected",
        "environment": settings.ENVIRONMENT,
    }
