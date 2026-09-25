from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        raw = request.query_params.get(self.page_size_query_param)
        if raw is None:
            return self.page_size
        try:
            value = int(raw)
        except (TypeError, ValueError):
            raise ValidationError({"page_size": ["Taille de page invalide."]})
        if not 1 <= value <= self.max_page_size:
            raise ValidationError({"page_size": ["Taille de page invalide."]})
        return value
