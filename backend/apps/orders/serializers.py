from rest_framework import serializers

from apps.main.models import Product


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
