import pathlib, re
p = pathlib.Path("backend/api/security.py")
s = p.read_text(encoding="utf-8")

# гарантируем импорт base64/json (не дублируя)
if "import base64" not in s:
    s = s.replace("import hmac, hashlib", "import hmac, hashlib\nimport base64")
if "import json" not in s:
    s = s.replace("import hmac, hashlib", "import hmac, hashlib\nimport json")

# лог ожидаемых значений (если ещё нет)
if 'expected_b64url' not in s:
    s = s.replace(
        "expected_hex = binascii.hexlify(raw_digest)  # bytes lower-hex",
        "expected_hex = binascii.hexlify(raw_digest)  # bytes lower-hex\n"
        "        logger.info(\"AUTH DEBUG | expected_hex=%s expected_b64url=%s\", "
        "expected_hex.decode(), base64.urlsafe_b64encode(raw_digest).decode().rstrip(\"=\"))"
    )

# запись «последнего запроса» в /tmp перед проверкой ok
inject = r'''
        try:
            with open("/tmp/onec_last.json","w") as f:
                json.dump({
                    "when": int(time.time()),
                    "ip": request.META.get("REMOTE_ADDR"),
                    "ts": ts,
                    "api_key_masked": (api_key[:8] + "...") if api_key else "",
                    "body_b64": base64.b64encode(body).decode(),
                    "body_len": len(body),
                    "provided_sign_raw": sign_in,
                    "normalized_sign": s_in,
                    "mode": "hex" if HEX64_RE.match(s_in) else "b64",
                    "expected_hex": expected_hex.decode(),
                    "expected_b64url": base64.urlsafe_b64encode(raw_digest).decode().rstrip("=")
                }, f, ensure_ascii=False, indent=2)
            logger.info("AUTH DEBUG | snapshot written to /tmp/onec_last.json")
        except Exception as _e:
            logger.warning("AUTH CAPTURE WRITE FAIL: %s", _e)
'''
s = re.sub(r'(\n\s*)if not ok:\s*\n', inject + r'\1if not ok:\n', s, count=1)

p.write_text(s, encoding="utf-8")
print("✅ Patched", p)
