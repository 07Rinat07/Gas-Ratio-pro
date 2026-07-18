# v225.8 — Stable Promotion & Live Workbench Acceptance

## Цель

Перевести Stage 4 из release candidate в stable на основании воспроизводимого runtime-доказательства, а не ручной отметки.

## Выполнено

1. Добавлен реальный временный Streamlit server health gate.
2. Добавлен AppTest acceptance пяти областей Workbench.
3. Проверены build/source identity и entry-point SHA-256.
4. Выполнена командная навигация LAS и открытие LAS Workspace без traceback.
5. Добавлен CLI и режим `run_app.ps1 -Acceptance`.
6. Канал сборки переведён в `stable` только после 14/14 checks.
