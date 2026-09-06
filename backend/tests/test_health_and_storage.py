import io
import pytest
from httpx import AsyncClient
from PIL import Image
from fastapi import HTTPException

from app.core.config import settings
from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    # Liveness probe
    live_res = await client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    # Readiness probe
    ready_res = await client.get("/health/ready")
    assert ready_res.status_code == 200
    data = ready_res.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_storage_service_image_sanitization():
    # Create valid test image with Pillow
    img = Image.new("RGB", (200, 200), color=(255, 182, 193))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    raw_bytes = buf.getvalue()

    sanitized, width, height = StorageService.sanitize_image(raw_bytes)
    assert len(sanitized) > 0
    assert width == 200
    assert height == 200

    # Verify output is valid WebP
    out_img = Image.open(io.BytesIO(sanitized))
    assert out_img.format == "WEBP"


def test_storage_service_rejects_corrupted_data():
    corrupted_bytes = b"not-an-image-header-corrupt"
    with pytest.raises(HTTPException) as exc_info:
        StorageService.sanitize_image(corrupted_bytes)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_storage_service_rejects_local_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")

    with pytest.raises(HTTPException) as exc_info:
        await StorageService.upload(b"fake_data", "test.webp")
    assert exc_info.value.status_code == 500
    assert "not permitted in production" in exc_info.value.detail
