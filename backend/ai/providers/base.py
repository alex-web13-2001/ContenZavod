"""Base interfaces for AI providers.

All AI providers must implement one of these abstract base classes.
This enables the pluggable provider system: add any AI provider
by implementing the interface and registering it in the registry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ai.capabilities import AICapability


@dataclass
class ClassificationResult:
    """Result of content classification."""

    relevance_score: int  # 0-100
    content_type: str  # news | analysis | tutorial | opinion
    channel_suitability: dict[str, dict[str, Any]]  # channel → {suitable, priority, format}
    topics: list[str]
    suggested_angle: str
    estimated_engagement: str  # low | medium | high
    raw_response: dict = field(default_factory=dict)


@dataclass
class AdaptedContentResult:
    """Result of content adaptation for a channel."""

    title: str
    body: str
    hashtags: list[str] = field(default_factory=list)
    cta: str = ""
    image_prompt: str = ""
    seo_keywords: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    raw_response: dict = field(default_factory=dict)


@dataclass
class VideoJobStatus:
    """Status of an async video generation job."""

    job_id: str
    status: str  # pending | generating | ready | failed
    progress: float = 0.0  # 0.0 - 1.0
    video_url: str | None = None
    error: str | None = None


class BaseAIProvider(ABC):
    """Base interface for all AI providers.

    Every provider must declare its name and capabilities.
    """

    name: str
    capabilities: list[AICapability]

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider API is reachable.

        Returns:
            True if the provider is operational.
        """
        ...


class TextAIProvider(BaseAIProvider):
    """Provider for text-based AI tasks (classification, adaptation, analysis)."""

    @abstractmethod
    async def classify(
        self, content: str, system_prompt: str, user_prompt: str
    ) -> ClassificationResult:
        """Classify content: relevance, type, channel suitability.

        Args:
            content: Raw text content to classify.
            system_prompt: System prompt for the AI model.
            user_prompt: User prompt template with content inserted.

        Returns:
            ClassificationResult with scores and recommendations.
        """
        ...

    @abstractmethod
    async def adapt(
        self,
        content: str,
        channel_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> AdaptedContentResult:
        """Adapt content for a specific publishing channel.

        Args:
            content: Source content to adapt.
            channel_type: Target channel (telegram, website, youtube).
            system_prompt: System prompt for the AI model.
            user_prompt: User prompt template.

        Returns:
            AdaptedContentResult with formatted content for the channel.
        """
        ...


class ImageAIProvider(BaseAIProvider):
    """Provider for image generation."""

    @abstractmethod
    async def generate_image(
        self, prompt: str, aspect_ratio: str = "16:9", **kwargs: Any
    ) -> bytes:
        """Generate an image from a text prompt.

        Args:
            prompt: Image description.
            aspect_ratio: Target aspect ratio.
            **kwargs: Provider-specific parameters.

        Returns:
            Raw image bytes.
        """
        ...


class VideoAIProvider(BaseAIProvider):
    """Provider for video generation (asynchronous workflow)."""

    @abstractmethod
    async def submit_job(self, script: str, **kwargs: Any) -> str:
        """Submit a video generation job.

        Args:
            script: Video script/storyboard.
            **kwargs: Provider-specific parameters.

        Returns:
            Job ID for status tracking.
        """
        ...

    @abstractmethod
    async def check_status(self, job_id: str) -> VideoJobStatus:
        """Check the status of a video generation job.

        Args:
            job_id: ID returned from submit_job.

        Returns:
            VideoJobStatus with current state and progress.
        """
        ...

    @abstractmethod
    async def download(self, job_id: str) -> bytes:
        """Download the completed video.

        Args:
            job_id: ID of the completed job.

        Returns:
            Raw video bytes.

        Raises:
            VideoNotReadyError: If the video is not yet completed.
        """
        ...
