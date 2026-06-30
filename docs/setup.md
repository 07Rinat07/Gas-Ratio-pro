# Установка и запуск

Этот документ описывает развертывание проекта с нуля. Его можно использовать
как чеклист для нового разработчика или инженера, который впервые запускает
Gas Ratio Interpreter.

## 1. Требования

Минимально нужно:

- Python 3.11 или новее
- Git
- Доступ к папке проекта
- Интернет для первой установки Python-зависимостей

Опционально для локального AI-помощника:

- Ollama
- заранее скачанная локальная модель, если рабочая машина может остаться без интернета

Проверка версий:

```powershell
python --version
git --version
```

## 2. Получить проект

Если проект хранится в git-репозитории:

```powershell
git clone <repo-url> gas-ratio-pro
cd gas-ratio-pro
```

Если проект уже скопирован локально:

```powershell
cd C:\OSPanel\home\gas-ratio-pro
```

## 3. Создать виртуальное окружение

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Если PowerShell запрещает активацию окружения, временно разрешите выполнение
скриптов только для текущего пользователя:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 4. Установить зависимости

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Проверить проект тестами

```powershell
python -m pytest
```

Ожидаемый результат: все тесты проходят без ошибок.

## 6. Проверить готовность окружения

```powershell
python scripts/preflight.py
python scripts/knowledge_base.py
python scripts/evaluate_ai.py
```

Если нужно получить JSON для диагностики:

```powershell
python scripts/preflight.py --json
```

## 7. Опционально подготовить локальную AI-модель

Если на работе возможна потеря интернета, скачайте модель заранее:

```powershell
python scripts/ai_models.py
python scripts/ai_models.py --profile balanced
ollama pull qwen3:4b
ollama list
```

После загрузки укажите точное имя модели в `config/ai.json` и включите
provider `ollama`. Подробности описаны в `docs/local_model_profiles.md`.

Если модель не нужна или машина слабая, оставьте provider `offline-docs`.
Этот режим работает без интернета и без локальной модели.

## 8. Запустить приложение

```powershell
streamlit run app/streamlit_app.py
```

Откройте адрес, который покажет Streamlit. Обычно это:

```text
http://localhost:8501
```

## 9. Проверить работу на примере

1. В интерфейсе нажмите загрузку файла.
2. Выберите `examples/sample_gas_data.csv`.
3. Проверьте превью строк.
4. Оставьте найденную строку заголовков.
5. Проверьте mapping колонок.
6. Убедитесь, что появились расчеты, классификация и графики.

## 10. Повторный запуск

После первой установки каждый следующий запуск обычно выглядит так:

```powershell
cd C:\OSPanel\home\gas-ratio-pro
.\.venv\Scripts\Activate.ps1
streamlit run app/streamlit_app.py
```
