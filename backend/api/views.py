import logging

from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import PurchaseSerializer
# from .utils import apply_purchase_bonus
from main.models import CustomUser, Store, Product, Transaction

logger = logging.getLogger(__name__)


class PurchaseView(APIView):

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

        # Store
        try:
            store = Store.objects.get(id=data['store_id'])
        except Store.DoesNotExist:
            return Response({"error": "Store not found"}, status=404)

        # Product
        product, _ = Product.objects.get_or_create(
            product_code=data['product_code'],
            defaults={
                'name': data['product_name'],
                'category': data['category'],
                'price': data['price'],
                'store': store,
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
            store=store,
            is_promotional=data['is_promotional']
        )

        return Response({
            "message": "Successfully",
            "transaction_id": transaction.id,
            "bonus_earned": float(transaction.bonus_earned),
            "total_bonuses": float(customer.bonuses)
        }, status=201)
