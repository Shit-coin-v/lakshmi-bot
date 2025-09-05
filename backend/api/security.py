import os
import hmac
import time
import hashlib
from functools import wraps
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

API_KEY = os.getenv("INTEGRATION_API_KEY", "")
HMAC_SECRET = os.getenv("INTEGRATION_HMAC_SECRET", "")
MAX_SKEW = int(os.getenv("HMAC_MAX_SKEW_SECONDS", "300"))

def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.META.get("HTTP_X_REAL_IP")
    if xri:
        return xri.strip()
    return request.META.get("REMOTE_ADDR", "")

def _ip_allowed(request):
    allowed_raw = os.getenv("ALLOWED_IPS", "").strip()
    if not allowed_raw:
        return True
    allowed = {ip.strip() for ip in allowed_raw.split(",") if ip.strip()}
    return _client_ip(request) in allowed

def _bad(status, msg):
    return JsonResponse({"detail": msg}, status=status)

def require_onec_auth(view_func):
    """
    Проверяет:
      - IP по белому списку (если задан)
      - заголовки X-Api-Key, X-Timestamp, X-Sign
      - окно времени +/- MAX_SKEW
      - HMAC-SHA256 по строке: f"{timestamp}." + raw_body
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not API_KEY or not HMAC_SECRET:
            return _bad(401, "Server auth not configured")
        if not _ip_allowed(request):
            return _bad(403, "IP not allowed")

        api_key = request.META.get("HTTP_X_API_KEY")
        ts = request.META.get("HTTP_X_TIMESTAMP")
        sign = request.META.get("HTTP_X_SIGN")
        if not api_key or not ts or not sign:
            return _bad(401, "Missing auth headers")
        if api_key != API_KEY:
            return _bad(401, "Bad API key")

        try:
            ts_int = int(ts)
        except (TypeError, ValueError):
            return _bad(401, "Bad timestamp")

        now = int(time.time())
        if abs(now - ts_int) > MAX_SKEW:
            return _bad(401, "Stale timestamp")

        # Django кэширует request.body после первого чтения
        body = request.body or b""
        expected = hmac.new(HMAC_SECRET.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sign):
            return _bad(401, "Bad signature")

        return view_func(request, *args, **kwargs)
    return _wrapped
