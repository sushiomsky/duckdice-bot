"""
Pagination utilities for API responses.
"""

from typing import TypeVar, Generic, Callable, Optional
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class PaginationParams:
    """Parameters for paginated requests"""
    page: int = 1
    page_size: int = 50
    
    def validate(self) -> None:
        """Validate pagination parameters"""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("Page size must be between 1 and 100")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database queries"""
        return self.page_size


class Paginator(Generic[T]):
    """Generic paginator for lists"""
    
    def __init__(self, items: list[T], page: int = 1, page_size: int = 50):
        """
        Initialize paginator.
        
        Args:
            items: Full list of items
            page: Current page number (1-indexed)
            page_size: Items per page
        """
        self.items = items
        self.page = page
        self.page_size = page_size
        self.total = len(items)
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages"""
        return (self.total + self.page_size - 1) // self.page_size if self.total > 0 else 1
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page"""
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page"""
        return self.page > 1
    
    @property
    def start_index(self) -> int:
        """Get start index for current page"""
        return (self.page - 1) * self.page_size
    
    @property
    def end_index(self) -> int:
        """Get end index for current page"""
        return min(self.start_index + self.page_size, self.total)
    
    def get_page(self) -> list[T]:
        """Get items for current page"""
        return self.items[self.start_index:self.end_index]
    
    def page_range(self, pages_around: int = 2) -> list[int]:
        """
        Get range of page numbers to display.
        
        Args:
            pages_around: Number of pages to show around current page
            
        Returns:
            List of page numbers
        """
        start = max(1, self.page - pages_around)
        end = min(self.total_pages, self.page + pages_around)
        return list(range(start, end + 1))


def create_page_response(
    items: list[T],
    page: int,
    page_size: int,
    transform: Optional[Callable[[T], any]] = None
) -> dict:
    """
    Create a standardized page response.
    
    Args:
        items: Full list of items
        page: Current page number
        page_size: Items per page
        transform: Optional function to transform each item
        
    Returns:
        Dict with pagination metadata and items
    """
    paginator = Paginator(items, page, page_size)
    page_items = paginator.get_page()
    
    if transform:
        page_items = [transform(item) for item in page_items]
    
    return {
        'items': page_items,
        'total': paginator.total,
        'page': page,
        'page_size': page_size,
        'total_pages': paginator.total_pages,
        'has_next': paginator.has_next,
        'has_prev': paginator.has_prev,
    }
