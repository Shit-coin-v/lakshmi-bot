# План рефакторинга V3 для lakshmi-bot

## Цели V3
- Устранить оставшийся технический долг
- Разорвать зависимость backend → bots
- Консолидировать Celery tasks в доменных приложениях
- Улучшить качество кода (exception handling)

---

## План из 10 шагов

### Шаг 1: Исправить except Exception в security.py (P0)
**Файл:** `backend/apps/common/security.py:96`

**Изменения:**
- Заменить `except Exception:` на специфичные исключения
- Добавить комментарий с обоснованием для defensive code

**Критерий:** `grep -rn "except Exception:" backend/apps/common/security.py` → 0 совпадений

---

### Шаг 2: Заменить print() на logger (P0)
**Файл:** `backend/apps/api/tasks.py:36`

**Изменения:**
- Заменить `print(f"Ошибка...")` на `logger.error(...)`
- Добавить импорт logger если отсутствует

**Критерий:** `grep -rn "print(" backend/apps/ | grep -v test` → 0 совпадений

---

### Шаг 3: Создать shared/broadcast/ модуль (P1)
**Цель:** Подготовить структуру для переноса broadcast логики

**Изменения:**
1. Создать `shared/broadcast/__init__.py`
2. Создать `shared/broadcast/django_sender.py`
3. Перенести `_send_with_django()` из `bots/customer_bot/broadcast.py`

**Структура:**
```
shared/
├── config/qr.py
└── broadcast/
    ├── __init__.py
    └── django_sender.py
```

---

### Шаг 4: Обновить импорты broadcast в backend (P1)
**Файл:** `backend/apps/main/tasks.py:24`

**Изменения:**
- Заменить `from bots.customer_bot.broadcast import _send_with_django`
- На `from shared.broadcast import send_with_django`

**Критерий:** `grep -rn "from bots\." backend/` → только тесты

---

### Шаг 5: Перенести send_birthday_congratulations (P1)
**Файлы:**
- `backend/apps/api/tasks.py` (источник)
- `backend/apps/notifications/tasks.py` (цель)

**Изменения:**
1. Перенести функцию `send_birthday_congratulations` в notifications/tasks.py
2. Удалить legacy wrapper
3. Обновить Celery beat schedule если есть

---

### Шаг 6: Создать integrations/onec/tasks.py (P2)
**Файл:** `backend/apps/integrations/onec/tasks.py` (новый)

**Изменения:**
1. Создать файл tasks.py в integrations/onec/
2. Перенести `send_order_to_onec` из apps/api/tasks.py
3. Обновить импорты

---

### Шаг 7: Удалить apps/api/tasks.py (P2)
**Файл:** `backend/apps/api/tasks.py`

**Изменения:**
1. Убедиться что все задачи перенесены (шаги 5-6)
2. Удалить файл
3. Обновить все импорты в проекте

**Целевая структура tasks:**
```
apps/notifications/tasks.py → send_birthday_congratulations
apps/integrations/onec/tasks.py → send_order_to_onec
apps/main/tasks.py → broadcast_send_task
```

---

### Шаг 8: Консолидация импортов моделей (P2)
**Цель:** Установить консистентный паттерн импортов

**Правило:**
- `CustomUser`, `Transaction` → `apps.loyalty.models`
- `Order`, `OrderItem`, `Product` → `apps.orders.models`
- `Notification`, `NotificationOpenEvent` → `apps.notifications.models`

**Изменения:**
1. Обновить импорты в `apps/integrations/onec/*.py`
2. Расширить фасады при необходимости

---

### Шаг 9: Документирование пустых интеграций (P2)
**Файлы:**
- `apps/integrations/payments/README.md` (создать)
- `apps/integrations/delivery/README.md` (создать)

**Изменения:**
1. НЕ удалять приложения
2. НЕ подключать в INSTALLED_APPS
3. Добавить README.md с описанием планируемого назначения:
   - payments/ — будущая интеграция с платёжными системами
   - delivery/ — будущая интеграция с сервисами доставки

---

### Шаг 10: Улучшение exception handling (P2)
**Файлы для ревью:**
- `apps/integrations/onec/order_sync.py:109`
- `apps/integrations/onec/customer_sync.py:63, 123`
- `apps/notifications/views.py:91`

**Изменения:**
- Заменить `except Exception:` на специфичные исключения
- Для defensive code добавить комментарий `# pragma: no cover`

---

## Сводная таблица

| Шаг | Приоритет | Описание | Сложность |
|-----|-----------|----------|-----------|
| 1 | P0 | except Exception в security.py | Низкая |
| 2 | P0 | print() → logger | Низкая |
| 3 | P1 | Создать shared/broadcast/ | Средняя |
| 4 | P1 | Импорты broadcast в backend | Низкая |
| 5 | P1 | Перенос birthday task | Низкая |
| 6 | P2 | Создать onec/tasks.py | Низкая |
| 7 | P2 | Удалить api/tasks.py | Низкая |
| 8 | P2 | Импорты моделей | Средняя |
| 9 | P2 | README для интеграций | Низкая |
| 10 | P2 | Exception handling | Низкая |

---

## Порядок выполнения

```
Шаг 1 → Шаг 2 → Шаг 3 → Шаг 4 → Шаг 5 → Шаг 6 → Шаг 7
                                                    ↓
                                          Шаги 8, 9, 10
```

---

## Верификация

```bash
# 1. Проверка границ backend/bots
grep -rn "from bots\." backend/
# Ожидается: только тесты

# 2. Проверка print statements
grep -rn "print(" backend/apps/ | grep -v test
# Ожидается: 0 совпадений

# 3. Проверка except Exception в security
grep -rn "except Exception:" backend/apps/common/security.py
# Ожидается: 0 совпадений

# 4. Компиляция
python -m compileall backend

# 5. Линтер
ruff check backend/

# 6. Тесты
cd backend && python manage.py test

# 7. Celery tasks
# Проверить broadcast_send_task
# Проверить send_birthday_congratulations
# Проверить send_order_to_onec
```
