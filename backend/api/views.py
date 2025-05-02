import logging
import requests
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import PurchaseSerializer
from main.models import CustomUser, Product, Transaction
from src import config

logger = logging.getLogger(__name__)


class PurchaseAPIView(APIView):
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
        customer.last_purchase_date = datetime.combine(data['purchase_date'], data['purchase_time'])
        customer.total_spent += data['total']
        customer.purchase_count += 1
        customer.save(update_fields=['bonuses', 'last_purchase_date', 'total_spent', 'purchase_count'])

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
            "msg": "Successfully",
            "transaction_id": transaction.id,
            "bonus_earned": float(transaction.bonus_earned),
            "total_bonuses": float(customer.bonuses),
            "is_first_purchase": is_first_purchase,
            "referrer": customer.referrer.telegram_id if customer.referrer else None,
        }, status=201)


class SendMessageAPIView(APIView):
    """
    Request:
    {
        "telegram_id": 12345678: int,
        "text": "Text": str
    }
    """

    @staticmethod
    def post(request):
        telegram_id = request.data.get('telegram_id')
        text = request.data.get('text')

        if not telegram_id or not text:
            return Response({'err': 'telegram_id and text are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return Response({'err': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not user.telegram_id:
            return Response({'err': 'User does not have a Telegram ID.'}, status=status.HTTP_400_BAD_REQUEST)

        telegram_url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': user.telegram_id,
            'text': text,
            'parse_mode': 'HTML',
        }

        response = requests.post(telegram_url, json=payload)

        if response.status_code == 200:
            return Response({'msg': 'Message sent successfully.'})
        else:
            return Response({'err': 'Failed to send message to Telegram.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
