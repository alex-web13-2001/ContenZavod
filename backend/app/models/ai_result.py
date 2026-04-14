"""AIResult model — stores results of AI operations.

Tracks every AI call: input, output, tokens, cost, latency.
Used for prompt optimization and cost tracking.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class AIResult(Base, TenantMixin, TimestampMixin):
    """Result of an AI operation (classification, adaptation, analysis)."""

    __tablename__ = "ai_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_materials.id", ondelete="CASCADE"), nullable=False
    )
    prompt_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_configs.id", ondelete="SET NULL"), nullable=True
    )

    # What type of AI task was performed
    task_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # classify | adapt | analyze

    # Which provider handled this task
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Full input/output for debugging and optimization
    input_data: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    output_data: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)

    # Usage tracking
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
