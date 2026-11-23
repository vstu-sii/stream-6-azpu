# stream-6-azpu
2026, 6 курс · AZPU

## AI-прототип AZPU

API проверяет один текст резюме по требованиям вакансии и возвращает цитаты,
которые рекрутер может сверить с исходником. Для неподтверждённого критерия
появляется вопрос для интервью. В прототипе использованы синтетические данные.

1. Установите Python 3.12 и зависимости: `python -m pip install -r requirements.txt`.
2. Возьмите GGUF из [карточки эксперимента](docs/experiments/lab3.md) и задайте
   путь в `AZPU_MODEL_PATH`. Для PowerShell:
   `$env:AZPU_MODEL_PATH = 'C:\models\qwen3-4b.gguf'`.
3. Запустите `python -m uvicorn backend.app:app`. Откройте
   [интерактивный API](http://127.0.0.1:8000/docs), вызовите
   `POST /v1/ai/assessments`. Пример запроса и ответа есть в
   [контракте](api/openapi.yaml).

[Архитектура](docs/ai-pipeline.md) · [Прогоны и метрики](docs/experiments/lab3.md)
· [Трассировка модели](ml/tracing/README.md)
