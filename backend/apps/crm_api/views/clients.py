from django.db.models import Q
from django.http import Http404
from rest_framework.exceptions import NotFound
from rest_framework.generics import ListAPIView, RetrieveAPIView

from apps.crm_api.pagination import CRMHeaderPagination
from apps.crm_api.serializers.client import ClientDetailSerializer, ClientListSerializer
from apps.crm_api.views._base import CRMAPIView
from apps.main.models import CustomUser


class ClientListView(ListAPIView, CRMAPIView):
    """GET /api/crm/clients/?q=&segment=&page=&page_size= — список клиентов CRM.

    Поиск (q) — по name/phone/email/card_id.
    Фильтр по сегменту (segment) — по значению CustomerRFMProfile.segment_label.
    """

    serializer_class = ClientListSerializer
    pagination_class = CRMHeaderPagination

    def get_queryset(self):
        qs = (
            CustomUser.objects
            .select_related("rfm_profile")
            .order_by("-id")
        )
        q = self.request.query_params.get("q", "").strip()
        segment = self.request.query_params.get("segment", "").strip()

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(phone__icontains=q)
                | Q(email__icontains=q)
                | Q(card_id__icontains=q)
            )
        if segment and segment != "Все":
            qs = qs.filter(rfm_profile__segment_label=segment)
        return qs


class ClientDetailView(RetrieveAPIView, CRMAPIView):
    """GET /api/crm/clients/<card_id>/ — карточка клиента CRM."""

    serializer_class = ClientDetailSerializer
    lookup_field = "card_id"
    lookup_url_kwarg = "card_id"

    def get_queryset(self):
        return (
            CustomUser.objects
            .select_related("rfm_profile")
            .prefetch_related("orders")
        )

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            raise NotFound("Клиент не найден")
