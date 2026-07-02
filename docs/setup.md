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
```

Если нужно получить JSON для диагностики:

```powershell
python scripts/preflight.py --json
```

Preflight проверяет Python, зависимости, ключевые файлы проекта, конфиг палеток
и доступность папки `logs`.

## 7. Запустить приложение

Самый простой запуск на Windows:

```powershell
.\run_app.ps1
```

Если скрипты PowerShell запрещены или нужно запустить вручную:

```powershell
python -m streamlit run app/streamlit_app.py
```

Откройте адрес, который покажет Streamlit. Обычно это:

```text
http://localhost:8501
```

## 8. Проверить работу на примере

1. В интерфейсе нажмите загрузку файла.
2. Выберите `examples/sample_gas_data.las` или `examples/sample_gas_data.csv`.
3. Проверьте превью строк.
4. Оставьте найденную строку заголовков.
5. Проверьте mapping колонок.
6. Убедитесь, что появились расчеты, классификация и графики.

## 9. Локальные данные

Приложение само создает рабочие папки при сохранении данных:

- `data/wells/` — сохраненные скважины и версии подготовленных данных;
- `data/projects/default/correlation_settings.json` — настройки LAS-корреляции локального проекта;
- `logs/app.log` — диагностический лог приложения.

## 10. Повторный запуск

После первой установки каждый следующий запуск обычно выглядит так:

```powershell
cd C:\OSPanel\home\gas-ratio-pro
.\run_app.ps1

# или вручную:
.\.venv\Scripts\Activate.ps1
python -m streamlit run app/streamlit_app.py
```
