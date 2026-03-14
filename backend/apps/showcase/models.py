from django.db import models


class ProductRanking(models.Model):
    """Предрассчитанный ранг товара для витрины.

    customer=NULL — глобальная витрина (fallback для всех).
    customer=конкретный — персональная витрина (этап 2).
    """

    customer = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="product_rankings",
        verbose_name="Клиент",
    )
    product = models.ForeignKey(
        "main.Product",
        on_delete=models.CASCADE,
        related_name="rankings",
        verbose_name="Товар",
    )
    score = models.FloatField("Score", default=0)
    calculated_at = models.DateTimeField("Дата расчёта")

    class Meta:
        db_table = "product_rankings"
        verbose_name = "Ранг товара"
        verbose_name_plural = "Ранги товаров"
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product"],
                name="uniq_customer_product_ranking",
            ),
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(customer__isnull=True),
                name="uniq_global_product_ranking",
            ),
        ]
        indexes = [
            models.Index(
                fields=["customer", "-score"],
                name="idx_ranking_customer_score",
            ),
        ]

    def __str__(self):
        if self.customer:
            return f"{self.product} — {self.customer} ({self.score})"
        return f"{self.product} — глобальный ({self.score})"
