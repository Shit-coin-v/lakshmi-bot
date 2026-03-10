from datetime import date

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.utils import timezone

from apps.main.models import CustomUser

from .models import Campaign, CustomerCampaignAssignment, CustomerSegment


class CampaignError(Exception):
    pass


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

    candidates = get_segment_customers(campaign.segment)

    opted_out = candidates.filter(promo_enabled=False)
    skipped_opted_out = opted_out.count()

    eligible = candidates.filter(promo_enabled=True)
    total_candidates = eligible.count()

    existing_user_ids = set(
        CustomerCampaignAssignment.objects.filter(
            campaign=campaign,
            customer__in=eligible,
        ).values_list("customer_id", flat=True)
    )

    new_users = eligible.exclude(id__in=existing_user_ids)
    skipped_existing = total_candidates - new_users.count()

    assignments = [
        CustomerCampaignAssignment(customer_id=uid, campaign=campaign)
        for uid in new_users.values_list("id", flat=True)
    ]
    CustomerCampaignAssignment.objects.bulk_create(
        assignments, ignore_conflicts=True
    )

    return {
        "campaign_id": campaign.id,
        "segment_id": campaign.segment_id,
        "total_candidates": total_candidates,
        "created_assignments": len(assignments),
        "skipped_existing": skipped_existing,
        "skipped_opted_out": skipped_opted_out,
    }
