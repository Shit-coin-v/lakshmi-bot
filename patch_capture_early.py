import pathlib, re
p = pathlib.Path("backend/api/security.py")
s = p.read_text(encoding="utf-8")

# Гарантируем импорты (без дублей)
for imp in ["import json", "import base64"]:
    if imp not in s:
        s = s.replace("import hmac, hashlib", "import hmac, hashlib\n"+imp)

# Вставляем блок записи снапшота сразу после body=...
pattern = r'(body\s*=\s*request\.body\s*or\s*b""\s*\n)'
inject = (
    "        # EARLY SNAPSHOT: пишем всё сразу, до любых возвратов\n"
    "        try:\n"
    "            body_bytes = body if isinstance(body,(bytes,bytearray)) else str(body).encode('utf-8','surrogatepass')\n"
    "            s_in_local = _normalize_sign(str(sign_in)) if 'sign_in' in locals() else ''\n"
    "            msg_local  = f\"{ts}.\".encode('utf-8') + body_bytes\n"
    "            raw_local  = hmac.new(HMAC_SECRET.encode('utf-8'), msg_local, hashlib.sha256).digest()\n"
    "            snap = {\n"
    "              'when': int(time.time()),\n"
    "              'ip': request.META.get('REMOTE_ADDR'),\n"
    "              'ts': ts,\n"
    "              'api_key_masked': (api_key[:8]+'...') if api_key else '',\n"
    "              'body_b64': base64.b64encode(body_bytes).decode(),\n"
    "              'body_len': len(body_bytes),\n"
    "              'provided_sign_raw': sign_in,\n"
    "              'normalized_sign': s_in_local,\n"
    "              'expected_hex': raw_local.hex(),\n"
    "              'expected_b64url': base64.urlsafe_b64encode(raw_local).decode().rstrip('='),\n"
    "            }\n"
    "            with open('/tmp/onec_last.json','w') as f:\n"
    "                json.dump(snap, f, ensure_ascii=False, indent=2)\n"
    "        except Exception as _e:\n"
    "            logger.warning('AUTH CAPTURE EARLY FAIL: %s', _e)\n"
)
s, n = re.subn(pattern, r"\1"+inject, s, count=1, flags=re.M)
if n == 0:
    raise SystemExit("Не нашёл якорь 'body = request.body or b\"\"' — патч не применён.")

p.write_text(s, encoding="utf-8")
print("✅ Patched:", p)
