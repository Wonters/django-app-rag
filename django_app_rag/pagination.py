"""
Pagination classes for REST API endpoints.

Provides configurable pagination with performance optimization.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django_app_rag.performance import performance_config


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for most API endpoints.

    Configurable via performance settings.
    """
    page_size = performance_config.api_page_size
    page_size_query_param = 'page_size'
    max_page_size = performance_config.api_max_page_size

    def get_paginated_response(self, data):
        """
        Return paginated response with additional metadata.
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.page_size,
            'results': data
        })


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for endpoints with large datasets (documents, etc).
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination for small datasets or detailed endpoints.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
