# Локальный ИИ-помощник

Проект поддерживает offline-first подход: помощник должен оставаться полезным
даже без интернета.

## Текущий режим

По умолчанию используется provider:

```text
offline-docs
```

Он не обращается к интернету и не требует локальной модели. Ответ строится по
локальной документации из `docs/` и безопасному контексту выбранного интервала.

## Локальная база знаний

Список документов и Q/A-примеров, доступных помощнику, хранится в:

```text
config/knowledge_sources.json
config/knowledge_qa.json
```

Проверить manifest и поиск можно командами:

```powershell
python scripts/knowledge_base.py
python scripts/knowledge_base.py --query "Как считается Wh?"
python scripts/knowledge_base.py --query "Почему Wh стал NaN из-за C2?"
python scripts/evaluate_ai.py
python scripts/evaluate_ai.py --provider-mode configured
```

Подробности описаны в `docs/knowledge_base.md` и `docs/ai_evaluation.md`.

## Конфигурация

Файл:

```text
config/ai.json
```

Посмотреть текущий provider:

```powershell
python scripts/ai_config.py status
```

Пример:

```json
{
  "provider": "offline-docs",
  "privacy": {
    "send_full_table": false,
    "send_selected_interval_only": true
  },
  "ollama": {
    "base_url": "http://localhost:11434",
    "model": "",
    "timeout_seconds": 60
  }
}
```

## Локальная модель через Ollama

Перед настройкой модели посмотрите проверяемые профили:

```powershell
python scripts/ai_models.py
python scripts/ai_models.py --profile balanced
python scripts/setup_local_agent.py --profile balanced
python scripts/ai_config.py ollama --profile balanced
python scripts/ai_config.py ollama --profile balanced --write
```

Подробный чеклист: `docs/local_ai_agent.md` и `docs/local_model_profiles.md`.

Чтобы использовать локальную модель, нужно:

1. Установить Ollama на рабочий компьютер.
2. Скачать модель заранее, пока интернет доступен.
3. Проверить, что Ollama работает локально.
4. Указать имя модели в `config/ai.json`.
5. Поменять provider на `ollama`.
6. Запустить `python scripts/preflight.py`.

Пример:

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

Приложение обращается только к локальному адресу `localhost`. Внешние облачные
API не используются.

## Проверка готовности

Перед запуском можно проверить AI runtime командой:

```powershell
python scripts/preflight.py
```

В блоке `Локальный ИИ-помощник` приложение показывает статус provider:

- `offline-docs` готов всегда и не требует интернета; вернуть этот режим можно командой `python scripts/ai_config.py offline-docs --write`;
- `ollama` готов только если локальный сервис отвечает и указанная модель найдена;
- если модель не указана или не загружена, приложение покажет понятное предупреждение;
- интерфейс показывает команды подготовки профиля `balanced` в блоке AI runtime.

Для подготовки рабочих машин заранее:

1. Установите Ollama там, где будет запускаться проект.
2. Пока интернет доступен, выберите профиль через `python scripts/ai_models.py`.
3. Скачайте выбранную модель через `python scripts/setup_local_agent.py --profile balanced --download`.
4. Проверьте локальный список моделей командой `ollama list`.
5. Укажите точное имя модели в `config/ai.json`.
6. Запустите приложение и убедитесь, что статус Ollama стал готовым.

## Что передается помощнику

В текущей реализации:

- вопрос пользователя;
- найденные фрагменты локальной документации;
- только безопасные расчетные поля выбранного интервала.

Полная таблица и сырые строки файла не передаются.

## Обучение локального агента

Под "обучением" в проекте нужно разделять два этапа:

1. RAG/knowledge base: добавляем проверенные методики, инструкции, FAQ и примеры
   в локальную базу знаний. Это первый и самый безопасный этап.
2. Fine-tune/LoRA: обучаем модель только после накопления экспертно проверенного
   датасета и очистки чувствительных данных.

Сейчас реализуется первый этап. Он лучше подходит для инженерного ПО, потому что
формулы и методики должны быть проверяемыми и обновляемыми без переобучения модели.

## Ограничения

- Помощник не дает окончательное геологическое заключение.
- Помощник не придумывает новые формулы.
- Если локальная модель не настроена, `ollama` provider покажет понятную ошибку.
- Каждый ответ должен содержать предупреждение о необходимости проверки по ГИС,
  литологии, буровому контексту, фону, СПО, наращиваниям и рециркуляции.

## Проверка

```powershell
python -m pytest tests/test_ai_assistant.py tests/test_ai_model_profiles.py
python scripts/ai_models.py --profile balanced
python scripts/knowledge_base.py --query "Как считается Wh?"
python scripts/knowledge_base.py --query "Почему Wh стал NaN из-за C2?"
streamlit run app/streamlit_app.py
```
