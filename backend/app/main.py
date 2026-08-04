import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import auth, products, cart, orders, ai

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI Powered Commerce Platform Backend for Kee Crochet",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev purposes, restrict in production environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
