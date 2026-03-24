import logging
from datetime import date

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.main.models import CustomUser

from .models import Campaign, CustomerCampaignAssignment, CustomerSegment

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
    if campaign.audience_type == "rfm_segment":
        if not campaign.rfm_segment:
            raise CampaignError(
                f"Кампания '{campaign.name}': rfm_segment не указан."
            )
        return get_rfm_segment_customers(campaign.rfm_segment)

    if campaign.audience_type == "customer_segment":
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
        user_ids = rules.get("user_ids")
        if not isinstance(user_ids, list):
            raise ValidationError(
                "Для ручного сегмента rules должен содержать 'user_ids' (список)."
            )
        return CustomUser.objects.filter(id__in=user_ids)

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
