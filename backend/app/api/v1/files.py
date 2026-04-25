"""File serving endpoints — proxies files from MinIO storage."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{file_path:path}")
async def serve_file(file_path: str):
    """Serve a file from MinIO storage.

    Example: GET /api/v1/files/covers/abc123.png
    """
    from app.services.storage import get_file_bytes

    try:
        data, content_type = get_file_bytes(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",  # 24h cache
        },
    )
