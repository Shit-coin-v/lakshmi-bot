# Lakshmi Bot — Project Rules

## Общие принципы

- Проект: lakshmi-bot
- Backend: Django + DRF
- Frontend: Flutter
- Инфраструктура: Docker + Nginx
- Авторизация интеграций: X-Api-Key (без HMAC)

Claude обязан:

- Работать строго по фактам из репозитория.
- Не менять бизнес-смысл без явного разрешения.
- Перед крупными изменениями сначала писать план.
- Для API:
  - учитывать serializers
  - permissions
  - authentication_classes
  - middleware

## API

- Контракты должны соответствовать serializers + views.
- Несоответствия считаются багами и подлежат исправлению.
- Разрешено чинить:
  - serializers
  - views
  - permissions
  - urls
- Запрещено:
  - менять модели без согласования.

## Workflow

- План → подтверждение → реализация.
- После работы:
  - git status
  - git diff

## Стиль

- Без маркетинговых описаний.
- Только инженерный язык.
