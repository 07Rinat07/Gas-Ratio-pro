# AI training pack

Этот документ описывает безопасную подготовку локального набора данных для
дальнейшей проверки моделей и будущего fine-tune/LoRA.

## Что экспортируется

Команда берет только проверяемые проектные источники:

- `config/knowledge_qa.json` -> supervised Q/A-примеры;
- `config/ai_eval_cases.json` -> evaluation-кейсы.

Сырые пользовательские таблицы, данные скважин, пароли, токены и приватные
файлы не должны попадать в этот пакет.

## Команда

```powershell
python scripts/export_ai_training_pack.py
```

По умолчанию файлы создаются в:

```text
artifacts/ai_training_pack/
```

Содержимое:

```text
manifest.json
qa_train.jsonl
eval_cases.jsonl
```

Папка `artifacts/` не коммитится. Это локальный generated output.

## Когда использовать

1. После добавления новых экспертно проверенных Q/A.
2. Перед сравнением локальных моделей Ollama.
3. Перед подготовкой отдельного fine-tune/LoRA датасета.

## Проверка

```powershell
python -m pytest tests/test_ai_training_dataset.py
python scripts/export_ai_training_pack.py
python scripts/evaluate_ai.py
python scripts/preflight.py
```

## Ограничения

Этот пакет еще не является готовым fine-tune датасетом для конкретного runtime.
Это безопасный промежуточный формат: он фиксирует знания, evaluation-кейсы,
источники и ограничения. Перед настоящим обучением нужно отдельно проверить
лицензии модели, качество ответов, приватность и формат целевого инструмента.
