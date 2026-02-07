from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class HeaderPagination(PageNumberPagination):
    """Return body as plain array; put pagination metadata into response headers."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        response = Response(data)
        response["X-Total-Count"] = self.page.paginator.count
        response["X-Page"] = self.page.number
        response["X-Page-Size"] = self.get_page_size(self.request)

        links = []
        next_url = self.get_next_link()
        prev_url = self.get_previous_link()
        if next_url:
            links.append(f'<{next_url}>; rel="next"')
        if prev_url:
            links.append(f'<{prev_url}>; rel="prev"')
        if links:
            response["Link"] = ", ".join(links)

        return response
