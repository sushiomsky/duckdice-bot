"""
Utilities package for DuckDice API.
"""

from .pagination import PaginationParams, Paginator, create_page_response
from .filters import (
    Filter,
    DateRangeFilter,
    ValueFilter,
    BooleanFilter,
    FilterSet,
    filter_by_date_range,
    filter_by_value,
    filter_by_boolean,
    filter_last_n_days,
    filter_wins_only,
    filter_losses_only,
)

__all__ = [
    'PaginationParams',
    'Paginator',
    'create_page_response',
    'Filter',
    'DateRangeFilter',
    'ValueFilter',
    'BooleanFilter',
    'FilterSet',
    'filter_by_date_range',
    'filter_by_value',
    'filter_by_boolean',
    'filter_last_n_days',
    'filter_wins_only',
    'filter_losses_only',
]
