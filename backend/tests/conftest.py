import asyncio
import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set testing environment before importing application
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_crochet.db"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-123456"
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_key"
os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_secret"

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.main import app
from app.models.user import User, UserRole
from app.models.product import Category, Product, ProductVariant
from app.models.order import Coupon, CouponType

TEST_DB_FILE = "./test_crochet.db"
test_engine = create_async_engine(
    "sqlite+aiosqlite:///./test_crochet.db",
    echo=False,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Setup clean schema before tests and teardown afterwards."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest_asyncio.fixture
async def db_session():
    """Provide isolated transaction per test."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client():
    """HTTP client with test database dependency override."""
    async def override_get_db():
        async with TestingSessionLocal() as session:
            try:
                yield session
            finally:
                pass

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test customer user."""
    user = User(
        email=f"customer_{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("SecretPassword123!"),
        full_name="Priya Sharma",
        phone=f"98{uuid.uuid4().int % 100000000:08d}",
        role=UserRole.customer,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create test admin user."""
    admin = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@keecrochet.com",
        hashed_password=hash_password("AdminMasterKey123!"),
        full_name="Harsha Kee",
        phone=f"99{uuid.uuid4().int % 100000000:08d}",
        role=UserRole.admin,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def user_token(test_user: User) -> str:
    """Generate access token for test customer."""
    return create_access_token(str(test_user.id), role="customer")


@pytest.fixture
def admin_token(test_admin: User) -> str:
    """Generate access token for test admin."""
    return create_access_token(str(test_admin.id), role="admin")


@pytest_asyncio.fixture
async def sample_product(db_session: AsyncSession) -> Product:
    """Create a sample product with 5 stock."""
    prod = Product(
        title="Lavender Bloom Bouquet",
        slug=f"lavender-bloom-{uuid.uuid4().hex[:6]}",
        description="Handcrafted soft lavender bouquet",
        price=650.0,
        stock=5,
        is_active=True,
        is_featured=True,
        images=["/images/lavender.webp"],
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest_asyncio.fixture
async def sample_coupon(db_session: AsyncSession) -> Coupon:
    """Create a sample 15% discount coupon."""
    coupon = Coupon(
        code="TEST15",
        description="15% discount for testing",
        type=CouponType.percentage,
        value=15.0,
        minimum_order_value=500.0,
        maximum_discount=200.0,
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)
    return coupon
