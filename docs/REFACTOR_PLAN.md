# План рефакторинга V4 для lakshmi-bot

## Статус: ⏳ ОЖИДАНИЕ ПОДТВЕРЖДЕНИЯ

## Цели V4
- Зарегистрировать доменные приложения в INSTALLED_APPS
- Устранить промежуточные прокси-слои (push_contract, task_contract, main/push)
- Переместить сериализаторы из apps/api в доменные приложения
- Исправить оставшиеся except Exception паттерны
- Очистить apps/api/serializers.py от реэкспортов

---

## План из 10 шагов

### Шаг 1: Зарегистрировать доменные приложения в INSTALLED_APPS (P0)
**Файл:** `backend/settings.py`

**Текущее состояние:** Только `apps.main` и `apps.api` зарегистрированы.

**Изменения:**
- Добавить в INSTALLED_APPS:
  - `apps.orders.apps.OrdersConfig`
  - `apps.loyalty.apps.LoyaltyConfig`
  - `apps.notifications.apps.NotificationsConfig`
  - `apps.integrations.onec.apps.OnecConfig`
  - `apps.common.apps.CommonConfig`

**Критерий:** `python -m compileall backend` → успех

---

### Шаг 2: Исправить except Exception без pragma (P0)
**Файлы с except Exception БЕЗ pragma: no cover:**
- `backend/apps/notifications/tasks.py:36`
- `backend/apps/main/signals.py:60`
- `backend/apps/integrations/onec/order_status.py:92`
- `backend/apps/integrations/onec/order_sync.py:125`

**Изменения:**
- Заменить `except Exception` на специфичные исключения (`requests.RequestException`, `ValueError`, `KeyError`, и т.д.)
- Или добавить `# pragma: no cover` с обоснованием для defensive code

**Критерий:** `grep -rn "except Exception" backend/apps/ | grep -v "pragma: no cover" | grep -v test | grep -v __pycache__` → 0 совпадений

---

### Шаг 3: Устранить цепочку push-прокси (P1)
**Проблема:** Двойная цепочка прокси:
```
signals.py → push_contract.py → main/push.py → notifications/push.py
views.py → push_contract.py → main/push.py → notifications/push.py
```

**Изменения:**
1. Обновить `backend/apps/main/signals.py` — импорт напрямую из `apps.notifications.push`
2. Обновить все вызовы, которые используют `push_contract.py`, на прямой импорт из `apps.notifications.push`
3. Удалить `backend/apps/notifications/push_contract.py`
4. Удалить `backend/apps/main/push.py` (прокси-файл)

**Критерий:** `rg -n "push_contract" backend/` → 0 совпадений; `python -m compileall backend` → успех

---

### Шаг 4: Удалить task_contract.py файлы (P1)
**Файлы:**
- `backend/apps/notifications/task_contract.py` — прокси для broadcast_send_task
- `backend/apps/integrations/onec/task_contract.py` — прокси для send_order_to_onec

**Изменения:**
1. Найти все использования task_contract и заменить на прямые вызовы .delay()
2. Обновить `backend/apps/api/serializers.py:218` — заменить import из task_contract на прямой
3. Обновить `backend/apps/main/admin.py` — заменить import из task_contract на прямой
4. Удалить оба файла task_contract.py

**Критерий:** `rg -n "task_contract" backend/` → 0 совпадений; `python -m compileall backend` → успех

---

### Шаг 5: Перенести PurchaseSerializer в apps/loyalty (P1)
**Файлы:**
- Источник: `backend/apps/api/serializers.py` (PurchaseSerializer, строки 20-37)
- Цель: `backend/apps/loyalty/serializers.py`

**Изменения:**
1. Создать/обновить `backend/apps/loyalty/serializers.py` с PurchaseSerializer
2. Обновить импорт в `backend/apps/loyalty/views.py`
3. Удалить PurchaseSerializer из `backend/apps/api/serializers.py`

**Критерий:** `ruff check backend/apps/loyalty/serializers.py` → успех

---

### Шаг 6: Перенести CustomerProfileSerializer в apps/main (P1)
**Файлы:**
- Источник: `backend/apps/api/serializers.py` (CustomerProfileSerializer, строки 225-238)
- Цель: `backend/apps/main/serializers.py`

**Изменения:**
1. Создать `backend/apps/main/serializers.py` с CustomerProfileSerializer
2. Обновить импорт в `backend/apps/main/views.py`
3. Удалить CustomerProfileSerializer из `backend/apps/api/serializers.py`

**Критерий:** `ruff check backend/apps/main/serializers.py` → успех

---

### Шаг 7: Перенести Receipt-сериализаторы в apps/integrations/onec (P2)
**Файлы:**
- Источник: `backend/apps/api/serializers.py` (ReceiptPositionSerializer, ReceiptTotalsSerializer, ReceiptCustomerSerializer, ReceiptSerializer, ProductUpdateSerializer)
- Цель: `backend/apps/integrations/onec/serializers.py`

**Изменения:**
1. Создать `backend/apps/integrations/onec/serializers.py`
2. Перенести 5 сериализаторов (Receipt*, ProductUpdate*)
3. Обновить импорты в `backend/apps/integrations/onec/receipt.py` и `product_sync_endpoint.py`
4. Удалить перенесённые классы из `backend/apps/api/serializers.py`

**Критерий:** `ruff check backend/apps/integrations/onec/serializers.py` → успех

---

### Шаг 8: Перенести OrderCreateSerializer и OrderItemSerializer в apps/orders (P2)
**Файлы:**
- Источник: `backend/apps/api/serializers.py` (OrderItemSerializer, OrderCreateSerializer)
- Цель: `backend/apps/orders/serializers.py`

**Изменения:**
1. Перенести OrderItemSerializer и OrderCreateSerializer в `backend/apps/orders/serializers.py`
2. Обновить импорты (task_contract заменён на шаге 4)
3. Удалить перенесённые классы из `backend/apps/api/serializers.py`

**Критерий:** `ruff check backend/apps/orders/serializers.py` → успех

---

### Шаг 9: Очистить apps/api/serializers.py от реэкспортов (P2)
**Файл:** `backend/apps/api/serializers.py`

**Текущее состояние:** Содержит `# noqa: F401` реэкспорты из notifications и orders.

**Изменения:**
1. Проверить, что apps/api/urls.py НЕ импортирует сериализаторы из api (подтверждено — urls.py импортирует views)
2. Удалить реэкспорт-импорты (строки 7-17)
3. Удалить неиспользуемые импорты моделей после переноса сериализаторов
4. После шагов 5-8 файл должен стать пустым → удалить файл

**Критерий:** `rg -n "noqa: F401" backend/apps/api/serializers.py` → 0 совпадений или файл удалён

---

### Шаг 10: Верификация и обновление документации (P2)
**Проверки:**
1. `python -m compileall backend` → успех
2. `ruff check backend/` → успех (или только ожидаемые warnings)
3. `grep -rn "push_contract\|task_contract" backend/` → 0 совпадений
4. `grep -rn "except Exception" backend/apps/ | grep -v "pragma: no cover" | grep -v test | grep -v __pycache__` → 0 совпадений
5. Проверить PYTHONPATH импорты: `PYTHONPATH=backend python -c "from apps.api import urls; print('ok')"`

**Документация:**
- Обновить `docs/AGENT_WORKLOG.md` с записью о V4

---

## Сводная таблица

| Шаг | Приоритет | Описание | Сложность |
|-----|-----------|----------|-----------|
| 1 | P0 | INSTALLED_APPS — регистрация доменных приложений | Низкая |
| 2 | P0 | except Exception — специфичные исключения | Низкая |
| 3 | P1 | Удалить push-прокси цепочку | Средняя |
| 4 | P1 | Удалить task_contract.py прокси | Средняя |
| 5 | P1 | PurchaseSerializer → loyalty | Низкая |
| 6 | P1 | CustomerProfileSerializer → main | Низкая |
| 7 | P2 | Receipt* сериализаторы → integrations/onec | Средняя |
| 8 | P2 | OrderCreate/Item сериализаторы → orders | Средняя |
| 9 | P2 | Очистка api/serializers.py | Низкая |
| 10 | P2 | Верификация и документация | Низкая |

---

## Порядок выполнения

```
Шаг 1 → Шаг 2 → Шаг 3 → Шаг 4 → Шаг 5 → Шаг 6 → Шаг 7 → Шаг 8 → Шаг 9 → Шаг 10
```

Шаги 3-4 (прокси) должны быть выполнены ДО шагов 5-8 (сериализаторы), так как сериализаторы используют task_contract.

---

## Верификация

```bash
# 1. Компиляция
python -m compileall backend

# 2. Линтер
ruff check backend/

# 3. Прокси удалены
grep -rn "push_contract\|task_contract" backend/
# Ожидается: 0 совпадений

# 4. except Exception исправлены
grep -rn "except Exception" backend/apps/ | grep -v "pragma: no cover" | grep -v test | grep -v __pycache__
# Ожидается: 0 совпадений

# 5. Импорт urls
PYTHONPATH=backend python -c "from apps.api import urls; print('ok')"
# Ожидается: ok

# 6. Реэкспорты удалены
grep -rn "noqa: F401" backend/apps/api/
# Ожидается: 0 совпадений
```
