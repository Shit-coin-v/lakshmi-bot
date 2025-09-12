import pathlib, re
p = pathlib.Path("backend/api/security.py")
s = p.read_text(encoding="utf-8")

# 1) После внутреннего импорта добавить флаг disabled
s = s.replace(
    "from .security import API_KEY, HMAC_SECRET, MAX_SKEW, _ip_allowed",
    "from .security import API_KEY, HMAC_SECRET, MAX_SKEW, _ip_allowed\n"
    "            disabled = (os.getenv(\"ONEC_HMAC_DISABLED\",\"\" ).lower() in (\"1\",\"true\",\"yes\",\"on\"))"
)

# 2) Не падать при пустом HMAC_SECRET, если disabled
s = re.sub(
    r"if not API_KEY or not HMAC_SECRET:\s*return _bad\(401, \"Server auth not configured\"\)",
    "if not API_KEY or (not HMAC_SECRET and not disabled):\n"
    "                return _bad(401, \"Server auth not configured\")",
    s
)

# 3) Гибкая проверка обязательных заголовков
s = re.sub(
    r"if not api_key or not ts or not sign_in:\s*return _bad\(401, \"Missing auth headers\"\)",
    "if (disabled and not api_key) or (not disabled and (not api_key or not ts or not sign_in)):\n"
    "                return _bad(401, \"Missing auth headers\")",
    s
)

# 4) Ранний выход в режиме disabled (после проверки API key)
s = re.sub(
    r"if api_key != API_KEY:\s*return _bad\(401, \"Bad API key\"\)",
    "if api_key != API_KEY:\n"
    "                return _bad(401, \"Bad API key\")\n"
    "            if disabled:\n"
    "                logger.warning(\"HMAC DISABLED TEMP | ip=%s path=%s\", _client_ip(request), getattr(request, 'path', '?'))\n"
    "                return view_func(request, *args, **kwargs)",
    s
)

p.write_text(s, encoding="utf-8")
print(\"✅ Patched:\", p)
