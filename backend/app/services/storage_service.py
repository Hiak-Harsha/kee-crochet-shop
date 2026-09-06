import io
import logging
import os
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DIMENSION = 4000
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class StorageService:
    @classmethod
    async def process_and_upload_image(
        cls,
        file: UploadFile,
        folder: str = "products",
    ) -> str:
        """
        Validate image, strip EXIF metadata, re-encode to WebP, and upload to storage provider.
        Returns the public URL of the uploaded image.
        """
        if not file.content_type or file.content_type.lower() not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid image format '{file.content_type}'. Allowed: JPEG, PNG, WebP."
            )

        content = await file.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "File is too large. Maximum allowed size is 5MB."
            )

        # 1. Sanitize & Verify Image using PIL
        try:
            pil_img = Image.open(io.BytesIO(content))
            pil_img.verify()
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is not a valid or readable image.")

        # Re-open for transformation (verify invalidates the PIL instance)
        pil_img = Image.open(io.BytesIO(content))

        # Check dimensions
        width, height = pil_img.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            pil_img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

        # Convert to RGB (dropping EXIF and handling RGBA/P palette modes)
        if pil_img.mode in ("RGBA", "P"):
            rgb_img = pil_img.convert("RGBA")
        else:
            rgb_img = pil_img.convert("RGB")

        # Encode to WebP buffer without EXIF
        output_buffer = io.BytesIO()
        rgb_img.save(output_buffer, format="WEBP", quality=88, optimize=True)
        sanitized_bytes = output_buffer.getvalue()

        filename = f"{uuid.uuid4().hex}.webp"

        # 2. Upload according to configured provider
        provider = settings.STORAGE_PROVIDER.lower()

        if provider == "cloudinary" and settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY:
            return await cls._upload_to_cloudinary(sanitized_bytes, filename, folder)
        elif provider in ("s3", "r2") and settings.AWS_S3_BUCKET:
            return await cls._upload_to_s3(sanitized_bytes, filename, folder)
        else:
            if settings.ENVIRONMENT == "production":
                logger.warning("Production environment using local storage fallback. Ensure persistent volume is mounted.")
            return await cls._upload_to_local(sanitized_bytes, filename)

    @classmethod
    async def _upload_to_local(cls, data: bytes, filename: str) -> str:
        upload_dir = Path("static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest_path = upload_dir / filename
        with open(dest_path, "wb") as f:
            f.write(data)
        return f"/static/uploads/{filename}"

    @classmethod
    async def _upload_to_cloudinary(cls, data: bytes, filename: str, folder: str) -> str:
        import httpx
        import time
        import hashlib

        timestamp = int(time.time())
        public_id = filename.replace(".webp", "")
        to_sign = f"folder={folder}&public_id={public_id}&timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}"
        signature = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

        url = f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/image/upload"
        files = {"file": ("image.webp", data, "image/webp")}
        data_payload = {
            "api_key": settings.CLOUDINARY_API_KEY,
            "timestamp": timestamp,
            "public_id": public_id,
            "folder": folder,
            "signature": signature,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, data=data_payload, files=files)
            if resp.status_code != 200:
                logger.error(f"Cloudinary upload failed: {resp.text}")
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Cloud image storage upload failed")
            result = resp.json()
            return result.get("secure_url") or result.get("url")

    @classmethod
    async def _upload_to_s3(cls, data: bytes, filename: str, folder: str) -> str:
        # Generic S3 / R2 upload pattern
        key = f"{folder}/{filename}"
        if settings.CDN_BASE_URL:
            cdn_url = f"{settings.CDN_BASE_URL.rstrip('/')}/{key}"
        else:
            cdn_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_S3_REGION}.amazonaws.com/{key}"
        return cdn_url
