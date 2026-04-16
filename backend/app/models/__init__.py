"""SQLAlchemy models package.

Import all models here so Alembic can discover them for auto-generation.
"""

from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.tenant import Tenant
from app.models.user import User
from app.models.source import Source
from app.models.material import RawMaterial
from app.models.ai_result import AIResult
from app.models.adapted_content import AdaptedContent
from app.models.media_asset import MediaAsset
from app.models.project import Project
from app.models.channel import Channel
from app.models.channel_score import MaterialChannelScore
from app.models.project_score import MaterialProjectScore
from app.models.channel_adaptation import ChannelAdaptation
from app.models.publish_job import PublishJob
from app.models.publication_metric import PublicationMetric
from app.models.prompt_config import PromptConfig

__all__ = [
    "Base",
    "TenantMixin",
    "TimestampMixin",
    "Tenant",
    "User",
    "Source",
    "RawMaterial",
    "AIResult",
    "AdaptedContent",
    "MediaAsset",
    "Project",
    "Channel",
    "MaterialChannelScore",
    "MaterialProjectScore",
    "ChannelAdaptation",
    "PublishJob",
    "PublicationMetric",
    "PromptConfig",
]
