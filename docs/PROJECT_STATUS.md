# GAS RATIO PRO — Current Project Status

Baseline: v198  
Current stage: Stage 4 — Workbench UI Completion / Technical Audit & Stabilization  
Runtime acceptance: **NOT YET CONFIRMED on owner environment**

## 1. Подтверждённая причина ревизии

Свежий пользовательский скриншот показывал минимальный линейный shell (`Modern Workbench`, navigation buttons, `Dock panels`) вместо пятизонного интерфейса из исходного кода v197. Строки этого shell отсутствуют в актуальном renderer. Это указывает на старый Streamlit-процесс или запуск из старой распакованной папки, а не на корректно загруженный build v197.

## 2. Что исправлено в v198

- добавлена неизменяемая runtime build identity (`v198`, channel, абсолютный project root, entry point);
- build и runtime source path отображаются в реальном Workbench;
- `run_app.ps1` проверяет владельца порта до запуска;
- занятый старым процессом проекта порт не используется молча;
- `-ForceRestart` разрешён только для процесса текущего project root;
- legacy UI environment flag очищается launcher-ом;
- активная документация сведена к четырём управляющим файлам;
- дублирующие progress/versioned roadmap документы перенесены в архив;
- Stage 4 повторно открыт до живого подтверждения интерфейса.

## 3. Единственный следующий разрешённый шаг

**Live Workbench acceptance из архива v198.**

1. распаковать v198 в отдельную новую папку;
2. запустить `./run_app.ps1 -ForceRestart`;
3. убедиться, что сверху виден `Build: v198`;
4. сверить `Runtime source` с новой папкой;
5. подтвердить Toolbar, Project Explorer, Workspace Host, Properties и Status Bar;
6. проверить navigation/collapse/restore и отсутствие traceback;
7. только после этого закрыть Stage 4 и активировать Petrophysical Engine.

Modeling Engine остаётся заблокированным до завершения Petrophysical Engine.
