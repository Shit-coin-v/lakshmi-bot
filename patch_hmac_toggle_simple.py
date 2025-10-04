import pathlib, re

p = pathlib.Path("backend/api/security.py")
s = p.read_text(encoding="utf-8")
changed = False

# 0) import os если вдруг нет
if re.search(r'^\s*import os\b', s, re.M) is None:
    s = s.replace("import hmac", "import os\nimport hmac", 1)
    changed = True

# 1) Добавим глобальный флаг DISABLE_HMAC после MAX_SKEW (один раз)
if "DISABLE_HMAC" not in s and "ONEC_HMAC_DISABLED" not in s:
    s, n = re.subn(
        r'(MAX_SKEW\s*=\s*int\([^\n]+\)\s*\n)',
        r'\1DISABLE_HMAC = (os.getenv("ONEC_HMAC_DISABLED","").lower() in ("1","true","yes","on"))\n',
        s, count=1
    )
    changed |= bool(n)

# 2) Разрешить пустой HMAC_SECRET при выключенном HMAC
s2, n = re.subn(
    r'if\s+not\s+API_KEY\s+or\s+not\s+HMAC_SECRET:\s*return\s+_bad\(401,\s*"Server auth not configured"\s*\)',
    'if not API_KEY or (not HMAC_SECRET and not DISABLE_HMAC):\n                return _bad(401, "Server auth not configured")',
    s
)
if n: s = s2; changed = True

# 3) Гибкая проверка обязательных заголовков
s2, n = re.subn(
    r'if\s+not\s+api_key\s+or\s+not\s+ts\s+or\s+not\s+sign_in:\s*return\s+_bad\(401,\s*"Missing auth headers"\s*\)',
    'if (DISABLE_HMAC and not api_key) or (not DISABLE_HMAC and (not api_key or not ts or not sign_in)):\n                return _bad(401, "Missing auth headers")',
    s
)
if n: s = s2; changed = True

# 4) Ранний выход, если HMAC выключен (после проверки API key)
if "HMAC DISABLED TEMP" not in s:
    s2, n = re.subn(
        r'(if\s+api_key\s*!=\s*API_KEY:\s*return\s+_bad\(401,\s*"Bad api key"[^)]*\)|'
        r'if\s+api_key\s*!=\s*API_KEY:\s*return\s+_bad\(401,\s*"Bad API key"\s*\))',
        r'\1\n            if DISABLE_HMAC:\n                logger.warning("HMAC DISABLED TEMP | ip=%s path=%s", _client_ip(request), getattr(request, "path", "?"))\n                return view_func(request, *args, **kwargs)',
        s, count=1, flags=re.I
    )
    if n: s = s2; changed = True

if changed:
    p.write_text(s, encoding="utf-8")
    print("✅ Patched", p)
else:
    print("ℹ️ Nothing changed")
