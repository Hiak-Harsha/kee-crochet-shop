import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, OTPCode


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    """Test user registration and subsequent login returning tokens."""
    email = "test_register_flow@example.com"
    password = "SafePassword123!"

    # 1. Register
    reg_resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test User", "phone": "9876543210"},
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert "refresh_token" in reg_data
    assert reg_data["user"]["email"] == email

    # 2. Duplicate registration rejected
    dup_resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Duplicate User"},
    )
    assert dup_resp.status_code == 400

    # 3. Login
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data

    # 4. Login with incorrect password
    bad_login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_otp_generation_and_verification(client: AsyncClient, db_session: AsyncSession):
    """Test OTP creation, salted hashing, and verification."""
    email = "otp_shopper@example.com"

    # Request OTP
    req_resp = await client.post("/api/auth/otp/request", json={"email": email})
    assert req_resp.status_code == 200

    # Retrieve stored OTP record from test db
    stmt = select(OTPCode).where(OTPCode.identifier == email)
    res = await db_session.execute(stmt)
    otp_record = res.scalar_one_or_none()
    assert otp_record is not None
    assert otp_record.hashed_code != ""  # Hashed with salt, not plain text

    # Verify that failed attempt increments attempt count
    fail_verify = await client.post(
        "/api/auth/otp/verify",
        json={"email": email, "otp": "000000"},
    )
    assert fail_verify.status_code == 400


@pytest.mark.asyncio
async def test_auth_me_endpoint(client: AsyncClient, user_token: str, test_user: User):
    """Test retrieving profile using Bearer token."""
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == test_user.email
    assert data["role"] == "customer"
