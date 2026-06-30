# Проверка качества AI-помощника

Этот документ описывает локальную проверку качества RAG-контекста и safety-
контракта AI-помощника. Проверка не требует интернета и не требует Ollama:
она использует текущий `offline-docs` provider и локальную базу знаний.

## Файл кейсов

```text
config/ai_eval_cases.json
```

Каждый кейс содержит:

- `id` - стабильный идентификатор проверки;
- `question` - типовой вопрос пользователя;
- `expected_sources` - источники, которые должны попасть в контекст;
- `required_context_terms` - фразы, которые должны быть найдены в prompt-контексте;
- `required_answer_terms` - фразы, которые должны быть в ответе provider;
- `forbidden_terms` - слова или фразы, которых не должно быть в prompt или ответе.

## Запуск

```powershell
python scripts/evaluate_ai.py
python scripts/evaluate_ai.py --json
```

Команда возвращает код `0`, если все кейсы прошли, и `1`, если хотя бы один
кейс не прошел.

## Что проверяется

- Q/A-примеры действительно попадают в RAG-контекст по типовым вопросам.
- В prompt есть нужные источники и ключевые инженерные ограничения.
- Ответ offline provider содержит обязательное предупреждение.
- В контекст и ответ не попадают запрещенные термины.

## Когда запускать

Запускайте evaluation после изменений в:

- `config/knowledge_sources.json`;
- `config/knowledge_qa.json`;
- `config/ai_eval_cases.json`;
- `ai/knowledge_base.py`;
- `ai/prompts.py`;
- `ai/provider.py`.

Минимальная проверка:

```powershell
python -m pytest tests/test_ai_evaluation.py tests/test_ai_assistant.py
python scripts/evaluate_ai.py
python scripts/preflight.py
```

## Дальнейшее развитие

Когда локальная Ollama-модель будет установлена, эти же кейсы можно использовать
как базовый набор для сравнения качества ответов модели. Перед fine-tune или
LoRA нужно накопить больше экспертно проверенных кейсов и очистить данные от
любой чувствительной информации.
