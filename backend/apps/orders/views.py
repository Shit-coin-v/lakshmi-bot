from __future__ import annotations

from django.db import transaction
from django.db.models import Count

from rest_framework import filters, generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.authentication import JWTAuthentication
from apps.common.permissions import CustomerPermission
from apps.main.models import Category
from apps.main.services.catalog_filters import (
    get_hidden_category_ids,
    request_can_view_hidden,
)
from apps.orders.serializers import (
    CategoryListSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    ProductListSerializer,
)
from apps.orders.models import Order, Product


class CatalogRootView(generics.ListAPIView):
    serializer_class = CategoryListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True, parent__isnull=True)
        if not request_can_view_hidden(self.request):
            qs = qs.exclude(hide_from_app=True)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class CatalogChildrenView(generics.ListAPIView):
    serializer_class = CategoryListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        parent = generics.get_object_or_404(Category, pk=self.kwargs["pk"])
        qs = parent.children.filter(is_active=True)
        if not request_can_view_hidden(self.request):
            qs = qs.exclude(hide_from_app=True)
            # Если сам родитель помечен hide_from_app, его потомков тоже скрываем.
            hidden_ids = get_hidden_category_ids()
            if parent.pk in hidden_ids:
                return qs.none()
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_queryset(self):
        from django.db.models import Q
        from rest_framework.exceptions import ValidationError

        qs = super().get_queryset()

        # Скрытые категории — спрятать товары и из выдачи, и из поиска.
        # Staff (Photo Studio) с валидным X-Api-Key + ?include_hidden=true
        # получает полный каталог.
        if not request_can_view_hidden(self.request):
            hidden_ids = get_hidden_category_ids()
            if hidden_ids:
                qs = qs.exclude(category_id__in=hidden_ids)

        category_id = self.request.query_params.get("category_id")
        if category_id is not None:
            try:
                category_id = int(category_id)
            except (ValueError, TypeError):
                raise ValidationError({"category_id": "Должно быть целым числом."})
            ids = self._collect_descendant_ids(category_id)
            qs = qs.filter(category_id__in=ids)

        # has_image=true|false — фильтр по наличию загруженного фото.
        # Используется Photo Studio для вкладок "Готово" / "Нет фото",
        # чтобы фильтрация работала на всём каталоге, а не локально по
        # одной странице.
        has_image = self.request.query_params.get("has_image")
        if has_image is not None:
            value = has_image.strip().lower()
            if value in {"true", "1", "yes"}:
                qs = qs.exclude(Q(image__isnull=True) | Q(image=""))
            elif value in {"false", "0", "no"}:
                qs = qs.filter(Q(image__isnull=True) | Q(image=""))
            else:
                raise ValidationError(
                    {"has_image": "Допустимы значения true/false."}
                )
        return qs

    @staticmethod
    def _collect_descendant_ids(category_id: int) -> set[int]:
        """Собрать ID категории и всех её потомков (BFS)."""
        ids = {category_id}
        queue = [category_id]
        while queue:
            parent_id = queue.pop()
            children = list(
                Category.objects.filter(
                    parent_id=parent_id, is_active=True,
                ).values_list("id", flat=True)
            )
            for child_id in children:
                if child_id not in ids:
                    ids.add(child_id)
                    queue.append(child_id)
        return ids


class OrderCreateView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def perform_create(self, serializer):
        serializer.save(customer=self.request.telegram_user)

    def create(self, request, *args, **kwargs):
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("OrderCreate payload: %s", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            _logger.warning("OrderCreate validation errors: %s", serializer.errors)
            serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        order = serializer.instance

        response_data = {"id": order.id}

        # For SBP payments, include confirmation_url
        confirmation_url = getattr(order, "_confirmation_url", None)
        if confirmation_url:
            response_data["confirmation_url"] = confirmation_url
            response_data["payment_id"] = order.payment_id

        return Response(response_data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all().prefetch_related("items__product")
    serializer_class = OrderDetailSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def get_object(self):
        obj = super().get_object()
        if obj.customer_id != self.request.telegram_user.pk:
            raise PermissionDenied("Нет доступа к чужому заказу")
        return obj


class OrderListUserView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.telegram_user,
        ).annotate(
            items_count=Count("items"),
        ).order_by("-created_at")


class OrderCancelView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    CANCELLABLE_STATUSES = ("new", "accepted", "assembly", "ready")

    def post(self, request, pk):
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(pk=pk)
            except Order.DoesNotExist:
                return Response(
                    {"detail": "Заказ не найден"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if order.customer_id != request.telegram_user.pk:
                return Response(
                    {"detail": "Нет доступа к чужому заказу"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if order.status not in self.CANCELLABLE_STATUSES:
                return Response(
                    {"detail": "Заказ нельзя отменить в текущем статусе"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            cancel_reason = request.data.get("cancel_reason")
            valid_reasons = {c[0] for c in Order.CANCEL_REASON_CHOICES}
            if cancel_reason and cancel_reason not in valid_reasons:
                cancel_reason = None

            order.status = "canceled"
            order.canceled_by = "client"
            order.cancel_reason = cancel_reason
            order.save(update_fields=["status", "canceled_by", "cancel_reason"])

            oid = order.id

            # Cancel/refund online payment if exists.
            if order.payment_id and order.payment_status in ("authorized", "captured"):
                from apps.integrations.payments.tasks import cancel_payment_task
                transaction.on_commit(lambda: cancel_payment_task.delay(oid))

            # Notify 1C about cancellation (if order was sent to 1C).
            if order.onec_guid or order.sync_status in ("sent", "confirmed"):
                from apps.integrations.onec.tasks import notify_onec_order_canceled
                transaction.on_commit(lambda: notify_onec_order_canceled.delay(oid))

        # Push notification handled by _order_post_save signal
        return Response({"detail": "Заказ отменён"})
