import logging
from datetime import date

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.authentication import JWTAuthentication
from apps.common.permissions import ApiKeyPermission, CustomerPermission
from apps.main.models import CustomUser
from apps.rfm.models import CustomerBonusTier

from .models import CampaignRule, CustomerCampaignAssignment
from .serializers import (
    UserAssignedCampaignSerializer,
)

logger = logging.getLogger(__name__)


class UserAssignedCampaignsView(generics.ListAPIView):
    """GET /api/campaigns/active/ — активные назначенные кампании текущего пользователя."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
    serializer_class = UserAssignedCampaignSerializer

    def get_queryset(self):
        now = timezone.now()
        return (
            CustomerCampaignAssignment.objects.filter(
                customer=self.request.telegram_user,
                campaign__is_active=True,
                campaign__start_at__lte=now,
                campaign__end_at__gte=now,
            )
            .exclude(
                campaign__one_time_use=True,
                used=True,
            )
            .select_related("campaign")
            .prefetch_related(
                Prefetch(
                    "campaign__rules",
                    queryset=CampaignRule.objects.filter(is_active=True),
                )
            )
            .order_by("-campaign__priority", "-campaign__created_at")
        )


def _build_not_found_response():
    return {
        "found": False,
        "bonus_tier": None,
        "bonus_tier_effective_from": None,
        "bonus_tier_effective_to": None,
        "campaign": None,
    }


def _build_campaign_block(rule, campaign):
    """Строит блок campaign для ответа, или None при fail-closed."""
    # --- stacking_mode ---
    if rule.stacking_mode == "replace_base":
        logger.warning(
            "campaigns.promo WARNING campaign_id=%d rule_id=%d "
            "uses unconfirmed stacking_mode=replace_base",
            campaign.id, rule.id,
        )
        return None

    # --- conditions ---
    conditions = {
        "min_purchase_amount": rule.min_purchase_amount,
        "product": None,
        "products": None,
        "category": None,
    }

    # Старый FK product (deprecated) или M2M products
    products_m2m = list(rule.products.all())
    has_old_product = rule.product_id is not None
    has_category = rule.category_id is not None

    # products + category одновременно → fail-closed
    if (products_m2m or has_old_product) and has_category:
        logger.warning(
            "campaigns.promo WARNING rule_id=%d campaign_id=%d "
            "has both products/product and category",
            rule.id, campaign.id,
        )
        return None

    # legacy product + products M2M одновременно → fail-closed
    if products_m2m and has_old_product:
        logger.warning(
            "campaigns.promo WARNING rule_id=%d campaign_id=%d "
            "has both legacy product_id=%s and products M2M — "
            "conflicting config, fail-closed",
            rule.id, campaign.id, rule.product_id,
        )
        return None

    if products_m2m:
        product_list = []
        for p in products_m2m:
            if not p.one_c_guid:
                logger.error(
                    "campaigns.promo ERROR product_id=%d missing one_c_guid, "
                    "campaign_id=%d rule_id=%d",
                    p.id, campaign.id, rule.id,
                )
                return None
            product_list.append({"one_c_guid": p.one_c_guid, "name": p.name})
        conditions["products"] = product_list
    elif has_old_product:
        product = rule.product
        if not product or not product.one_c_guid:
            logger.error(
                "campaigns.promo ERROR product_id=%s missing one_c_guid, "
                "campaign_id=%d rule_id=%d",
                rule.product_id, campaign.id, rule.id,
            )
            return None
        conditions["product"] = {
            "one_c_guid": product.one_c_guid,
            "name": product.name,
        }

    if has_category:
        cat = rule.category
        if not cat or not cat.external_id:
            logger.error(
                "campaigns.promo ERROR category_id=%s missing external_id, "
                "campaign_id=%d rule_id=%d",
                rule.category_id, campaign.id, rule.id,
            )
            return None
        conditions["category"] = {
            "external_id": cat.external_id,
            "name": cat.name,
        }

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "reward_type": rule.reward_type,
        "reward_value": rule.reward_value,
        "reward_percent": rule.reward_percent,
        "stacking_mode": rule.stacking_mode,
        "one_time_use": campaign.one_time_use,
        "conditions": conditions,
    }


class CustomerPromoView(APIView):
    """GET /api/campaigns/customer-promo/?telegram_id=<id>

    Возвращает бонусный статус клиента и активную рекламную кампанию для 1С.
    """

    authentication_classes = []
    permission_classes = [ApiKeyPermission]

    def get(self, request):
        # --- валидация telegram_id ---
        raw_tid = request.query_params.get("telegram_id", "").strip()
        if not raw_tid:
            return Response(
                {"detail": "telegram_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            telegram_id = int(raw_tid)
        except (ValueError, TypeError):
            return Response(
                {"detail": "telegram_id must be integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- поиск клиента ---
        try:
            user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return Response(_build_not_found_response())

        now = timezone.now()
        today = date.today()

        # --- bonus tier ---
        bonus_tier = "standard"
        effective_from = None
        effective_to = None

        try:
            tier_record = CustomerBonusTier.objects.get(
                customer=user,
                effective_from__lte=today,
                effective_to__gte=today,
            )
            bonus_tier = tier_record.tier
            effective_from = tier_record.effective_from
            effective_to = tier_record.effective_to
        except CustomerBonusTier.DoesNotExist:
            logger.error(
                "campaigns.promo ERROR customer_id=%d today=%s — "
                "no CustomerBonusTier found (batch failure?)",
                user.id, today,
            )
        except CustomerBonusTier.MultipleObjectsReturned:
            logger.error(
                "campaigns.promo ERROR customer_id=%d today=%s — "
                "multiple CustomerBonusTier records",
                user.id, today,
            )

        # --- campaign ---
        campaign_block = None

        assignments = list(
            CustomerCampaignAssignment.objects.filter(
                customer=user,
                campaign__is_active=True,
                campaign__start_at__lte=now,
                campaign__end_at__gte=now,
            )
            .exclude(campaign__one_time_use=True, used=True)
            .select_related("campaign")
            .prefetch_related(
                Prefetch(
                    "campaign__rules",
                    queryset=CampaignRule.objects.filter(is_active=True)
                    .select_related("product", "category")
                    .prefetch_related("products"),
                )
            )
            .order_by("-campaign__priority", "-campaign__created_at")
        )

        if len(assignments) > 1:
            # Fail-closed: множественные active assignments — нарушение инварианта
            assignment_ids = [a.id for a in assignments]
            logger.error(
                "campaigns.promo ERROR customer_id=%d has %d active assignments "
                "(ids=%s) — fail-closed, returning campaign=null",
                user.id, len(assignments), assignment_ids,
            )
        elif len(assignments) == 1:
            assignment = assignments[0]
            campaign = assignment.campaign
            active_rules = list(campaign.rules.all())

            if len(active_rules) == 0:
                logger.warning(
                    "campaigns.promo WARNING assignment_id=%d campaign_id=%d "
                    "— no active rules",
                    assignment.id, campaign.id,
                )
            elif len(active_rules) > 1:
                rule_ids = [r.id for r in active_rules]
                logger.warning(
                    "campaigns.promo WARNING campaign_id=%d has %d active rules "
                    "(ids=%s) — fail-closed",
                    campaign.id, len(active_rules), rule_ids,
                )
            else:
                campaign_block = _build_campaign_block(active_rules[0], campaign)

        data = {
            "found": True,
            "bonus_tier": bonus_tier,
            "bonus_tier_effective_from": effective_from,
            "bonus_tier_effective_to": effective_to,
            "campaign": campaign_block,
        }
        return Response(data)


class MarkCampaignUsedView(APIView):
    """POST /api/campaigns/mark-used/

    Отмечает одноразовую кампанию как использованную.
    """

    authentication_classes = []
    permission_classes = [ApiKeyPermission]

    def post(self, request):
        telegram_id = request.data.get("telegram_id")
        campaign_id = request.data.get("campaign_id")
        receipt_id = request.data.get("receipt_id")

        if not telegram_id or not campaign_id:
            return Response(
                {"detail": "telegram_id and campaign_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            telegram_id = int(telegram_id)
        except (ValueError, TypeError):
            return Response(
                {"detail": "telegram_id must be integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "customer not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            assignment = CustomerCampaignAssignment.objects.select_related(
                "campaign"
            ).get(customer=user, campaign_id=campaign_id)
        except CustomerCampaignAssignment.DoesNotExist:
            logger.warning(
                "campaigns.mark_used WARNING telegram_id=%d campaign_id=%s "
                "— assignment not found",
                telegram_id, campaign_id,
            )
            return Response(
                {"detail": "assignment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not assignment.campaign.one_time_use:
            logger.warning(
                "campaigns.mark_used WARNING telegram_id=%d campaign_id=%s "
                "— campaign is not one-time-use",
                telegram_id, campaign_id,
            )
            return Response(
                {"detail": "campaign is not one-time-use"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if assignment.used:
            logger.info(
                "campaigns.mark_used INFO duplicate mark-used "
                "assignment_id=%d receipt_id=%s",
                assignment.id, receipt_id,
            )
            return Response({"ok": True})

        assignment.used = True
        assignment.used_at = timezone.now()
        if receipt_id:
            assignment.receipt_id = str(receipt_id)[:100]
        assignment.save(update_fields=["used", "used_at", "receipt_id"])

        return Response({"ok": True})
