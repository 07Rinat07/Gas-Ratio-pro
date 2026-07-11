
## v210 — Export responsiveness and rerun optimization

- Professional report profile/format controls are batched in a Streamlit form.
- PDF/DOCX/HTML/bundle generation runs only after explicit confirmation, not on every widget rerun.
- The generated artifact is retained in session state and the download button always reflects its real format.
- Export start/completion/failure events now include format, duration and byte size in `logs/app.log`.
- Interpretation Plotly figures reuse the latest session cache while data and graph settings remain unchanged.
- Stage 4 remains open pending live acceptance of all export formats and responsiveness.

# GAS RATIO PRO — Current Project Status

Baseline: v210
Current stage: Stage 4 — Workbench UI Completion / module integration audit
Runtime acceptance: **FAILED for v202; navigation works, but core LAS/report/documentation workflows are not yet proven visible and usable**

## 1. Подтвержденное состояние

Modern Workbench shell, navigation, command dispatch and dock layout work. Live owner testing proved that `Command executed` is not sufficient acceptance: LAS upload/editor/viewer, graphs, reports, printing and Documentation were not observable as usable workflows in the central workspace. Browser DevTools also reported form/accessibility findings, but no JavaScript exception explaining the empty modules.

## 2. Активный инкремент v210

**Functional navigation and calculation/report workflow restoration**:

- `Data Workspace` восстановлен как отдельный маршрут Modern Workbench и открывает существующий экран `Работа с данными`;
- верхнее меню больше не является декоративным HTML: каждый пункт выполняет command-backed navigation;
- Project Explorer больше не является статическим списком: корень и коллекции открывают соответствующие реальные маршруты;
- `Interpretation` продолжает использовать рассчитанные данные из Data Workspace;
- `Reports` использует существующий report/export workflow и при отсутствии расчета показывает явную кнопку перехода в Data Workspace;
- Stage 5 — Petrophysical Engine остается заблокирован до живой приемки полного сценария.
- Предыдущий Functional visibility repair сохранен как завершенная техническая предпосылка v206; текущий фокус — функциональная навигация и сквозной расчет/report workflow.

## 3. Единственный следующий разрешенный шаг

Run v207 with diagnostics and repeat LAS/Interpretation/Reports/Exports/Documentation acceptance. Confirm that real controls appear immediately inside the central workspace without scrolling past an empty viewport-height panel.

Launch diagnostics mode:

```powershell
.\run_app.ps1 -ForceRestart -Diagnostics
```

## 4. Production acceptance gates

For every Workbench route:

1. command executes without traceback;
2. active route changes;
3. correct renderer and provider are resolved;
4. `module_loaded = YES`;
5. real controls are visible;
6. test input can be submitted;
7. expected visual/download result appears;
8. errors show a correlation ID and are readable in `logs/app.log`.

## 5. Управляющая документация

Active governance remains limited to `PROJECT_ROADMAP.md`, `PROJECT_STATUS.md`, `ARCHITECTURE.md` and `DOCUMENTATION_INDEX.md`. No new plan/status files are created.


## v208 — Functional menu and branding correction

- File and Project are no longer silent decorative menu labels; they open command-backed project/session controls.
- The shared application logo is displayed once in the Workbench title bar at a compact standard size.
- The duplicate Documentation hero logo overlay was removed.
- Stage 4 remains IN PROGRESS pending live acceptance of File/Project and remaining functional tabs.

## v209 — Correlation and printable report repair

Status: IN PROGRESS pending live acceptance.

Implemented: dedicated correlation route, active Project Explorer entry, compact engineering report composition, figures before tables, top-15 non-zero intervals, expert-only detailed reasoning, and PDF plot embedding with Kaleido fallback.

Properties/Dock correction is also implemented: Project Explorer selections now populate contextual Properties, the empty state is user-facing instead of technical `None`/`—`, and Developer Diagnostics is hidden while the right dock is collapsed so the narrow rail no longer contains clipped vertical text.
