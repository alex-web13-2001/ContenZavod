"""API v1 router — aggregates all endpoint modules."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.channels import router as channels_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.health import router as health_router
from app.api.v1.materials import router as materials_router
from app.api.v1.projects import router as projects_router
from app.api.v1.sources import router as sources_router
from app.api.v1.adaptations import router as adaptations_router
from app.api.v1.files import router as files_router
from app.api.v1.digests import router as digests_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(sources_router)
api_router.include_router(materials_router)
api_router.include_router(projects_router)
api_router.include_router(channels_router)
api_router.include_router(adaptations_router)
api_router.include_router(files_router)
api_router.include_router(digests_router)

