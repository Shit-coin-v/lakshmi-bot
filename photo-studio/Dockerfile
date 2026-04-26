# Builder для Lakshmi Photo Studio (статичный SPA на Vite).
# Артефакты копируются в shared volume /out, который смонтирован в nginx-контейнер.
FROM node:20-alpine

WORKDIR /src

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Очистить /out и положить туда готовый dist.
# rm -rf нужен, чтобы старые файлы (с другими хешами) не оставались
# в volume между деплоями.
CMD ["sh", "-c", "rm -rf /out/* /out/.* 2>/dev/null; cp -r dist/. /out/"]
