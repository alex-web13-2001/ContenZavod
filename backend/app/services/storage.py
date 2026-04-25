"""MinIO storage service for ContenZavod.

Handles uploading images and other files to MinIO object storage.
"""

import io
from urllib.parse import urlparse

import httpx
import structlog
from minio import Minio
from minio.error import S3Error

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# ── MinIO client singleton ───────────────────────────────

_client: Minio | None = None


def get_minio_client() -> Minio:
    """Get or create MinIO client singleton."""
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        # Ensure bucket exists
        _ensure_bucket()
    return _client


def _ensure_bucket():
    """Create the default bucket if it doesn't exist."""
    client = _client
    if client is None:
        return
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
            logger.info("minio.bucket_created", bucket=settings.minio_bucket)
    except S3Error as e:
        logger.error("minio.bucket_error", error=str(e))


def upload_bytes(
    data: bytes,
    object_name: str,
    content_type: str = "image/webp",
) -> str:
    """Upload raw bytes to MinIO.
    
    Returns the object path (e.g., 'covers/abc123.webp').
    """
    client = get_minio_client()
    stream = io.BytesIO(data)
    
    client.put_object(
        settings.minio_bucket,
        object_name,
        stream,
        length=len(data),
        content_type=content_type,
    )
    
    logger.info("minio.uploaded", object_name=object_name, size=len(data))
    return object_name


async def download_and_upload(
    url: str,
    object_name: str,
) -> str:
    """Download a file from URL and upload to MinIO.
    
    Auto-detects content type from the response.
    Returns the object path.
    """
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as http:
        resp = await http.get(url)
        resp.raise_for_status()
    
    content_type = resp.headers.get("content-type", "image/png")
    # Normalize content type
    if "jpeg" in content_type or "jpg" in content_type:
        content_type = "image/jpeg"
    elif "png" in content_type:
        content_type = "image/png"
    elif "webp" in content_type:
        content_type = "image/webp"
    
    data = resp.content
    return upload_bytes(data, object_name, content_type)


def get_file_bytes(object_name: str) -> tuple[bytes, str]:
    """Read file from MinIO. Returns (data, content_type)."""
    client = get_minio_client()
    try:
        response = client.get_object(settings.minio_bucket, object_name)
        data = response.read()
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        response.close()
        response.release_conn()
        return data, content_type
    except S3Error as e:
        logger.error("minio.get_error", object_name=object_name, error=str(e))
        raise FileNotFoundError(f"Object not found: {object_name}")
