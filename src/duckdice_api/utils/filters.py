"""
Filtering utilities for data queries.
"""

from typing import TypeVar, Callable, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal

T = TypeVar('T')


class Filter:
    """Base filter class"""
    
    def apply(self, items: list[T], getter: Callable[[T], Any]) -> list[T]:
        """Apply filter to items"""
        raise NotImplementedError


class DateRangeFilter(Filter):
    """Filter items by date range"""
    
    def __init__(self, start: Optional[datetime] = None, end: Optional[datetime] = None):
        self.start = start
        self.end = end
    
    def apply(self, items: list[T], getter: Callable[[T], datetime]) -> list[T]:
        """Filter items within date range"""
        result = items
        if self.start:
            result = [item for item in result if getter(item) >= self.start]
        if self.end:
            result = [item for item in result if getter(item) <= self.end]
        return result


class ValueFilter(Filter):
    """Filter items by value comparison"""
    
    def __init__(self, value: Any, operator: str = 'eq'):
        """
        Initialize value filter.
        
        Args:
            value: Value to compare against
            operator: Comparison operator ('eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in')
        """
        self.value = value
        self.operator = operator
    
    def apply(self, items: list[T], getter: Callable[[T], Any]) -> list[T]:
        """Filter items by value"""
        if self.operator == 'eq':
            return [item for item in items if getter(item) == self.value]
        elif self.operator == 'ne':
            return [item for item in items if getter(item) != self.value]
        elif self.operator == 'gt':
            return [item for item in items if getter(item) > self.value]
        elif self.operator == 'gte':
            return [item for item in items if getter(item) >= self.value]
        elif self.operator == 'lt':
            return [item for item in items if getter(item) < self.value]
        elif self.operator == 'lte':
            return [item for item in items if getter(item) <= self.value]
        elif self.operator == 'in':
            return [item for item in items if getter(item) in self.value]
        else:
            return items


class BooleanFilter(Filter):
    """Filter items by boolean value"""
    
    def __init__(self, value: bool):
        self.value = value
    
    def apply(self, items: list[T], getter: Callable[[T], bool]) -> list[T]:
        """Filter items by boolean"""
        return [item for item in items if getter(item) == self.value]


class FilterSet:
    """Collection of filters to apply"""
    
    def __init__(self):
        self.filters: list[tuple[Filter, Callable]] = []
    
    def add(self, filter_obj: Filter, getter: Callable[[T], Any]) -> 'FilterSet':
        """Add a filter with its getter function"""
        self.filters.append((filter_obj, getter))
        return self
    
    def apply(self, items: list[T]) -> list[T]:
        """Apply all filters sequentially"""
        result = items
        for filter_obj, getter in self.filters:
            result = filter_obj.apply(result, getter)
        return result


# Convenience functions
def filter_by_date_range(
    items: list[T],
    getter: Callable[[T], datetime],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> list[T]:
    """Filter items by date range"""
    return DateRangeFilter(start, end).apply(items, getter)


def filter_by_value(
    items: list[T],
    getter: Callable[[T], Any],
    value: Any,
    operator: str = 'eq'
) -> list[T]:
    """Filter items by value"""
    return ValueFilter(value, operator).apply(items, getter)


def filter_by_boolean(
    items: list[T],
    getter: Callable[[T], bool],
    value: bool
) -> list[T]:
    """Filter items by boolean value"""
    return BooleanFilter(value).apply(items, getter)


def filter_last_n_days(
    items: list[T],
    getter: Callable[[T], datetime],
    days: int
) -> list[T]:
    """Filter items from last N days"""
    start = datetime.now() - timedelta(days=days)
    return filter_by_date_range(items, getter, start=start)


def filter_wins_only(items: list[T], getter: Callable[[T], bool]) -> list[T]:
    """Filter only winning items"""
    return filter_by_boolean(items, getter, True)


def filter_losses_only(items: list[T], getter: Callable[[T], bool]) -> list[T]:
    """Filter only losing items"""
    return filter_by_boolean(items, getter, False)
