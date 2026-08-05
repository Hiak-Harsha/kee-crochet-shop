import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
from app.core.rate_limiter import RateLimitingMiddleware
from app.api.routes import auth, products, cart, orders, ai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure static uploads directory is created before static files are mounted at import time
os.makedirs("static/uploads", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Security checks
    if settings.ENVIRONMENT == "production":
        if settings.SECRET_KEY == "cozy_crochet_yarn_secret_key_1234567890_change_me_in_prod":
            logger.critical("CRITICAL SECURITY WARNING: Default SECRET_KEY is active in production environment! Please set a unique SECRET_KEY environment variable.")

    # Ensure all models are imported so they are registered on Base.metadata
    from app.models.user import User, AIChatSession, AIChatMessage, OTPCode, CustomRequest
    from app.models.product import Category, Product, ProductVariant, ProductReview
    from app.models.cart import Cart, CartItem
    from app.models.order import Order, OrderItem

    # Startup Database Table Creation (ideal for mock dev/sandbox mode)
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        # SQLite or PostgreSQL table creation
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")
    
    # Auto-seed database if empty
    from app.core.seed import seed_data
    from app.core.database import async_session
    async with async_session() as session:
        try:
            await seed_data(session)
        except Exception as e:
            logger.error(f"Failed to seed database: {e}")
            
    yield
    logger.info("Shutting down database connection...")
    await engine.dispose()


is_prod = settings.ENVIRONMENT == "production"
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI Powered Commerce Platform Backend for Kee Crochet",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://kee-crochet-shop.vercel.app",
]

# Add Vercel deployment URLs
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)
    if frontend_url.endswith("/"):
        origins.append(frontend_url[:-1])

# Allow all Vercel preview deployments for this project
vercel_project = os.getenv("VERCEL_PROJECT_URL")
if vercel_project:
    origins.append(f"https://{vercel_project}")

if settings.ENVIRONMENT == "production":
    prod_origin = os.getenv("FRONTEND_URL")
    if prod_origin:
        origins.append(prod_origin)
        if prod_origin.endswith("/"):
            origins.append(prod_origin[:-1])
    else:
        origins.append("https://keecrochet.com")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    return response


# Rate Limiting Middleware for sensitive auth and AI endpoints
app.add_middleware(
    RateLimitingMiddleware,
    limit_sec=60,
    max_requests=15
)

# Mount Static Files for product image uploads
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(cart.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(ai.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }
