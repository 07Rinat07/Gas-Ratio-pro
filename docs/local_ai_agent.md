# Локальный AI-агент

Этот runbook описывает, как подготовить бесплатного локального AI-агента для
проекта. Цель - чтобы приложение продолжало помогать пользователю даже без
интернета.

## Что считается обучением в текущей версии

В проекте используется безопасный первый этап обучения: локальная RAG-база
знаний. Мы добавляем проверенные документы, Q/A-примеры и evaluation-кейсы, а
локальная модель получает этот контекст в prompt.

Такой подход выбран специально:

- методики и формулы остаются проверяемыми в git;
- знания можно обновлять без переобучения модели;
- сырые рабочие таблицы не попадают в обучающий датасет;
- качество можно проверять командой `python scripts/evaluate_ai.py`.

Fine-tune или LoRA можно добавлять позже, только после накопления очищенного и
экспертно подтвержденного датасета.

## Быстрый план подготовки

Посмотреть план без скачивания:

```powershell
python scripts/setup_local_agent.py --profile balanced
```

Когда Ollama установлен и интернет доступен, скачать модель:

```powershell
python scripts/setup_local_agent.py --profile balanced --download
```

После скачивания включить модель в проекте:

```powershell
python scripts/setup_local_agent.py --profile balanced --write-config
python scripts/preflight.py
python scripts/evaluate_ai.py --provider-mode configured
```

Если нужно сделать все подряд на подготовленной машине:

```powershell
python scripts/setup_local_agent.py --profile balanced --download --write-config --evaluate
```

## Что делает команда

`scripts/setup_local_agent.py`:

1. выбирает профиль из `config/ai_model_profiles.json`;
2. проверяет локальную RAG-базу знаний через evaluation;
3. при флаге `--download` запускает `ollama pull <model>`;
4. при флаге `--write-config` переключает `config/ai.json` на Ollama;
5. при флаге `--evaluate` проверяет ответы уже настроенного provider.

Команда без флагов ничего не скачивает и не меняет в конфиге.

По умолчанию `--write-config` пишет в `config/ai.local.json`. Это локальный override для рабочей машины; он не коммитится и не ломает дефолтный `config/ai.json` для пользователей без Ollama.

## Если Ollama не установлен

Команда покажет понятную ошибку и не будет менять проект. Нужно:

1. установить Ollama с `https://ollama.com/download`;
2. перезапустить PowerShell или терминал;
3. проверить `ollama --version`;
4. повторить `python scripts/setup_local_agent.py --profile balanced --download`.

## Возврат в безопасный offline-режим

Если локальная модель работает медленно или недоступна:

```powershell
python scripts/ai_config.py offline-docs --write
python scripts/preflight.py
```

Provider `offline-docs` не требует интернета и модели.

## Что улучшать дальше

- расширять `config/knowledge_qa.json` экспертно проверенными вопросами;
- добавлять новые evaluation-кейсы в `config/ai_eval_cases.json`;
- экспортировать безопасный training/evaluation pack командой `python scripts/export_ai_training_pack.py`;
- сравнивать качество профилей `minimal_cpu`, `balanced`, `strong_local`;
- готовить отдельный очищенный датасет перед любым fine-tune.
