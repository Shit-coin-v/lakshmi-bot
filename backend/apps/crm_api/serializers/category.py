from rest_framework import serializers

from apps.main.models import Category, Product


# Стабы для аналитических полей. Реальный источник — отдельный milestone.
_STUB_TREND = [42, 48, 51, 55, 58, 62, 65, 68, 72, 75, 78, 82]
_STUB_ABC_BY_INDEX = ["A", "A", "A", "B", "B", "B", "B", "C", "C", "C", "C", "C"]
_STUB_XYZ_BY_INDEX = ["X", "X", "Y", "Y", "X", "Y", "Z", "Y", "X", "Z", "X", "Y"]


def _slug_for(category) -> str:
    return f"cat-{category.external_id or category.id}"


class CategoryListSerializer(serializers.ModelSerializer):
    slug = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()
    skus = serializers.IntegerField(read_only=True)  # из annotate
    revenue = serializers.SerializerMethodField()
    cogs = serializers.SerializerMethodField()
    share = serializers.SerializerMethodField()
    turnover = serializers.SerializerMethodField()
    abc = serializers.SerializerMethodField()
    xyz = serializers.SerializerMethodField()
    trend = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "slug", "code", "name", "skus", "revenue", "cogs", "share", "turnover", "abc", "xyz", "trend"]

    def get_slug(self, obj) -> str:
        return _slug_for(obj)

    def get_code(self, obj) -> str:
        return obj.external_id or str(obj.id)

    def get_revenue(self, obj) -> int:
        # Стаб: 100k * (sort_order+1). Реальный расчёт — M2.
        return (obj.sort_order + 1) * 100_000

    def get_cogs(self, obj) -> int:
        return int(self.get_revenue(obj) * 0.7)

    def get_share(self, obj) -> float:
        return round(8.0 - obj.sort_order * 0.3, 1)

    def get_turnover(self, obj) -> float:
        return 5.0

    def get_abc(self, obj) -> str:
        return _STUB_ABC_BY_INDEX[obj.sort_order % 12]

    def get_xyz(self, obj) -> str:
        return _STUB_XYZ_BY_INDEX[obj.sort_order % 12]

    def get_trend(self, obj) -> list[int]:
        return _STUB_TREND


class _SkuInCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="product_code")
    sales30d = serializers.SerializerMethodField()
    units30d = serializers.SerializerMethodField()
    abc = serializers.SerializerMethodField()
    xyz = serializers.SerializerMethodField()
    suggestedOrder = serializers.SerializerMethodField()
    stockDays = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()
    spark = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "stock", "sales30d", "units30d",
            "abc", "xyz", "suggestedOrder", "stockDays", "supplier", "spark",
        ]

    # Все аналитические поля — стабы.
    def get_sales30d(self, obj) -> int:
        return int((obj.price or 0) * 100)

    def get_units30d(self, obj) -> int:
        return 50

    def get_abc(self, obj) -> str:
        return "A"

    def get_xyz(self, obj) -> str:
        return "X"

    def get_suggestedOrder(self, obj) -> int:
        return 100

    def get_stockDays(self, obj) -> float:
        return 2.5

    def get_supplier(self, obj) -> str:
        return "—"

    def get_spark(self, obj) -> list[int]:
        return _STUB_TREND


class CategoryDetailSerializer(CategoryListSerializer):
    skuList = serializers.SerializerMethodField()

    class Meta(CategoryListSerializer.Meta):
        fields = CategoryListSerializer.Meta.fields + ["skuList"]

    def get_skuList(self, obj) -> list[dict]:
        products = list(obj.products.filter(is_active=True)[:50])
        return _SkuInCategorySerializer(products, many=True).data
