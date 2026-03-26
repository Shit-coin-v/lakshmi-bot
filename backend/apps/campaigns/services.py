import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.main.models import CustomUser

from .models import AudienceType, Campaign, CustomerCampaignAssignment, CustomerSegment

logger = logging.getLogger(__name__)


class CampaignError(Exception):
    pass


def get_rfm_segment_customers(segment_label: str) -> QuerySet[CustomUser]:
    """Return customers whose current RFM profile matches segment_label."""
    from apps.rfm.models import CustomerRFMProfile

    customer_ids = (
        CustomerRFMProfile.objects
        .filter(segment_label=segment_label)
        .values_list("customer_id", flat=True)
    )
    return CustomUser.objects.filter(id__in=customer_ids)


def get_campaign_customers(campaign: Campaign) -> QuerySet[CustomUser]:
    """Return candidate customers for a campaign based on its audience_type."""
    if campaign.audience_type == AudienceType.RFM_SEGMENT:
        if not campaign.rfm_segment:
            raise CampaignError(
                f"Кампания '{campaign.name}': rfm_segment не указан."
            )
        return get_rfm_segment_customers(campaign.rfm_segment)

    if campaign.audience_type == AudienceType.CUSTOMER_SEGMENT:
        if not campaign.segment:
            raise CampaignError(
                f"Кампания '{campaign.name}': CustomerSegment не указан."
            )
        return get_segment_customers(campaign.segment)

    raise CampaignError(
        f"Кампания '{campaign.name}': неизвестный audience_type '{campaign.audience_type}'."
    )


def get_segment_customers(segment: CustomerSegment) -> QuerySet[CustomUser]:
    rules = segment.rules or {}

    if segment.segment_type == "manual":
        card_ids = rules.get("card_ids")
        if not isinstance(card_ids, list) or not card_ids:
            raise ValidationError(
                "Для ручного сегмента rules должен содержать 'card_ids' (список)."
            )
        return CustomUser.objects.filter(card_id__in=card_ids)

    if segment.segment_type == "rule_based":
        qs = CustomUser.objects.all()

        if "total_spent_gte" in rules:
            qs = qs.filter(total_spent__gte=rules["total_spent_gte"])

        if "purchase_count_gte" in rules:
            qs = qs.filter(purchase_count__gte=rules["purchase_count_gte"])

        if "bonuses_gte" in rules:
            qs = qs.filter(bonuses__gte=rules["bonuses_gte"])

        if "last_purchase_date_lte" in rules:
            try:
                d = date.fromisoformat(rules["last_purchase_date_lte"])
            except (ValueError, TypeError):
                raise ValidationError(
                    "last_purchase_date_lte: невалидный формат даты (ожидается YYYY-MM-DD)."
                )
            qs = qs.filter(last_purchase_date__date__lte=d)

        if "registration_date_lte" in rules:
            try:
                d = date.fromisoformat(rules["registration_date_lte"])
            except (ValueError, TypeError):
                raise ValidationError(
                    "registration_date_lte: невалидный формат даты (ожидается YYYY-MM-DD)."
                )
            qs = qs.filter(registration_date__date__lte=d)

        return qs

    raise ValidationError(f"Неизвестный тип сегмента: {segment.segment_type}")


def _get_overlapping_assignment_user_ids(campaign: Campaign) -> set[int]:
    """Находит клиентов с assignment в другой кампании с пересекающимся периодом.

    Два периода пересекаются (включительно по обеим границам):
    start_a <= end_b AND start_b <= end_a.

    Не блокируют:
    - Кампании с is_active=False.
    - Одноразовые кампании, уже отмеченные как used.
    """
    overlapping_q = (
        Q(campaign__is_active=True)
        & Q(campaign__start_at__lte=campaign.end_at)
        & Q(campaign__end_at__gte=campaign.start_at)
        & ~Q(campaign=campaign)
    )
    # Одноразовая кампания с used=True не блокирует
    overlapping_q &= ~Q(campaign__one_time_use=True, used=True)

    return set(
        CustomerCampaignAssignment.objects.filter(overlapping_q)
        .values_list("customer_id", flat=True)
    )


def assign_campaign_to_customers(campaign_id: int) -> dict:
    try:
        campaign = Campaign.objects.select_related("segment").get(id=campaign_id)
    except Campaign.DoesNotExist:
        raise CampaignError(f"Кампания с id={campaign_id} не найдена.")

    if not campaign.is_active:
        raise CampaignError(f"Кампания '{campaign.name}' неактивна.")

    now = timezone.now()
    if now < campaign.start_at:
        raise CampaignError(
            f"Кампания '{campaign.name}' ещё не началась (start_at={campaign.start_at})."
        )
    if now > campaign.end_at:
        raise CampaignError(
            f"Кампания '{campaign.name}' уже завершилась (end_at={campaign.end_at})."
        )

    candidates = get_campaign_customers(campaign)

    opted_out = candidates.filter(promo_enabled=False)
    skipped_opted_out = opted_out.count()

    eligible = candidates.filter(promo_enabled=True)
    total_candidates = eligible.count()

    # Исключить уже назначенных в эту кампанию
    existing_user_ids = set(
        CustomerCampaignAssignment.objects.filter(
            campaign=campaign,
            customer__in=eligible,
        ).values_list("customer_id", flat=True)
    )

    # Исключить клиентов с пересекающимися кампаниями (активные/будущие)
    overlapping_user_ids = _get_overlapping_assignment_user_ids(campaign)

    blocked_ids = existing_user_ids | overlapping_user_ids
    new_users = eligible.exclude(id__in=blocked_ids)

    skipped_existing = len(existing_user_ids & set(eligible.values_list("id", flat=True)))
    skipped_overlapping = len(overlapping_user_ids & set(eligible.values_list("id", flat=True)))

    assignments = [
        CustomerCampaignAssignment(customer_id=uid, campaign=campaign)
        for uid in new_users.values_list("id", flat=True)
    ]
    CustomerCampaignAssignment.objects.bulk_create(
        assignments, ignore_conflicts=True
    )

    if skipped_overlapping > 0:
        logger.info(
            "campaigns.assign INFO campaign_id=%d skipped_overlapping=%d",
            campaign.id,
            skipped_overlapping,
        )

    return {
        "campaign_id": campaign.id,
        "audience_type": campaign.audience_type,
        "segment_id": campaign.segment_id,
        "rfm_segment": campaign.rfm_segment,
        "total_candidates": total_candidates,
        "created_assignments": len(assignments),
        "skipped_existing": skipped_existing,
        "skipped_overlapping": skipped_overlapping,
        "skipped_opted_out": skipped_opted_out,
    }


@dataclass
class CampaignRewardPayload:
    assignment_id: int
    campaign_id: int
    campaign_name: str
    rule_id: int
    reward_type: str
    bonus_amount: Decimal
    is_accrual: bool
    card_id: str
    receipt_guid: str


def evaluate_campaign_reward(
    customer,
    total_amount: Decimal,
    positions: list[dict],
    receipt_guid: str,
) -> CampaignRewardPayload | None:
    """Evaluate whether a campaign reward applies to this receipt.

    Returns CampaignRewardPayload if conditions are met, None otherwise.
    Does NOT create CampaignRewardLog — caller is responsible.
    Does NOT modify any data.
    """
    from .models import CampaignRewardLog, CustomerCampaignAssignment

    # No card_id — cannot send to 1C
    if not customer.card_id:
        return None

    # Already successfully processed for this receipt
    if CampaignRewardLog.objects.filter(
        receipt_guid=receipt_guid, status=CampaignRewardLog.Status.SUCCESS,
    ).exists():
        return None

    # Find active assignments (limit 2 for fail-closed check)
    now = timezone.now()
    assignments = list(
        CustomerCampaignAssignment.objects.filter(
            customer=customer,
            campaign__is_active=True,
            campaign__start_at__lte=now,
            campaign__end_at__gte=now,
            used=False,
        )
        .select_related("campaign")
        .order_by("-campaign__priority", "-campaign__created_at")[:2]
    )

    if not assignments:
        return None

    if len(assignments) > 1:
        logger.warning(
            "evaluate_campaign_reward: customer_id=%d has %d active assignments, fail-closed",
            customer.id, len(assignments),
        )
        return None

    assignment = assignments[0]
    campaign = assignment.campaign

    # Get active rules (limit 2 for fail-closed)
    from .models import CampaignRule
    rules = list(
        campaign.rules.filter(is_active=True)
        .select_related("product", "category")
        .prefetch_related("products")[:2]
    )

    if not rules:
        return None

    if len(rules) > 1:
        logger.warning(
            "evaluate_campaign_reward: campaign_id=%d has %d active rules, fail-closed",
            campaign.id, len(rules),
        )
        return None

    rule = rules[0]

    # Unsupported reward types
    if rule.reward_type == "product_discount":
        logger.info(
            "evaluate_campaign_reward: skipping product_discount for receipt flow, campaign_id=%d",
            campaign.id,
        )
        return None

    # Check min_purchase_amount
    if rule.min_purchase_amount is not None and total_amount < rule.min_purchase_amount:
        return None

    # Determine matching amount based on product filter
    from apps.main.models import Product as ProductModel

    has_product_filter = False
    target_codes: set[str] = set()

    if rule.product_id is not None and rule.product:
        # Legacy FK
        has_product_filter = True
        target_codes = {rule.product.product_code}
    elif rule.products.exists():
        # M2M
        has_product_filter = True
        target_codes = set(rule.products.values_list("product_code", flat=True))
    elif rule.category_id is not None:
        # Category filter — lookup via Product.category FK
        has_product_filter = True
        receipt_codes = {pos["product_code"] for pos in positions}
        target_codes = set(
            ProductModel.objects.filter(
                product_code__in=receipt_codes, category=rule.category,
            ).values_list("product_code", flat=True)
        )

    if has_product_filter:
        matched_positions = [p for p in positions if p["product_code"] in target_codes]
        if not matched_positions:
            return None
        matching_amount = sum(
            (_as_decimal(p["price"]) - _as_decimal(p.get("discount_amount", 0)))
            * _as_decimal(p["quantity"])
            for p in matched_positions
        )
    else:
        matching_amount = total_amount

    # Calculate bonus
    bonus = Decimal("0")
    if rule.reward_type == "fixed_bonus":
        bonus = rule.reward_value or Decimal("0")
    elif rule.reward_type == "bonus_percent":
        percent = rule.reward_percent or Decimal("0")
        bonus = matching_amount * percent / Decimal("100")
    elif rule.reward_type == "fixed_plus_percent":
        fixed = rule.reward_value or Decimal("0")
        percent = rule.reward_percent or Decimal("0")
        bonus = fixed + matching_amount * percent / Decimal("100")
    else:
        logger.warning(
            "evaluate_campaign_reward: unknown reward_type=%s, campaign_id=%d",
            rule.reward_type, campaign.id,
        )
        return None

    bonus = bonus.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if bonus <= 0:
        return None

    return CampaignRewardPayload(
        assignment_id=assignment.id,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        rule_id=rule.id,
        reward_type=rule.reward_type,
        bonus_amount=bonus,
        is_accrual=True,
        card_id=customer.card_id,
        receipt_guid=receipt_guid,
    )


def _as_decimal(value) -> Decimal:
    """Convert value to Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
