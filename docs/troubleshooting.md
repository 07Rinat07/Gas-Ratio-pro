# Troubleshooting

## Preflight показывает FAILED

Запустите подробную проверку:

```powershell
python scripts/preflight.py --json
```

Типовые причины:

- не активировано виртуальное окружение;
- не установлены зависимости из `requirements.txt`;
- поврежден `config/ai.json`, `config/ai_eval_cases.json`, `config/ai_model_profiles.json`, `config/knowledge_qa.json`, `config/knowledge_sources.json` или `config/palettes.json`;
- папка `logs` недоступна для записи;
- выбран provider `ollama`, но локальная модель не указана или не найдена.

## Где смотреть подробности ошибки

Если интерфейс сообщает, что подробности записаны в лог, выполните:

```powershell
Get-Content logs/app.log -Tail 80
```

Лог показывает шаги workflow и stack trace внутренних ошибок. В лог не должны
попадать сырые таблицы и полное содержимое загруженных файлов.

## Streamlit не запускается

Проверьте, что активировано виртуальное окружение и установлены зависимости:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

Если команда `streamlit` не найдена, это нормально для Windows PATH. Используйте готовый launcher или запуск через Python-модуль:

```powershell
.\run_app.ps1

# или вручную:
python -m streamlit run app/streamlit_app.py
```

## Порт 8501 занят

Запустите на другом порту:

```powershell
python -m streamlit run app/streamlit_app.py --server.port 8502
```

## PowerShell не активирует `.venv`

Ошибка может быть связана с execution policy. Для текущего пользователя:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## Excel-файл не читается

Проверьте:

- файл имеет расширение `.xlsx` или `.xlsm`;
- файл не открыт в Excel в режиме блокировки;
- файл не поврежден;
- установлен `openpyxl` из `requirements.txt`.

Повторная установка зависимости:

```powershell
pip install openpyxl
```

## CSV отображается одной колонкой

CSV читается с автоопределением разделителя, но нестандартные файлы могут быть
распознаны неверно. Проверьте файл в текстовом редакторе:

- разделитель должен быть запятая, точка с запятой или табуляция;
- строка заголовков должна быть в первых 50 строках;
- кодировка желательно `utf-8-sig` или `cp1251`.

## Не найдена строка заголовков

Выберите строку заголовков вручную в интерфейсе. Нумерация начинается с `0`.

Если строка заголовков ниже 50-й строки, удалите лишнюю служебную шапку файла
или подготовьте файл так, чтобы заголовок был выше.

## Колонки не сопоставились

Исправьте mapping вручную в интерфейсе. Если такое название часто встречается,
добавьте алиас в `mapping/curve_aliases.py` и тест в `tests/test_mapping.py`.

## Все расчеты дают NaN

Проверьте:

- газовые компоненты распознаны правильно;
- числовые значения не содержат единиц измерения прямо в ячейках;
- десятичный разделитель соответствует формату, который понимает pandas;
- в знаменателях нет нулей.

Деление на 0 специально возвращает `NaN`, чтобы приложение не падало.

## Глубина отсутствует

Если `depth` не найден, приложение использует индекс строки как техническую
глубину и показывает предупреждение. Для инженерной интерпретации лучше
добавить настоящую колонку глубины.

## Тесты не проходят

Запустите:

```powershell
python -m pytest -vv
```

Сначала исправляйте расчетные тесты, затем import/mapping тесты. Если тест
падает после изменения формулы, проверьте `docs/formulas.md` и источник методики.

## Локальная база знаний AI-помощника не проходит проверку

Проверьте manifest и поиск:

```powershell
python scripts/knowledge_base.py --json
python scripts/knowledge_base.py --query "Как считается Wh?"
python scripts/knowledge_base.py --query "Почему Wh стал NaN из-за C2?"
python -m pytest tests/test_knowledge_manifest.py tests/test_knowledge_qa.py tests/test_ai_evaluation.py
python scripts/evaluate_ai.py
```

Типовые причины:

- путь в `config/knowledge_sources.json` указывает на отсутствующий файл;
- путь абсолютный или содержит `..`;
- повторяется один и тот же `path`;
- источник добавлен без topics или description;
- Q/A-пример ссылается на отсутствующий документ;
- повторяется один и тот же `id` Q/A-примера;
- `config/ai_eval_cases.json` ожидает источник, который больше не попадает в RAG-контекст.

## Профили локальных AI-моделей не проходят проверку

Проверьте каталог:

```powershell
python scripts/ai_models.py --json
python -m pytest tests/test_ai_model_profiles.py
```

Типовые причины:

- пустой или повторяющийся `id`;
- модель указана без tag;
- provider отличается от `ollama`;
- нет описания сценариев применения.

## Локальная модель Ollama не готова

Если в UI показано, что Ollama недоступен или модель не найдена:

```powershell
python scripts/ai_config.py status
python scripts/ai_models.py --profile balanced
ollama list
```

Проверьте:

- установлен ли Ollama на этой машине;
- запущен ли локальный сервис;
- совпадает ли имя модели в локальном AI config с именем из `ollama list`;
- была ли модель скачана заранее, пока интернет был доступен.

Если интернета нет, используйте provider `offline-docs`: он работает по локальной
документации и не требует модели.

## Чат поддержки не отвечает

Если сообщение появилось в истории, но ответа пока нет, подождите: локальная модель
Ollama может готовить первый ответ 20-120 секунд. В `logs/app.log` это видно как
`ai_question_received`, а затем `ai_answer_generated`.

Проверьте текущий AI provider и общий preflight:

```powershell
python scripts/ai_config.py status
python scripts/preflight.py
```

Если выбран `ollama`, убедитесь, что локальный сервис запущен и модель из
AI config видна в списке:

```powershell
ollama list
```

Если модель не готова или интернет недоступен, верните режим `offline-docs`:
он работает по локальной документации без внешних API и без скачанной модели.
Для диагностики откройте последние строки лога:

```powershell
Get-Content logs/app.log -Tail 80
```

Если помощник не знает ответ на новый типовой вопрос, добавьте проверенный Q/A
в `config/knowledge_qa.json`, затем проверьте качество:

```powershell
python scripts/evaluate_ai.py
```

## Открылось окно Ollama Launch

На экране Ollama Launch могут быть пункты Claude Code, Codex App, Hermes,
OpenClaw и другие инструменты. Для Gas Ratio Interpreter выбирать их не нужно.

Проект использует локальный HTTP-сервис Ollama и модель из AI config. Окно
Ollama можно свернуть или закрыть, если сервис остается запущенным в фоне.

Проверка:

```powershell
ollama list
python scripts/ai_config.py status
python scripts/preflight.py
```
