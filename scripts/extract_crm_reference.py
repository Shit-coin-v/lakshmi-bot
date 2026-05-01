#!/usr/bin/env python3
"""Распаковать Lakshmi CRM.html (Claude.ai artifact bundle) в crm-web/.reference/.
Одноразовый скрипт — нужен только при портировании прототипа.
"""
import re, json, base64, gzip, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Lakshmi CRM.html")
OUT = os.path.join(ROOT, "crm-web", ".reference")

if not os.path.exists(SRC):
    sys.exit(f"Не найден файл: {SRC}")

os.makedirs(OUT, exist_ok=True)
html = open(SRC, encoding="utf-8").read()

m_manifest = re.search(r'<script type="__bundler/manifest">\s*(.+?)\s*</script>', html, re.DOTALL)
m_template = re.search(r'<script type="__bundler/template">\s*(.+?)\s*</script>', html, re.DOTALL)
if not (m_manifest and m_template):
    sys.exit("Не найдены теги manifest/template — проверь, что входной файл — это Claude artifact bundle")

manifest = json.loads(m_manifest.group(1))
template = json.loads(m_template.group(1))

with open(os.path.join(OUT, "_template.html"), "w", encoding="utf-8") as f:
    f.write(template)

EXT_MAP = {
    "application/javascript": "js",
    "image/svg+xml": "svg",
    "font/woff2": "woff2",
    "image/png": "png",
}

for uuid, entry in manifest.items():
    data = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        data = gzip.decompress(data)
    ext = EXT_MAP.get(entry["mime"], "bin")
    out_path = os.path.join(OUT, f"{uuid}.{ext}")
    with open(out_path, "wb") as f:
        f.write(data)

print(f"Распаковано {len(manifest)} ассетов в {OUT}")
