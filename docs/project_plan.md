# Gas Ratio Pro — Project Plan v2

## Назначение плана

Этот документ является основной дорожной картой развития Gas Ratio Pro после завершения базовых этапов проекта Gas Ratio Interpreter. План фиксирует последовательность работ: один законченный пункт плана реализуется отдельным этапом разработки и отдельным коммитом.

Приложение развивается как локальная инженерная система для работы с LAS, газовым каротажем, проектными скважинами, расчетами, интерпретационными планшетами, отчетами и проверяемой проектной базой.

## Правила выполнения этапов

- Рабочая ветка разработки: `main`.
- Один завершенный пункт плана = один отдельный коммит.
- Старые коммиты не переписываются.
- Новая функциональность сопровождается тестами, если меняется код.
- Документация обновляется вместе с изменением интерфейса, формата данных, workflow, импорта, экспорта или расчетов.
- Сырые таблицы и полное содержимое пользовательских файлов не пишутся в лог.
- Интерпретация остается предварительной инженерной подсказкой и требует проверки по ГИС, литологии, буровому контексту, фону, СПО, наращиваниям и рециркуляции.
- После завершенного этапа выполняются `python -m pytest` и `python scripts/preflight.py`.

## Completed Milestones

Ниже перечислены крупные блоки, уже перенесенные в новую дорожную карту и закрытые в рамках Project Plan v2.

- [x] Project Explorer: дерево проекта, группы скважин, пользовательские папки, metadata-only перемещение объектов и цветовые метки.
- [x] Well Manager: карточка скважины, координаты, KB, GL, TD, дата начала бурения, оператор и месторождение.
- [x] Dataset Manager: LAS, CSV, Excel, Core, Mud Log и Production datasets.
- [x] Project Database: индексация файлов, проверка дубликатов, версии файлов и автоматические UUID.

---

# Этап 1. Data Management

## 1.1 Project Explorer

- [x] Дерево проекта.
- [x] Группы скважин.
- [x] Папки.
- [x] Перетаскивание/перемещение объектов через metadata-only операции.
- [x] Цветовые метки.

## 1.2 Well Manager

- [x] Карточка скважины.
- [x] Координаты.
- [x] KB.
- [x] GL.
- [x] TD.
- [x] Дата бурения.
- [x] Оператор.
- [x] Месторождение.

## 1.3 Dataset Manager

- [x] LAS.
- [x] CSV.
- [x] Excel.
- [x] Core.
- [x] Mud Log.
- [x] Production.

## 1.4 Project Database

- [x] Индексация файлов.
- [x] Проверка дубликатов.
- [x] Версии файлов.
- [x] Автоматические UUID.

---

# Этап 2. LAS Professional

## 2.1 Curve Manager

- [x] Rename curves.
- [x] Alias curves.
- [ ] Merge curves.
- [ ] Split curves.
- [ ] Curve statistics.

## 2.2 Units Manager

- [ ] Автоматическая конвертация единиц.
- [ ] Пользовательские единицы.
- [ ] Проверка несовместимости.

## 2.3 Curve Quality

- [ ] Spike detector.
- [ ] Flat detector.
- [ ] Missing intervals.
- [ ] Duplicate depth.
- [ ] Sampling diagnostics.

## 2.4 Curve Processing

- [ ] Moving Average.
- [ ] Median.
- [ ] Savitzky-Golay.
- [ ] Gaussian.
- [ ] Low-pass.

---

# Этап 3. Mud Gas Professional

## 3.1 Gas Normalization

- [ ] C1 normalization.
- [ ] Background correction.
- [ ] Lag correction.
- [ ] Flow correction.

## 3.2 Gas Quality

- [ ] Air contamination.
- [ ] Sample quality.
- [ ] Gas stability.
- [ ] Mud circulation check.

## 3.3 Gas Diagnostics

- [ ] Automatic anomaly detection.
- [ ] Gas peaks.
- [ ] Gas drops.
- [ ] Missing gas.

---

# Этап 4. Petrophysics

## 4.1 Lithology

- [ ] Lithology calculator.
- [ ] Clay estimation.
- [ ] Sand/Shale split.

## 4.2 Porosity

- [ ] Density.
- [ ] Neutron.
- [ ] Sonic.
- [ ] Combined.

## 4.3 Water Saturation

- [ ] Archie.
- [ ] Simandoux.
- [ ] Indonesia.
- [ ] Dual Water.

## 4.4 Permeability

- [ ] Timur.
- [ ] Coates.
- [ ] SDR.

---

# Этап 5. Interpretation

## 5.1 Interval Manager

- [ ] Reservoirs.
- [ ] Layers.
- [ ] Tops.
- [ ] Bottoms.

## 5.2 Zone Correlation

- [ ] Compare wells.
- [ ] Shared tops.
- [ ] Marker matching.

## 5.3 Pay Calculator

- [ ] Net Pay.
- [ ] Gross.
- [ ] NTG.
- [ ] HC Columns.

---

# Этап 6. Tablet Professional

## 6.1 Track Designer

- [ ] Drag & Drop tracks.
- [ ] Templates.
- [ ] Track locking.
- [ ] Track synchronization.

## 6.2 Annotation

- [ ] Notes.
- [ ] Symbols.
- [ ] Images.
- [ ] Comments.

## 6.3 Printing

- [ ] Multi-page.
- [ ] A0.
- [ ] A1.
- [ ] A3.
- [ ] Scale presets.

---

# Этап 7. Reports

## 7.1 Report Builder

- [ ] Word.
- [ ] PDF.
- [ ] HTML.

## 7.2 Templates

- [ ] Company templates.
- [ ] User templates.
- [ ] Logo.
- [ ] Header.
- [ ] Footer.

## 7.3 Automatic Reports

- [ ] Interval reports.
- [ ] Gas reports.
- [ ] Project summary.

---

# Этап 8. Visualization

## 8.1 Crossplots

- [ ] Pickett.
- [ ] M-N.
- [ ] RHOB-NPHI.
- [ ] Custom.

## 8.2 Histograms

- [ ] Single curve.
- [ ] Multi curve.
- [ ] Statistics.

## 8.3 Scatter

- [ ] Multi-axis.
- [ ] Color mapping.
- [ ] Bubble plots.

---

# Этап 9. Multi Well

## 9.1 Well Comparison

- [ ] Side-by-side.
- [ ] Overlay.
- [ ] Shared depth.

## 9.2 Batch Calculations

- [ ] Selected wells.
- [ ] Entire project.
- [ ] Background processing.

## 9.3 Batch Export

- [ ] PDF.
- [ ] PNG.
- [ ] CSV.
- [ ] LAS.

---

# Этап 10. Professional Features

## 10.1 Autosave

- [ ] Automatic recovery.
- [ ] Backup.
- [ ] Version history.

## 10.2 Plugin API

- [ ] Plugin loader.
- [ ] Python plugins.
- [ ] User scripts.

## 10.3 Settings

- [ ] Workspace presets.
- [ ] Themes.
- [ ] Keyboard shortcuts.

## 10.4 Performance

- [ ] Cache.
- [ ] Lazy loading.
- [ ] Large LAS optimization.

---

# Этап 11. Enterprise

## 11.1 Audit

- [ ] Operation history.
- [ ] Change history.
- [ ] User actions.

## 11.2 Security

- [ ] Project lock.
- [ ] Read only.
- [ ] Integrity check.

## 11.3 Project Exchange

- [ ] Import package.
- [ ] Export package.
- [ ] Validation.

---

### Реализовано: LAS Professional → Curve Manager → Rename curves

LAS-редактор получил отдельный Curve Manager для безопасного переименования кривых. Логика вынесена в `las_editor/curve_rename.py` и выполняет нормализацию имени, проверку существования исходной кривой, запрет пустого имени, проверку конфликтов с существующими колонками, запись истории `old_name/new_name/timestamp/reason/source` и одноуровневый undo последнего rename.

После переименования обновляются реально существующие ссылочные структуры редакторского workflow: tablet tracks из session state, доступные preset-списки, export columns и manifest-представление текущих колонок. Общая функция обновления ссылок работает рекурсивно с dict/list/tuple/set, поэтому ее можно повторно использовать для templates, presets, saved calculations, exports и manifest при расширении проектного хранения.

## Следующий пункт разработки

### Реализовано: LAS Professional → Curve Manager → Alias curves

LAS-редактор получил менеджер стандартных alias для LAS-кривых. Логика вынесена в `las_editor/curve_alias.py` и назначает канонические роли кривым без переименования исходных колонок: `depth`, `depth_from`, `depth_to`, `c1`, `c2`, `c3`, `ic4`, `nc4`, `ic5`, `nc5`, `co2`, `h2s`, `rop`, `lithology` и другие ключи из существующего словаря `mapping/curve_aliases.py`.

Alias Manager проверяет существование выбранной кривой, запрещает пустой или неподдерживаемый alias, нормализует имя alias, показывает предупреждение при конфликте классификации и сохраняет историю `curve_name/alias/previous_alias/timestamp/reason/source`. Для последнего назначения доступен одноуровневый undo: если alias был новым, он удаляется; если он заменял старое назначение, восстанавливается предыдущий alias.

UI-блок `Curve Manager · Alias curves` добавлен во вкладку `LAS-редактор`. Пользователь может автоматически определить alias по существующему словарю авто-маппинга, вручную назначить alias выбранной кривой, посмотреть текущие назначения и историю, а также отменить последнее назначение. Alias записываются в session state и переданные reference-структуры (`curve_aliases`, `manifest`) без изменения данных DataFrame.

## Следующий пункт разработки

Текущий следующий незавершенный пункт: **LAS Professional → Curve Manager → Merge curves**.
