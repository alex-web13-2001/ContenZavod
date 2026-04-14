"""AI capability types — what each provider can do."""

from enum import StrEnum


class AICapability(StrEnum):
    """Types of AI capabilities that providers can offer."""

    TEXT_CLASSIFY = "text_classify"
    TEXT_ADAPT = "text_adapt"
    TEXT_ANALYZE = "text_analyze"
    IMAGE_GENERATE = "image_generate"
    VIDEO_GENERATE = "video_generate"
