"""AI Provider Registry — single point of access for all AI providers.

Supports:
- Registration of multiple providers per capability
- Tenant-specific provider preferences
- Automatic fallback on provider failure
"""

import structlog

from ai.capabilities import AICapability
from ai.providers.base import BaseAIProvider

logger = structlog.get_logger()


class AllProvidersFailedError(Exception):
    """Raised when all providers for a capability have failed."""

    def __init__(self, capability: str):
        super().__init__(f"All providers failed for capability: {capability}")
        self.capability = capability


class AIProviderRegistry:
    """Registry for AI providers with fallback support.

    Usage:
        registry = AIProviderRegistry()
        registry.register(GeminiFlashProvider(api_key="..."))
        registry.register(NanoBananaProvider(api_key="..."))

        # Get a specific provider
        text_ai = registry.get(AICapability.TEXT_CLASSIFY)

        # Get with tenant preference
        text_ai = registry.get(AICapability.TEXT_CLASSIFY, preferred="gemini_flash")

        # Execute with automatic fallback
        result = await registry.execute_with_fallback(
            AICapability.TEXT_CLASSIFY,
            task={"content": "..."},
            preferred="gemini_flash"
        )
    """

    def __init__(self) -> None:
        self._providers: dict[str, dict[str, BaseAIProvider]] = {}

    def register(self, provider: BaseAIProvider) -> None:
        """Register a provider for its declared capabilities.

        Args:
            provider: AI provider instance to register.
        """
        for capability in provider.capabilities:
            self._providers.setdefault(capability, {})[provider.name] = provider
            logger.info(
                "ai.provider.registered",
                provider=provider.name,
                capability=capability,
            )

    def get(
        self, capability: str | AICapability, preferred: str | None = None
    ) -> BaseAIProvider:
        """Get a provider for a capability.

        Args:
            capability: The AI capability needed.
            preferred: Preferred provider name (optional).

        Returns:
            AI provider instance.

        Raises:
            KeyError: If no provider is registered for the capability.
        """
        providers = self._providers.get(str(capability), {})
        if not providers:
            raise KeyError(f"No providers registered for capability: {capability}")

        if preferred and preferred in providers:
            return providers[preferred]

        # Return first available
        return next(iter(providers.values()))

    def list_providers(self, capability: str | AICapability | None = None) -> dict[str, list[str]]:
        """List all registered providers, optionally filtered by capability.

        Args:
            capability: Filter by capability (optional).

        Returns:
            Dict mapping capability → list of provider names.
        """
        if capability:
            providers = self._providers.get(str(capability), {})
            return {str(capability): list(providers.keys())}
        return {cap: list(provs.keys()) for cap, provs in self._providers.items()}

    async def execute_with_fallback(
        self,
        capability: str | AICapability,
        method: str,
        preferred: str | None = None,
        **kwargs,
    ) -> any:
        """Execute a method on a provider with automatic fallback.

        Tries the preferred provider first, then falls back to alternatives.

        Args:
            capability: The AI capability needed.
            method: Method name to call on the provider.
            preferred: Preferred provider name.
            **kwargs: Arguments to pass to the method.

        Returns:
            Result from the provider method.

        Raises:
            AllProvidersFailedError: If all providers fail.
        """
        providers = self._providers.get(str(capability), {})
        if not providers:
            raise KeyError(f"No providers registered for capability: {capability}")

        # Order: preferred first, then others
        ordered: list[BaseAIProvider] = []
        if preferred and preferred in providers:
            ordered.append(providers[preferred])
        ordered.extend(p for name, p in providers.items() if name != preferred)

        last_error: Exception | None = None
        for provider in ordered:
            try:
                func = getattr(provider, method)
                result = await func(**kwargs)
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    "ai.provider.fallback",
                    provider=provider.name,
                    capability=str(capability),
                    method=method,
                    error=str(e),
                )

        raise AllProvidersFailedError(str(capability)) from last_error


# Global registry instance
registry = AIProviderRegistry()
