import logging

from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import PurchaseSerializer
from main.models import CustomUser, Product, Transaction

logger = logging.getLogger(__name__)


class PurchaseView(APIView):
    """
    Request:
    {
        "telegram_id": 373604254,
        "product_code": "ABC123",
        "product_name": "Молоко",
        "category": "Молочные продукты",
        "quantity": 2,
        "price": 90.00,
        "total": 180.00,
        "purchase_date": "2025-03-25",
        "purchase_time": "18:12:00",
        "store_id": 1,
        "is_promotional": false,
        "bonus_earned": 2.00,
        "total_bonuses": 9.40
    }
    """

    @staticmethod
    def post(request):
        logger.info(f"Incoming purchase data: {request.data}")
        serializer = PurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data

        # User
        try:
            customer = CustomUser.objects.get(telegram_id=data['telegram_id'], )
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        customer.bonuses = data['total_bonuses']
        customer.save(update_fields=['bonuses'])

        # Checking the first purchase
        is_first_purchase = not Transaction.objects.filter(customer=customer).exists()

        # Product
        product, _ = Product.objects.get_or_create(
            product_code=data['product_code'],
            defaults={
                'name': data['product_name'],
                'category': data['category'],
                'price': data['price'],
                'store_id': data['store_id'],
                'is_promotional': data['is_promotional'],
            }
        )

        # Transaction
        transaction = Transaction.objects.create(
            customer=customer,
            product=product,
            quantity=data['quantity'],
            total_amount=data['total'],
            bonus_earned=data['bonus_earned'],
            purchase_date=data['purchase_date'],
            purchase_time=data['purchase_time'],
            store_id=data['store_id'],
            is_promotional=data['is_promotional']
        )

        if customer.referrer and is_first_purchase:
            is_first_purchase = True

        return Response({
            "message": "Successfully",
            "transaction_id": transaction.id,
            "bonus_earned": float(transaction.bonus_earned),
            "total_bonuses": float(customer.bonuses),
            "is_first_purchase": is_first_purchase,
            "referrer": customer.referrer.telegram_id if customer.referrer else None,
        }, status=201)
