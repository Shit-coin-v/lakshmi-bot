# from decimal import Decimal
# from main.models import CustomUser, Store


# def apply_purchase_bonus(user: CustomUser, store: Store, total_amount: Decimal) -> Decimal:
#     """
#     Начисляет бонусы пользователю в зависимости от процента типа магазина.
#     Возвращает сумму начисленных бонусов.
#     """
#     try:
#         store_type = store.type
#         percent = store_type.percent
#     except AttributeError:
#         percent = Decimal('0')
#
#     bonus = (total_amount * percent) / 100
#     user.bonuses += bonus
#     user.save(update_fields=['bonuses'])
#
#     return bonus
