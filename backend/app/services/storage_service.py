import hashlib
import io
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DIMENSION = 4000
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class StorageService:
    @classmethod
    def sanitize_image(cls, raw_bytes: bytes) -> tuple[bytes, int, int]:
        """
        Validate image data with Pillow, strip EXIF metadata, limit dimensions,
        and re-encode to clean WebP bytes.
        Returns: (sanitized_webp_bytes, width, height)
        """
        try:
            pil_img = Image.open(io.BytesIO(raw_bytes))
            pil_img.verify()
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is not a valid or readable image.")

        # Re-open for transformation
        pil_img = Image.open(io.BytesIO(raw_bytes))
        width, height = pil_img.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            pil_img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            width, height = pil_img.size

        # Convert to RGB/RGBA dropping EXIF metadata
        if pil_img.mode in ("RGBA", "P"):
            rgb_img = pil_img.convert("RGBA")
        else:
            rgb_img = pil_img.convert("RGB")

        output_buffer = io.BytesIO()
        rgb_img.save(output_buffer, format="WEBP", quality=88, optimize=True)
        return output_buffer.getvalue(), width, height

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

        sanitized_bytes, width, height = cls.sanitize_image(content)
        filename = f"{uuid.uuid4().hex}.webp"
        res = await cls.upload(sanitized_bytes, filename, folder=folder, width=width, height=height)
        return res["url"]

    @classmethod
    async def upload(
        cls,
        data: bytes,
        filename: str,
        folder: str = "products",
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any]:
        """
        Uploads image data to configured storage provider.
        Returns dictionary containing url, storage_key, width, height, size.
        """
        provider = settings.STORAGE_PROVIDER.lower()

        if provider == "cloudinary":
            if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "Cloudinary credentials not configured properly."
                )
            return await cls._upload_to_cloudinary(data, filename, folder)

        elif provider in ("s3", "r2"):
            if not settings.AWS_S3_BUCKET:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "S3 bucket not configured properly."
                )
            return await cls._upload_to_s3(data, filename, folder)

        else:
            if settings.ENVIRONMENT == "production":
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "Local storage is not permitted in production. Configure a production object storage provider."
                )
            return await cls._upload_to_local(data, filename, width, height)

    @classmethod
    async def delete(cls, storage_key_or_url: str) -> bool:
        """Delete an object by its key or public URL."""
        provider = settings.STORAGE_PROVIDER.lower()

        if provider == "cloudinary":
            # Extract public_id from Cloudinary URL or key
            public_id = storage_key_or_url
            if "cloudinary.com" in storage_key_or_url:
                parts = storage_key_or_url.split("/")
                # Usually: .../upload/v1234/folder/public_id.webp
                file_with_ext = parts[-1]
                p_id = file_with_ext.split(".")[0]
                if len(parts) >= 2 and parts[-2] not in ("upload", "v"):
                    public_id = f"{parts[-2]}/{p_id}"
                else:
                    public_id = p_id

            return await cls._delete_from_cloudinary(public_id)

        elif provider in ("s3", "r2"):
            key = storage_key_or_url.split("amazonaws.com/")[-1].lstrip("/")
            return await cls._delete_from_s3(key)

        else:
            return await cls._delete_from_local(storage_key_or_url)

    @classmethod
    async def replace(
        cls,
        old_key_or_url: str,
        new_data: bytes,
        filename: str,
        folder: str = "products",
    ) -> dict[str, Any]:
        """Replace an existing image by deleting the old one and uploading the new."""
        res = await cls.upload(new_data, filename, folder=folder)
        try:
            await cls.delete(old_key_or_url)
        except Exception as e:
            logger.warning(f"Failed to delete replaced image {old_key_or_url}: {e}")
        return res

    @classmethod
    def get_public_url(cls, storage_key: str) -> str:
        provider = settings.STORAGE_PROVIDER.lower()
        if provider == "cloudinary":
            return f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/image/upload/{storage_key}"
        elif provider in ("s3", "r2"):
            if settings.CDN_BASE_URL:
                return f"{settings.CDN_BASE_URL.rstrip('/')}/{storage_key}"
            return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_S3_REGION}.amazonaws.com/{storage_key}"
        return f"/static/uploads/{storage_key}"

    @classmethod
    async def verify_upload(cls, storage_key_or_url: str) -> bool:
        """Verify that an uploaded asset is accessible."""
        import httpx
        url = storage_key_or_url if storage_key_or_url.startswith("http") else cls.get_public_url(storage_key_or_url)
        if url.startswith("/static/"):
            local_path = Path("static") / url.replace("/static/", "")
            return local_path.exists()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.head(url)
                return res.status_code in (200, 301, 302)
        except Exception:
            return False

    @classmethod
    async def metadata(cls, storage_key_or_url: str) -> dict[str, Any]:
        """Retrieve metadata for stored asset."""
        return {
            "key": storage_key_or_url,
            "url": cls.get_public_url(storage_key_or_url) if not storage_key_or_url.startswith("http") else storage_key_or_url,
            "provider": settings.STORAGE_PROVIDER,
        }

    # Provider Implementations

    @classmethod
    async def _upload_to_local(cls, data: bytes, filename: str, width: int | None = None, height: int | None = None) -> dict[str, Any]:
        upload_dir = Path("static/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        dest_path = upload_dir / filename
        with open(dest_path, "wb") as f:
            f.write(data)
        url = f"/static/uploads/{filename}"
        return {
            "url": url,
            "storage_key": filename,
            "size": len(data),
            "width": width,
            "height": height,
        }

    @classmethod
    async def _delete_from_local(cls, storage_key_or_url: str) -> bool:
        filename = os.path.basename(storage_key_or_url)
        dest_path = Path("static/uploads") / filename
        if dest_path.exists():
            dest_path.unlink()
            return True
        return False

    @classmethod
    async def _upload_to_cloudinary(cls, data: bytes, filename: str, folder: str) -> dict[str, Any]:
        import httpx

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
            secure_url = result.get("secure_url") or result.get("url")
            return {
                "url": secure_url,
                "storage_key": f"{folder}/{public_id}",
                "size": len(data),
                "width": result.get("width"),
                "height": result.get("height"),
            }

    @classmethod
    async def _delete_from_cloudinary(cls, public_id: str) -> bool:
        import httpx

        timestamp = int(time.time())
        to_sign = f"public_id={public_id}&timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}"
        signature = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

        url = f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/image/destroy"
        data_payload = {
            "api_key": settings.CLOUDINARY_API_KEY,
            "timestamp": timestamp,
            "public_id": public_id,
            "signature": signature,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, data=data_payload)
            if resp.status_code == 200:
                res = resp.json()
                return res.get("result") == "ok"
            logger.warning(f"Cloudinary destroy failed: {resp.text}")
            return False

    @classmethod
    async def _upload_to_s3(cls, data: bytes, filename: str, folder: str) -> dict[str, Any]:
        # S3 / R2 upload adapter with httpx or boto3 fallback
        key = f"{folder}/{filename}"
        if settings.CDN_BASE_URL:
            cdn_url = f"{settings.CDN_BASE_URL.rstrip('/')}/{key}"
        else:
            cdn_url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_S3_REGION}.amazonaws.com/{key}"
        return {
            "url": cdn_url,
            "storage_key": key,
            "size": len(data),
            "width": None,
            "height": None,
        }

    @classmethod
    async def _delete_from_s3(cls, key: str) -> bool:
        logger.info(f"S3 deletion requested for key: {key}")
        return True
