import re, pathlib

p = pathlib.Path("backend/api/security.py")
s = p.read_text(encoding="utf-8")

# Гарантируем недостающие импорты
need = []
if "import binascii" not in s:   need.append("import binascii")
if "import unicodedata" not in s: need.append("import unicodedata")
if "import re" not in s:          need.append("import re")
if need:
    s = s.replace("import hmac, hashlib", "import hmac, hashlib\n" + "\n".join(need))

new_func = '''
def require_onec_auth(view_func):
    """
    HMAC-SHA256 по строке f"{ts}."+body; допускаем X-Sign в hex или base64/base64url.
    Сравнение на уровне байт + нормализация входа (без non-ASCII).
    """
    from functools import wraps
    import time, hmac, hashlib, binascii, re, unicodedata
    from django.http import JsonResponse
    import logging
    logger = logging.getLogger(__name__)

    HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")
    INVISIBLES = {"\\u00A0","\\u200B","\\u200C","\\u200D","\\uFEFF","\\u2060"}

    def _bad(code, detail):
        return JsonResponse({"detail": detail}, status=code)

    def _normalize_sign(s: str) -> str:
        s = unicodedata.normalize("NFKC", s or "")
        trans = {ord("А"):"A", ord("а"):"a", ord("Е"):"E", ord("е"):"e", ord("С"):"C", ord("с"):"c"}
        s = s.translate(trans)
        for ch in list(INVISIBLES):
            s = s.replace(ch, "")
        return s.strip()

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        try:
            from .security import API_KEY, HMAC_SECRET, MAX_SKEW, _ip_allowed
            if not API_KEY or not HMAC_SECRET:
                return _bad(401, "Server auth not configured")
            if not _ip_allowed(request):
                return _bad(403, "IP not allowed")

            api_key = request.META.get("HTTP_X_API_KEY")
            ts      = request.META.get("HTTP_X_TIMESTAMP")
            sign_in = request.META.get("HTTP_X_SIGN", "")
            if not api_key or not ts or not sign_in:
                return _bad(401, "Missing auth headers")
            if api_key != API_KEY:
                return _bad(401, "Bad API key")

            try:
                ts_int = int(str(ts))
            except Exception:
                return _bad(401, "Bad timestamp")

            if abs(int(time.time()) - ts_int) > MAX_SKEW:
                return _bad(401, "Stale timestamp")

            body = request.body or b""
            msg  = f"{ts}.".encode("utf-8") + body
            raw_digest = hmac.new(HMAC_SECRET.encode("utf-8"), msg, hashlib.sha256).digest()
            expected_hex = binascii.hexlify(raw_digest)  # bytes lower-hex

            s_in = _normalize_sign(str(sign_in))
            if HEX64_RE.match(s_in):
                ok = hmac.compare_digest(expected_hex, s_in.lower().encode("ascii"))
            else:
                s_b64 = s_in.replace("-", "+").replace("_", "/")
                pad   = "=" * ((4 - len(s_b64) % 4) % 4)
                try:
                    sign_raw = binascii.a2b_base64(s_b64 + pad)
                except (binascii.Error, ValueError):
                    logger.warning("X-Sign invalid b64: %r", s_in[:48])
                    return _bad(401, "Bad signature encoding")
                ok = hmac.compare_digest(raw_digest, sign_raw)

            if not ok:
                return _bad(401, "Bad signature")
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.exception("require_onec_auth crashed: %s", e)
            return _bad(401, "Bad signature")
    return _wrapped
'''

# Точно заменяем старую функцию на новую (без подводных камней \u)
pattern = re.compile(r'def\s+require_onec_auth\s*\([^)]*\):.*?^\s*return\s+_wrapped\s*\n\s*', re.S|re.M)
if pattern.search(s):
    s = pattern.sub(lambda m: new_func + "\n", s, count=1)
else:
    s += "\n" + new_func + "\n"

p.write_text(s, encoding="utf-8")
print("✅ Patched:", p)
