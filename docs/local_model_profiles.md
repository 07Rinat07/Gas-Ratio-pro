# Профили локальных AI-моделей

Этот документ помогает заранее подготовить бесплатный локальный AI runtime,
чтобы помощник продолжал работать на рабочих компьютерах без интернета.

Проект ничего не скачивает автоматически. Каталог профилей только подсказывает,
какую модель выбрать, и дает проверяемые команды для установки через Ollama.

## Где хранятся профили

```text
config/ai_model_profiles.json
```

Структура валидируется тестами и командой preflight.

## Посмотреть доступные профили

```powershell
python scripts/ai_models.py
```

Показать один профиль:

```powershell
python scripts/ai_models.py --profile balanced
```

Вывести JSON для диагностики:

```powershell
python scripts/ai_models.py --json
```

## Текущие профили

| ID | Модель | Когда использовать |
| --- | --- | --- |
| `minimal_cpu` | `llama3.2:3b` | слабые ноутбуки, базовые ответы по документации |
| `balanced` | `qwen3:4b` | рекомендуемый первый вариант для рабочих машин |
| `strong_local` | `qwen3:8b` | более сильные ответы на машинах с запасом RAM |
| `workstation_large` | `gemma3:12b` | рабочие станции, будущая проверка на датасетах |

Оценки RAM в конфиге являются ориентиром. Перед массовым внедрением модель
нужно проверить на реальном компьютере инженера: скорость ответа, качество
русского языка, качество объяснений и стабильность Ollama.

## Подготовить машину до работы без интернета

1. Установить Ollama на рабочий компьютер.
2. Пока интернет доступен, выбрать профиль.
3. Скачать модель командой из `python scripts/ai_models.py --profile <id>`.
4. Проверить список локальных моделей.
5. Указать точное имя модели в `config/ai.json`.
6. Запустить preflight.

Пример для рекомендуемого профиля:

```powershell
python scripts/ai_models.py --profile balanced
ollama pull qwen3:4b
ollama list
```

После загрузки модели настройте `config/ai.json`:

```json
{
  "provider": "ollama",
  "privacy": {
    "send_full_table": false,
    "send_selected_interval_only": true
  },
  "ollama": {
    "base_url": "http://localhost:11434",
    "model": "qwen3:4b",
    "timeout_seconds": 60
  }
}
```

Проверка:

```powershell
python scripts/preflight.py
python scripts/evaluate_ai.py --provider-mode configured
streamlit run app/streamlit_app.py
```

Если модель не найдена или Ollama не запущен, preflight и UI покажут понятное
сообщение. Для слабых машин можно вернуть provider `offline-docs`; он работает
без модели и без интернета.

## Как обновлять каталог

1. Проверить модель и tag в официальной библиотеке Ollama.
2. Добавить профиль в `config/ai_model_profiles.json`.
3. Указать понятный `id`, `model`, ориентир RAM и сценарии применения.
4. Запустить:

```powershell
python -m pytest tests/test_ai_model_profiles.py tests/test_preflight.py
python scripts/preflight.py
```

5. Обновить `CHANGELOG.md`, если профиль добавлен для пользователей.

## Источники

- https://ollama.com/library/llama3.2
- https://ollama.com/library/qwen3
- https://ollama.com/library/gemma3
