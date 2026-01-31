from rest_framework import serializers

from apps.main.models import Order, OrderItem, Product


class ProductListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 
            'product_code', 
            'name', 
            'price', 
            'category', 
            'stock', 
            'image_url',     
            'description',   
            'is_promotional'
        ]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class OrderItemDetailSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "product_code",
            "name",
            "quantity",
            "price_at_moment",
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = OrderItemDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "created_at",
            "status",
            "status_display",
            "payment_method",
            "fulfillment_type",
            "address",
            "phone",
            "comment",
            "products_price",
            "delivery_price",
            "total_price",
            "items",
        ]
