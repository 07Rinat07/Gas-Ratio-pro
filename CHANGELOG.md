# История изменений

## Unreleased

Добавлено:

- Внешний JSON-конфиг `config/palettes.json` для Pixler/ternary палеток.
- Загрузчик и валидация конфигурации палеток.
- Отображение версии и предупреждения палеточного конфига в Streamlit sidebar.
- Черновые ternary-регионы из конфига.
- Локальное диагностическое логирование в `logs/app.log`.
- Тесты логирования и палеточного конфига.
- Документация `docs/palettes.md`, `docs/logging.md` и `docs/ai_agent_plan.md`.
- План локального бесплатного ИИ-помощника на базе локального runtime и RAG.
- Offline-first AI skeleton: локальная knowledge base, provider contract, Ollama provider и Streamlit-блок помощника.
- AI runtime readiness check для offline-docs/Ollama и отображение статуса в UI.
- Preflight-команда `python scripts/preflight.py` для проверки окружения перед запуском.
- Каталог профилей локальных AI-моделей, CLI `python scripts/ai_models.py` и preflight-валидация профилей.
- Manifest локальной RAG-базы знаний, CLI `python scripts/knowledge_base.py` и preflight-валидация источников.
- Q/A-каталог `config/knowledge_qa.json` для типовых вопросов локального AI-помощника.
- AI evaluation-кейсы `config/ai_eval_cases.json` и CLI `python scripts/evaluate_ai.py` для проверки RAG/safety качества.
- Режим `python scripts/evaluate_ai.py --provider-mode configured` для проверки provider из `config/ai.json`.
- CLI `python scripts/ai_config.py` для безопасного просмотра и переключения AI-provider.
- CLI `python scripts/setup_local_agent.py` и runbook `docs/local_ai_agent.md` для подготовки локального AI-агента.
- Подсказка в Streamlit UI с командами подготовки локального AI runtime.
- CLI `python scripts/export_ai_training_pack.py` для безопасного экспорта AI training/evaluation pack.
- Локальный override `config/ai.local.json` для включения Ollama без изменения дефолтного `config/ai.json`.
- Q/A-пример и evaluation-кейс про экран Ollama Launch, чтобы пользователь понимал, что выбирать там не нужно.
- Streamlit-блок `Чат поддержки` с историей сообщений, быстрыми вопросами и очисткой чата.
- Q/A-примеры и evaluation-кейсы для первого запуска приложения и диагностики чата поддержки.
- Windows launcher `run_app.ps1` и запуск Streamlit через `python -m streamlit`, чтобы не зависеть от PATH.
- Индикатор ожидания ответа Ollama в чате поддержки и логирование времени генерации.
- Более крупная типографика Streamlit UI, увеличенный таймаут Ollama и fallback-ответ по локальной документации при таймауте модели.
- Выбор размера интерфейса в sidebar, быстрый режим чата по базе знаний, расширенное распознавание Excel-заголовков и depth-графики по середине интервала.
- LAS importer для секций `~Curve`/`~ASCII`, пример `examples/sample_gas_data.las` и тесты полного pipeline mapping/calculation.
- План вкладки `LAS-редактор` для проверки глубины, изменения шага, добавления строк, ручного/автоматического заполнения пропусков, хранения скважин и выгрузки LAS/XLSX/CSV.
- Core-ядро LAS-редактора: диагностика глубин, построение сетки шага и стратегии заполнения `empty`, `top`, `bottom`, `average`, `linear`.

## v0.3

Дата: 2026-06-30

Добавлено:

- Streamlit-интерфейс для локального запуска.
- Импорт CSV, XLSX и XLSM.
- Чтение всех листов Excel.
- Автоматический поиск строки заголовков среди первых 50 строк.
- Ручной выбор строки заголовков.
- Mapping engine для стандартных полей газового каротажа.
- Расчет `Wh`, `Bh`, `BAR2`, Pixler ratios, ternary ratios.
- Настраиваемый режим `Ch` с предупреждением о необходимости подтверждения.
- Предварительная инженерная интерпретация интервалов.
- Pixler palette, ternary palette и depth tracks.
- CSV/XLSX helper-экспорт.
- Pytest-набор для расчетов, mapping, импорта и безопасного деления.
- Документация по установке, использованию, данным, формулам и troubleshooting.

Ограничения:

- Pixler-зоны требуют подтвержденных корпоративных границ.
- `Ch` требует подтверждения по корпоративной методике.
- LAS importer и расширенные отчеты еще не реализованы.
