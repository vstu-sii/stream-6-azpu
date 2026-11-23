# Отбор резюме под вакансию

2026, 6 курс · AZPU

## Структура

- `site/index.html` — стартовая страница проекта.
- `compose.yaml` — локальная среда с nginx.
- `.github/workflows/ci.yml` — проверка запуска Compose и ответа стартовой страницы.

## Локальный запуск

Установите Docker с Compose и выполните `docker compose up -d` из корня репозитория.
Страница доступна по адресу http://127.0.0.1:8080/.
Для остановки выполните `docker compose down`.

## Публичная демонстрация

[Hello World](https://ziifurs.github.io/azpu-lab1-demo/)

## Лабораторная №2. Архитектура и dev-среда

- [Контекст C4](docs/architecture/context.puml) показывает рекрутера, систему AZPU и поставщика модели.
- [Контейнеры C4](architecture.puml) описывают веб-интерфейс и API оценки. Внутри API запланированы подготовка контекста и проверка свидетельств из ответа модели.
- `compose.dev.yml` и `dev/*.conf` поднимают веб-заглушку и заглушку API без резюме, ключей и сетевых обращений к модели.

Проверка архитектуры из корня репозитория:

```sh
npx --yes aact@beta check
```

Запуск заглушек и проверка маршрута от веб-сервиса до API:

```sh
docker compose -f compose.dev.yml up -d --wait
curl -fsS http://127.0.0.1:8080/
curl -fsS http://127.0.0.1:8080/api/healthz
docker compose -f compose.dev.yml down
```

Запрос `POST /api/v1/ai/assessments` возвращает HTTP 501 до реализации оценки резюме.
