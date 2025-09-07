import json
import logging
import requests
from datetime import datetime, timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import PurchaseSerializer
from main.models import CustomUser, Product, Transaction
from src import config

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .security import require_onec_auth

from decimal import Decimal as D, ROUND_HALF_UP
from django.db import transaction as db_tx
from django.utils.dateparse import parse_datetime
from django.utils import timezone as dj_tz
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .security import require_onec_auth
from .serializers import ReceiptSerializer, ProductUpdateSerializer
from .models import OneCClientMap
from django.db import IntegrityError

import hmac, hashlib
from functools import wraps


logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_onec_auth, name='dispatch')
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


@csrf_exempt
@require_POST
@require_onec_auth
def onec_health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
@require_onec_auth
def onec_receipt(request):
    """
    Принимает чек (ISO-8601 datetime с TZ).
    Создаёт позиционные транзакции и обновляет агрегаты клиента.
    Идемпотентность обеспечивается заголовком X-Idempotency-Key
    и уникальностью пары receipt_guid + line_number.
    """
    try:
        # 0) Парсинг JSON из сырого тела (НЕ request.data)
        try:
            payload = json.loads((request.body or b"{}").decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"detail": "invalid_json"}, status=400)

        # 1) Валидация
        ser = ReceiptSerializer(data=payload)
        if not ser.is_valid():
            return JsonResponse({"detail": ser.errors}, status=400)
        data = ser.validated_data

        # 2) Идемпотентность по X-Idempotency-Key
        idem_key = request.headers.get("X-Idempotency-Key")
        if not idem_key:
            return JsonResponse({"detail": "missing idempotency key"}, status=400)
        if Transaction.objects.filter(idempotency_key=idem_key).exists():
            return JsonResponse({"status": "already processed"}, status=200)

        receipt_guid = data["receipt_guid"]

        # 3) Время: у сериализатора datetime — aware (+TZ)
        dt_in = data["datetime"]
        dt_naive = dj_tz.make_naive(dt_in) if dj_tz.is_aware(dt_in) else dt_in
        purchase_date = dt_naive.date()
        purchase_time = dt_naive.time()

        # 4) Клиент: GUID 1C -> telegram_id -> create
        cust = data["customer"]
        telegram_id = cust.get("telegram_id")
        one_c_guid = cust.get("one_c_guid")

        user = None
        if one_c_guid:
            link = OneCClientMap.objects.select_related("user")\
                                        .filter(one_c_guid=one_c_guid).first()
            if link:
                user = link.user

        if not user and telegram_id:
            user = CustomUser.objects.filter(telegram_id=telegram_id).first()

        if not user:
            user = CustomUser.objects.create(telegram_id=telegram_id or None)

        if one_c_guid and not OneCClientMap.objects.filter(one_c_guid=one_c_guid).exists():
            OneCClientMap.objects.create(user=user, one_c_guid=one_c_guid)

        # 5) Тоталы
        totals = data["totals"]
        total_amount   = D(totals["total_amount"])
        discount_total = D(totals["discount_total"])
        bonus_spent    = D(totals["bonus_spent"])
        bonus_earned   = D(totals["bonus_earned"])

        positions = data["positions"]
        created_count = 0
        allocations = []

        # чтобы не делить на ноль
        denom = total_amount if total_amount > 0 else D("1")

        # 6) Позиции (атомарно)
        with db_tx.atomic():
            first = True
            for p in positions:
                code  = p["product_code"]
                name  = p.get("name") or "UNKNOWN"
                qty   = D(p["quantity"])
                price = D(p["price"])
                disc  = D(p.get("discount_amount", 0))
                is_promotional = bool(p.get("is_promotional", False))
                line_number = p["line_number"]

                pos_total = (price - disc) * qty
                pos_bonus_earned = (bonus_earned * (pos_total / denom)).quantize(D("0.01"))

                # Product upsert: кладём только реально существующие поля
                prod_fields = {f.name for f in Product._meta.fields}
                defaults = {}
                if "name" in prod_fields:
                    defaults["name"] = name
                if "price" in prod_fields:
                    defaults["price"] = price
                if "category" in prod_fields and "category" in p:
                    defaults["category"] = p["category"]
                if "is_promotional" in prod_fields:
                    defaults["is_promotional"] = is_promotional
                if "store_id" in prod_fields and "store_id" in data:
                    defaults["store_id"] = data["store_id"]

                product, _ = Product.objects.get_or_create(product_code=code, defaults=defaults)

                # Transaction: тоже только существующие поля
                trx_fields = {f.name for f in Transaction._meta.fields}
                trx_kwargs = {
                    "customer":      user,
                    "product":       product,
                    "quantity":      qty,
                    "total_amount":  pos_total,
                    "bonus_earned":  pos_bonus_earned,
                    "purchase_date": purchase_date,
                    "purchase_time": purchase_time,
                }
                if "store_id" in trx_fields and "store_id" in data:
                    trx_kwargs["store_id"] = data["store_id"]
                if "is_promotional" in trx_fields:
                    trx_kwargs["is_promotional"] = is_promotional
                if "receipt_guid" in trx_fields:
                    trx_kwargs["receipt_guid"] = receipt_guid
                if "receipt_line" in trx_fields:
                    trx_kwargs["receipt_line"] = line_number
                if first and "idempotency_key" in trx_fields:
                    trx_kwargs["idempotency_key"] = idem_key
                    first = False

                try:
                    Transaction.objects.create(**trx_kwargs)
                    created_count += 1
                    allocations.append({
                        "product_code": code,
                        "quantity": float(qty),
                        "total_amount": float(pos_total),
                        "bonus_earned": float(pos_bonus_earned),
                    })
                except IntegrityError:
                    continue

            # 7) Агрегаты клиента
            user.total_spent = (user.total_spent or D("0")) + total_amount
            user.purchase_count = (user.purchase_count or 0) + 1
            user.last_purchase_date = dt_in if settings.USE_TZ else dt_naive
            user.bonuses = (user.bonuses or D("0")) - bonus_spent + bonus_earned
            user.save(update_fields=["total_spent", "purchase_count", "last_purchase_date", "bonuses"])

        # 8) Ответ
        resp = {
            "status": "ok",
            "receipt_guid": receipt_guid,
            "created_count": created_count,
            "allocations": allocations,
            "customer": {
                "telegram_id": user.telegram_id,
                "one_c_guid": one_c_guid or None,
                "bonus_balance": float(user.bonuses or D("0")),
                "total_spent": float(user.total_spent or D("0")),
                "purchase_count": user.purchase_count or 0,
                "last_purchase_date": (dt_in if settings.USE_TZ else dt_naive).isoformat(),
            },
            "totals": {
                "total_amount": float(total_amount),
                "discount_total": float(discount_total),
                "bonus_spent": float(bonus_spent),
                "bonus_earned": float(bonus_earned),
            },
        }

        return JsonResponse(resp, status=201)

    except Exception as e:
        logger.exception("onec_receipt failed: %s", e)
        return JsonResponse(
            {"detail": "internal_error", "error": str(e), "type": type(e).__name__},
            status=500,
        )

@csrf_exempt
@require_POST
@require_onec_auth
def onec_customer_sync(request):
    """
    1С -> Бот: синхронизация клиента

    JSON:
    {
      "one_c_guid": "CUST-1C-0001",
      "telegram_id": 373604254,
      "qr_code": "QR-373604254",
      "bonus_balance": 25.5,
      "created_at": "2025-09-01T12:00:00+09:00",
      "referrer_telegram_id": 111222333   # опционально
    }
    Заголовки: X-Api-Key, X-Timestamp, X-Sign, (опц.) X-Idempotency-Key
    Подпись: sha256( HMAC(secret, f"{TS}." + RAW_BODY) )
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        raw = request.body or b""
        if not raw:
            return JsonResponse({"detail": "empty_body"}, status=400)

        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"detail": "invalid_json"}, status=400)

        # обязательные поля
        required = ["one_c_guid", "telegram_id", "qr_code", "created_at"]
        missing = [k for k in required if not data.get(k)]
        if missing:
            return JsonResponse(
                {"detail": {k: ["Обязательное поле."] for k in missing}}, status=400
            )

        one_c_guid = str(data["one_c_guid"])
        telegram_id = int(data["telegram_id"])
        qr_code = str(data["qr_code"])
        bonus_balance = data.get("bonus_balance", None)
        referrer_tid = data.get("referrer_telegram_id")

        # 1) парсинг ISO 8601
        try:
            dt = datetime.fromisoformat(str(data["created_at"]).replace("Z", "+00:00"))
        except Exception:
            return JsonResponse({"detail": {"created_at": ["Неверный формат datetime"]}}, status=400)

        # 2) нормализация к UTC (как ты хотел)
        if dj_tz.is_naive(dt):
            dt_naive = dt
            dt_aware = dj_tz.make_aware(dt_naive, timezone=timezone.utc)
        else:
            dt_aware = dt
            dt_naive = dj_tz.make_naive(dt_aware, timezone=timezone.utc)

        # находим/создаём клиента по telegram_id
        user, _ = CustomUser.objects.get_or_create(
            telegram_id=telegram_id, defaults={"qr_code": qr_code}
        )

        # обновим qr_code, если изменился
        if qr_code and getattr(user, "qr_code", None) != qr_code:
            user.qr_code = qr_code

        # если передали баланс — положим как есть
        if bonus_balance is not None:
            try:
                user.bonuses = D(str(bonus_balance))
            except Exception:
                return JsonResponse(
                    {"detail": {"bonus_balance": ["Неверное число"]}}, status=400
                )

        # рефералка (если у модели есть поле referrer / referrer_id)
        if referrer_tid:
            try:
                ref_tid = int(referrer_tid)
                if ref_tid and ref_tid != telegram_id:
                    ref_user = CustomUser.objects.filter(telegram_id=ref_tid).first()
                    if (
                        ref_user
                        and hasattr(user, "referrer_id")
                        and not getattr(user, "referrer_id")
                    ):
                        user.referrer = ref_user
            except Exception:
                # мягко игнорируем любые проблемы с парсингом/поиском реферала
                pass

        # опционально сохраняем дату создания, если поле есть и пустое
        try:
            if hasattr(user, "created_at") and not user.created_at:
                user.created_at = dt_aware if settings.USE_TZ else dt_naive
        except Exception:
            pass

        # сохраняем все изменения одной операцией
        user.save()

        # карта соответствия 1С <-> клиент
        OneCClientMap.objects.update_or_create(
            one_c_guid=one_c_guid, defaults={"user": user}
        )

        resp = {
            "status": "ok",
            "customer": {
                "telegram_id": user.telegram_id,
                "one_c_guid": one_c_guid,
                "qr_code": user.qr_code,
                "bonus_balance": float(user.bonuses or 0),
                "referrer_telegram_id": getattr(getattr(user, "referrer", None), "telegram_id", None),
            },
        }
        return JsonResponse(resp, status=200)

    except Exception as e:
        logger.exception("onec_customer_sync unhandled error")
        return JsonResponse(
            {"detail": "internal_error", "error": str(e), "type": e.__class__.__name__},
            status=500,
        )


@csrf_exempt
@require_POST
@require_onec_auth
def onec_product_sync(request):
    """1С -> Бот: обновление номенклатуры"""
    try:
        try:
            payload = json.loads((request.body or b"{}").decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"detail": "invalid_json"}, status=400)

        ser = ProductUpdateSerializer(data=payload)
        if not ser.is_valid():
            return JsonResponse({"detail": ser.errors}, status=400)
        data = ser.validated_data

        defaults = {
            "one_c_guid": data.get("one_c_guid"),
            "name": data["name"],
            "price": data["price"],
            "category": data["category"],
            "is_promotional": data["is_promotional"],
        }
        if hasattr(Product, 'store_id'):
            defaults.setdefault('store_id', 0)
        product, created = Product.objects.update_or_create(
            product_code=data["product_code"], defaults=defaults
        )

        resp = {
            "status": "created" if created else "updated",
            "product": {
                "product_code": product.product_code,
                "one_c_guid": product.one_c_guid,
                "name": product.name,
                "price": float(product.price),
                "category": product.category,
                "is_promotional": product.is_promotional,
            },
        }
        return JsonResponse(resp, status=201 if created else 200)

    except Exception as e:
        logger.exception("onec_product_sync failed: %s", e)
        return JsonResponse({"detail": "internal_error", "error": str(e)}, status=500)

