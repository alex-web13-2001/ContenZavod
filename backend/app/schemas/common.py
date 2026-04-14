"""Common schemas — pagination, responses."""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""

    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


class PaginatedResponse(BaseModel):
    """Wrapper for paginated API responses."""

    items: list = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
