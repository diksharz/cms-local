from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10  # Set the number of items per page for this ViewSet
    page_size_query_param = 'page_size'  # Allow clients to modify page size via query parameters
    max_page_size = 100  # Maximum page size limit
