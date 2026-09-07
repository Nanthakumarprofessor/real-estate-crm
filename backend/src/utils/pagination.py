"""
Pagination utilities.

All list endpoints in the CRM return a consistent pagination envelope:
    {
        "items": [...],
        "total": <int>,
        "page":  <int>,
        "size":  <int>
    }

Usage in a router:
    from src.utils.pagination import PaginationParams, paginate_query

    @router.get("/leads")
    def list_leads(pagination: PaginationParams = Depends()):
        ...
"""
from typing import Any, Generic, List, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PaginationParams:
    """
    FastAPI dependency that extracts page/size query parameters
    and computes the SQL offset.

    Defaults: page=1, size=10
    Max size: 100 (prevents accidental full-table dumps)
    """

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-based)"),
        size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response envelope.
    Used as the return type for all list endpoints.

    Example:
        PaginatedResponse[LeadResponse]
    """

    items: List[T]
    total: int
    page: int
    size: int

    @classmethod
    def build(
        cls,
        items: List[Any],
        total: int,
        pagination: PaginationParams,
    ) -> "PaginatedResponse[Any]":
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
        )
