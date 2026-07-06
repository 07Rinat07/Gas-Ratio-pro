# Gas Ratio Pro — Project Plan v4

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
- [x] Dashboard background shell: главная страница получила фирменный Gas Ratio Pro фон, темный overlay, навигационный navbar, интерактивные карточки, быстрый доступ, динамические новости, статистику, активность и блок авторских прав.
- [x] Dashboard application shell: стартовая страница растягивается на всю ширину рабочей области, использует современный navbar с поисковыми/action-чипами, glass-сетку карточек и status footer; рабочие модули закрываются темными рабочими панелями для читаемости.
- [x] Responsive dashboard navigation refresh: декоративный левый rail-sidebar убран, быстрый доступ переделан в крупные функциональные action-карточки, верхние вкладки оформлены как кнопки с hover-анимацией, фирменный фон доступен как общий бренд-слой приложения.
- [x] Branded responsive background system: текущий морской фон заменен на фирменный вертикальный Gas Ratio Pro background, добавлен логотип приложения, прозрачность Dashboard/Instructions снижена, а layout-профили разделены на телефон, ноутбук и большой экран.
- [x] Proportional branded background scaling: фирменная вертикальная картинка больше не растягивается `cover` на всю страницу, а масштабируется пропорционально по профилям телефон/ноутбук/большой экран с более прозрачными overlay/glass-слоями.
- [x] Dashboard brand visibility tuning: overlay и glass-слои Dashboard дополнительно ослаблены, чтобы фирменная картинка читалась через панели без потери читаемости текста.

---

# Приоритетный UI Modernization Track

Этот трек добавлен после решения изменить дизайн главной страницы и использовать фирменный фон с буровой. Он выполняется отдельными небольшими этапами, чтобы не ломать рабочие модули LAS, графики и таблицы.

## UI.1 Application Shell

- [x] Dashboard background shell.
- [x] Modern navigation bar.
- [x] Compact left rail-sidebar prototype.
- [x] Remove unproductive dashboard rail-sidebar.
- [x] Responsive central workspace.
- [x] Mobile/tablet dashboard breakpoints.
- [x] Phone / laptop / large-screen layout profiles.
- [x] Dynamic status bar.
- [x] Responsive branded navigation and documentation background.
- [x] Sidebar 2.0 / project control center.
- [x] Global command palette.
- [x] Unified page layout.
- [ ] Keyboard shortcuts.

## UI.2 Dashboard

- [x] Background image integration.
- [x] Replace temporary sea-rig background with branded Gas Ratio Pro background.
- [x] Dark overlay engine.
- [x] Responsive widget layout.
- [x] Adaptive dashboard transparency so the branded background is clearly visible.
- [x] Dashboard brand visibility tuning for lighter glass layers.
- [x] Proportional background scaling without ugly crop/oversize.
- [x] Glass panels.
- [x] Welcome panel.
- [ ] Project preview from real LAS data.
- [ ] Dashboard widget settings.


## 3.14 Dashboard UX Refactoring

### Simplify dashboard navigation

Dashboard использует одну навигационную модель: каждая карточка раздела является единственным кликабельным элементом, без второй кнопки `Открыть`. Это уменьшает визуальный шум и улучшает отображение на ноутбуках 1366×768 и 1440×900.


- [x] Remove duplicated navigation buttons.
- [x] Make dashboard navigation cards clickable.
- [x] Remove duplicate `Open` buttons from dashboard cards.
- [x] Optimize dashboard grid for 1366×768 and 1440×900 notebooks.
- [x] Redesign quick actions as compact clickable shortcuts.
- [x] Improve dashboard information hierarchy.
- [x] Create Dashboard 3.0 branch as a full dashboard replacement after UX regression.
- [x] Restore useful dashboard blocks instead of deleting them.
- [x] Add product-style left navigation rail, overview metrics, recent project/LAS/calculation/activity panels, project health and license status.
- [x] Center and contain the branded background inside the Dashboard 3.0 layout.
- [x] Run responsive layout audit after each UI stage.
- [x] Refine dashboard background centering and scaling.


### Реализовано: Dashboard UX Refactoring → Dashboard 3.0

Создана отдельная ветка интерфейса Dashboard 3.0: вместо агрессивного удаления блоков главный экран восстановлен как полноценная рабочая панель. Dashboard теперь содержит левую навигационную рейку, верхний обзор, статистику проекта, последние проекты, последние LAS-файлы, последние расчеты, последнюю активность, статус проекта и лицензионный блок. Дублирующие кнопки `Открыть...` не возвращались. Сетка построена через адаптивный CSS Grid с отдельными правилами для 1440px, 1200px и мобильных экранов.

Текущий следующий незавершенный пункт: **следующий модуль после Dashboard UX Refactoring**.



### Реализовано: Dashboard UX Refactoring → Background Refinement

Dashboard 3.0 получил отдельный проход по фоновому изображению: брендовый арт теперь центрирован, уменьшен и переведен в режим `contain`, чтобы не вылезать из сетки и не конкурировать с карточками. Для 1366×768, 1440×900, 1600×900, Full HD и мобильных экранов заданы отдельные размеры и позиции фона. Левый brand-card также использует `contain`, а не `cover`, чтобы логотип и буровая не обрезались внутри карточки.

Текущий следующий незавершенный пункт: **следующий модуль после Dashboard UX Refactoring**.

### Реализовано: Dashboard UX Refactoring → Quick Actions Redesign

Стартовая панель быстрых действий переработана в компактные кликабельные плитки: каждая плитка теперь является единственным рабочим действием и переключает нужный раздел через общий механизм `ACTIVE_MAIN_TAB_KEY`. Дублирующие большие карточки и текст `Нажмите одноименную кнопку ниже` удалены из Dashboard, чтобы быстрый доступ не повторял собственные функции два раза на одной странице.

В реестр `START_ACTIONS` добавлены `icon` и `short_title`, поэтому кнопки стали короче и лучше помещаются на ноутбуках 1366×768 и 1440×900. Внутренний блок Dashboard показывает только краткую сводку и последнее действие без повторных кнопок. README не изменялся и не засорялся журналом этапа.

Текущий следующий незавершенный пункт: **Dashboard UX Refactoring → Dashboard Information Hierarchy**.


### Реализовано: Dashboard UX Refactoring → Responsive Layout Audit

Dashboard 3.0 получил отдельный responsive audit pass для ноутбуков и рабочих мониторов: добавлены явные правила для 1366×768, 1440×900, 1600×900 и 1920×1080, ограничение `overflow-x: clip`, безопасные `minmax(0, 1fr)` сетки, компактные метрики и перенос длинного текста внутри списков. Цель этапа — не удалять полезные блоки, а сохранить полный Dashboard 3.0 без горизонтального переполнения и пустых разрывов.

Текущий следующий незавершенный пункт: **Dashboard UX Refactoring → Background refinement**.

## UI.3 Dashboard Widgets

- [x] Recent projects.
- [x] Quick actions.
- [x] Project statistics.
- [x] Recent activity.
- [x] Useful tips.
- [x] What's new.
- [ ] Recent reports.
- [ ] License status widget.

## UI.4 Dynamic Data

- [x] Live project statistics.
- [x] Live recent projects.
- [x] Live recent activity.
- [ ] Live reports.
- [ ] Live calculations preview.
- [ ] Live import history.

## UI.5 Theme Engine

- [ ] Theme manager.
- [ ] Dark theme tokens.
- [x] Dashboard background support.
- [x] Global branded background layer for all tabs.
- [x] Branded instructions background.
- [x] Adaptive proportional brand image size for phone, laptop and large screens.
- [x] Adaptive transparency for dashboard panels.
- [x] Dark readable work panels above branded background for plots, LAS editor, crossplots, tables and reports.

## UI.6 Branding and Commercial Readiness

- [x] Dashboard author/copyright block.
- [x] Logo asset integrated into project assets.
- [x] Dashboard logo watermark.
- [x] About dialog redesign.
- [x] Application identity metadata.
- [ ] EULA document.
- [ ] License manager.
- [ ] Offline activation.
- [ ] License validation.
- [ ] Trial mode.
- [ ] Build signing notes.

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
- [x] Merge curves.
- [x] Curve grouping.
- [x] Curve categories.
- [x] Curve units manager.
- [x] Curve metadata editor.
- [x] Curve duplicate detection.
- [x] Curve quality flags.
- [x] Curve mnemonics dictionary.
- [x] Curve bulk edit.
- [ ] Curve import rules.
- [x] Curve export rules.
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

### Реализовано: LAS Professional → Curve Manager → Merge curves

LAS-редактор получил менеджер объединения кривых. Логика вынесена в `las_editor/curve_merge.py` и позволяет выбрать минимум две существующие LAS-кривые, задать результирующее имя, нормализовать его и создать новую derived-кривую по одной из стратегий: `coalesce_first`, `coalesce_last`, `mean` или `sum`.

Merge Manager проверяет существование всех исходных кривых, запрещает пустое имя результата, не допускает конфликт с существующими колонками и проверяет числовой тип исходных кривых для стратегий `mean` и `sum`. История хранит `source_names`, `target_name`, `strategy`, `timestamp`, `reason`, `source` и флаг `keep_sources`. Для последнего merge доступен одноуровневый undo: приложение удаляет созданную результирующую кривую и очищает metadata-ссылки на нее.

UI-блок `Curve Manager · Merge curves` добавлен во вкладку `LAS-редактор` после rename и alias. Пользователь выбирает исходные кривые, стратегию объединения, имя результирующей кривой и режим сохранения исходников. Переданные reference-структуры `manifest` и `exports.columns` обновляются для новой кривой; при удалении исходников ссылки tablet tracks/templates/presets/saved calculations перенаправляются на результирующую кривую.


### Реализовано: LAS Professional → Curve Manager → Curve grouping

LAS-редактор получил менеджер группировки кривых. Логика вынесена в `las_editor/curve_grouping.py` и использует существующие правила классификации LAS-корреляции для автоматического распределения кривых по инженерным группам: глубина, gamma ray, total gas, C1-C5, газовые коэффициенты, resistivity, density/neutron, буровые параметры, литология и прочие.

Curve Grouping Manager проверяет существование выбранной кривой, запрещает пустую или неподдерживаемую группу, хранит ручные overrides отдельно от исходного DataFrame и записывает историю `curve_name/group/previous_group/timestamp/reason/source`. Для последнего назначения доступен одноуровневый undo: если ручное правило заменяло автоматическую группу, override удаляется, а кривая возвращается к автоматической классификации.

UI-блок `Curve Manager · Curve grouping` добавлен во вкладку `LAS-редактор` после alias и до merge. Пользователь видит таблицу авто-группы, текущей группы, alias и признака ручного правила, может назначить группу вручную и отменить последнее действие. Reference-структуры `curve_group_overrides`, `curve_groups` и `manifest` обновляются без изменения данных DataFrame.

## Следующий пункт разработки

### Реализовано: LAS Professional → Curve Manager → Curve categories

LAS-редактор получил менеджер категорий кривых поверх существующих инженерных групп. Логика вынесена в `las_editor/curve_categories.py`: категории `depth_reference`, `petrophysics`, `mud_gas`, `drilling`, `interpretation` и `uncategorized` строятся автоматически на основе активных групп, включая ручные group overrides.

Curve Categories Manager проверяет выбранную кривую, запрещает пустую или неподдерживаемую категорию, хранит ручные `curve_category_overrides` отдельно от DataFrame и ведет историю `curve_name/category/previous_category/timestamp/reason/source`. Одноуровневый undo возвращает кривую к предыдущей ручной категории или к автоматической категории, рассчитанной по текущей группе.

UI-блок `Curve Manager · Curve categories` добавлен во вкладку `LAS-редактор` после grouping и до merge. Пользователь видит сводку категорий, таблицу кривых с alias, группой, авто-категорией, текущей категорией и признаком ручного правила. Reference-структуры `curve_categories`, `curve_category_overrides` и `manifest` обновляются без изменения исходных данных.

## Следующий пункт разработки

### Реализовано: LAS Professional → Curve Manager → Curve units manager

Добавлен `las_editor/curve_units.py`: поддерживаются нормализация единиц, авто-подбор unit по группе/категории, ручные unit overrides, история изменений, undo последнего назначения, summary rows и безопасные коэффициенты пересчета для метр/фут, fraction/percent/ppm.

UI-блок `Curve Manager · Curve units manager` добавлен во вкладку `LAS-редактор` после categories и до merge. Пользователь видит сводку единиц, таблицу кривых с alias, категорией, авто-единицей, текущей единицей, ручным правилом и доступными безопасными пересчетами. Reference-структуры `curve_units`, `curve_unit_overrides` и `manifest` обновляются без изменения исходных LAS-значений.

Текущий следующий незавершенный пункт: **LAS Professional → Curve Manager → Curve metadata editor**.


### Реализовано: UI Modernization Track → Dashboard background shell

Главная страница получила новый Dashboard shell на основе фонового изображения `assets/dashboard/gas_ratio_brand_background.png`. Изображение используется только на стартовой странице и накрывается темным gradient overlay, чтобы текст, карточки и кнопки оставались читаемыми. Рабочие области с графиками, LAS-кривыми, таблицами и числами не переводятся на фоновую картинку, чтобы не ухудшать видимость инженерных данных.

Dashboard теперь содержит HTML/CSS shell с верхним navbar, glass-панелями, блоком приветствия, недавними проектами, быстрым доступом, динамическими новостями, статистикой проекта, активностью, ежедневным советом и блоком авторских прав. Значения в карточках строятся из реального состояния проекта: списка проектов, LAS-файлов, расчетов, экспортов, скважин и активности, если соответствующие данные уже есть в локальном хранилище.

## Следующий пункт разработки

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Keyboard shortcuts**.


### Реализовано: UI Modernization Track → Dashboard application shell

Главная страница переработана из узкого прототипа в полноширинный application shell. Streamlit `block-container` в широком режиме больше не ограничивает Dashboard фиксированной шириной, поэтому стартовая область занимает доступное пространство экрана и не оставляет большие пустые поля по бокам.

Dashboard получил современный navbar с брендом, навигационными кнопками, поисковым чипом `Ctrl+K` и чипом активного проекта. Фоновое изображение `assets/dashboard/gas_ratio_brand_background.png` растягивается на всю Dashboard-область, позиционируется по центру/правому краю и перекрывается менее агрессивным затемняющим overlay: карточки остаются читаемыми, но логотип и буровая визуально видны как часть дизайна, а не как скрытая картинка под блоками.

Основные виджеты переведены в адаптивную glass-сетку: приветствие, недавние проекты, быстрый доступ, статистика проекта, активность, новости, полезные советы, mini log preview и лицензия. Статистика, проекты, новости, активность и советы строятся из реального состояния локального проекта и session state. Рабочие модули LAS Editor, графики, таблицы, correlation и reports закрываются темными рабочими панелями для читаемости кривых, чисел и инженерных таблиц.

### Реализовано: UI Modernization Track → Responsive dashboard navigation refresh

После визуальной проверки чернового shell удален неэффективный левый rail-sidebar внутри Dashboard: он занимал место, не давал полезной навигации и ухудшал внешний вид. Быстрый доступ переведен в крупные информативные action-карточки со ссылками-якорями на рабочие разделы: проект/импорт, LAS-редактор, LAS-корреляция, графики/отчеты и инструкции.

Фирменный фирменный Gas Ratio Pro фон теперь доступен как общий бренд-слой приложения. Для рабочих вкладок он приглушается темным overlay, а реальные графики, LAS-кривые, таблицы и редакторы остаются на темных панелях, чтобы фон не мешал данным. Верхние Streamlit-вкладки стилизованы как крупные кнопки с активным состоянием и hover-анимацией, чтобы переключение разделов визуально воспринималось как меню приложения. Добавлены CSS-breakpoints для широкого экрана, обычного монитора и мобильной ширины: dashboard-сетка перестраивается из трех колонок в две и одну колонку.

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Keyboard shortcuts**.


### Реализовано: UI Modernization Track → Responsive branded navigation and documentation background

По результатам визуальной проверки стартового экрана обновлена оболочка приложения: стандартные маленькие вкладки Streamlit заменены на крупные информативные кнопки навигации. Кнопки теперь реально переключают рабочие разделы через состояние приложения, а не являются декоративными ссылками-якорями.

Фоновое изображение `assets/dashboard/gas_ratio_brand_background.png` сделано заметнее: общий overlay и glass-карточки стали прозрачнее, чтобы логотип и буровая читались как фирменный визуальный слой. Вкладка инструкций получила полноэкранный branded background с отдельными читаемыми панелями. Рабочие инженерные области сохраняют темные панели поверх фона, чтобы LAS-кривые, таблицы, графики и числовые данные не теряли читаемость.

Левый sidebar переработан: вместо длинного малополезного списка добавлена современная карточка активного проекта со статистикой по скважинам, LAS-файлам, расчетам и экспортам; подробное дерево проекта свернуто в expander и не занимает постоянное место.

Добавлен файл `LICENSE` с proprietary-лицензией: права принадлежат Rinat Sarmuldin, коммерческое использование и модификация требуют предварительного письменного разрешения.


### Реализовано: UI Modernization Track → Dashboard visibility and project search refresh

Фоновое изображение Dashboard сделано заметнее: основной overlay и glass-карточки стали прозрачнее, чтобы логотип и буровая читались как полноценный фирменный фон, но текст оставался контрастным. Вкладка «Инструкции и документация» использует тот же полноэкранный бренд-фон с отдельными читаемыми panel-блоками. Быстрый доступ на стартовой странице вынесен в реальные Streamlit-кнопки, которые переключают рабочие разделы приложения. Добавлен рабочий поиск по проекту на стартовой странице и в боковом проектном виджете: поиск фильтрует элементы структуры проекта по имени, статусу и типу объекта. Боковой виджет стал компактнее: настройки интерфейса свернуты, основная карточка показывает активный проект и ключевые счетчики.


### Реализовано: UI Modernization Track → Branded responsive background system

Фирменная система фона обновлена: временное изображение фирменной Gas Ratio Pro картинкой удалено из активного Dashboard-фона, вместо него используется вертикальная бренд-картинка Gas Ratio Pro из `assets/dashboard/gas_ratio_brand_background.png`. Логотип приложения сохранен в `assets/branding/gas_ratio_pro_logo.png` и используется как полупрозрачный watermark на Dashboard.

Overlay и glass-слои на стартовой странице и во вкладке «Инструкции и документация» стали заметно прозрачнее, чтобы фирменная картинка была видна как часть дизайна, а не скрывалась за темными блоками. Для рабочих модулей с LAS-кривыми, графиками, таблицами и отчетами сохраняется темная рабочая поверхность поверх бренд-фона, чтобы инженерные данные оставались читаемыми.

В план интерфейса добавлены отдельные layout-профили `Телефон`, `Ноутбук` и `Большой экран`. Dashboard, navigation cards и documentation page имеют media-breakpoints для узких экранов, ноутбуков и широких мониторов.

### Реализовано: UI Modernization Track → Proportional branded background scaling

Фирменный фон переведен из режима полноэкранного `cover` в пропорциональное позиционирование. На больших экранах картинка занимает контролируемую часть правой нижней области, на ноутбуках уменьшается до компактного размера, а на узких экранах центрируется сверху и не разрывает верстку. Это убирает некрасивое гигантское масштабирование и предотвращает грубое обрезание логотипа/буровой.

Overlay и glass-слои дополнительно ослаблены: глобальный фон, Dashboard shell, Dashboard-карточки и вкладка «Инструкции и документация» используют более прозрачные значения, чтобы бренд-картинка была реально видна, но текст оставался читаемым. Рабочие инженерные области по-прежнему должны закрывать графики, LAS-кривые, таблицы и отчеты темными поверхностями.

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Keyboard shortcuts**.


### Реализовано: UI Modernization Track → Documentation hero banner

Вкладка `Инструкции и документация` получила отдельный hero-banner вместо пустого темного прямоугольника. В баннер встроен новый фирменный wide-арт `assets/dashboard/documentation_hero.png` с буровой, логотипом Gas Ratio Pro и авторством Rinat Sarmuldin. Изображение используется как верхний визуальный блок документации, а не как случайный затемненный фон, поэтому пользователь сразу видит фирменную картинку.

Документационный hero использует адаптивную высоту, `background-size: cover`, центрированное позиционирование и мягкий overlay. Заголовок и вводный текст размещены на отдельной glass-панели, чтобы картинка оставалась видимой, а текст читался на ноутбуках, больших мониторах и узких экранах.

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Keyboard shortcuts**.

### UI Modernization Track — Documentation hero image placement

- [x] Documentation hero image placement

Вкладка `Инструкции и документация` больше не использует пустой темный прямоугольник. Верхний блок документации рендерит изображение `assets/dashboard/documentation_hero.png` напрямую через HTML `<img>`, поэтому фирменная картинка с буровой, названием `GAS RATIO PRO` и авторством отображается внутри верхнего баннера. Поверх изображения оставлен легкий градиент для читаемости, справа добавлен небольшой фирменный логотип-бейдж. Лишняя техническая подпись про использование фонового изображения удалена из карточки `Лицензия и авторские права` на Dashboard.

### Реализовано: UI Modernization Track → Dashboard brand visibility tuning

Стартовый Dashboard получил более прозрачные glass-панели и более легкий общий overlay: фон теперь виден как часть интерфейса, а не как скрытая картинка под темными блоками. Для этого ослаблены затемняющие градиенты, снижена непрозрачность карточек, quick-action tiles, метрик и навигационной панели, а blur оставлен минимальным, чтобы брендовый арт сохранял детали.

Рабочие инженерные экраны пока сохраняют темные читаемые панели. Следующий практический этап по визуальному плану: **Global command palette / Ctrl+K search**.


### Реализовано: UI Modernization Track → Sidebar 2.0 project control center

Левый sidebar переработан из вспомогательного Streamlit-блока в проектный control center. Вверху добавлен фирменный блок Gas Ratio Pro с логотипом, активным проектом и краткой идентификацией продукта. Ниже отображаются проектная сводка, состояние проекта, режим лицензии, быстрые переходы в рабочие разделы и последние материалы активного проекта.

Структура проекта, поиск, перемещение объектов и цветовые метки сохранены, но теперь убраны в свернутый expander, чтобы не занимать постоянное место и не перегружать интерфейс. Sidebar стал информативным: пользователь сразу видит количество скважин, LAS-файлов, расчетов, экспортов, состояние данных и недавние действия.

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Keyboard shortcuts**.

### Реализовано: UI Modernization Track → Global command palette / Ctrl+K search

В верхней части приложения добавлена глобальная командная палитра в стиле `Ctrl+K`. Она ищет не только по основным разделам приложения, но и по рабочим действиям, документации и объектам активного проекта. Команды ведут в конкретные разделы: импорт данных, LAS-редактор, LAS-корреляцию, интерпретационные графики и инструкции.

Палитра использует реальные данные проекта: дерево активного проекта, документы из `DOCUMENTATION_TAB_DOCS`, статические рабочие команды и навигационные разделы. Найденные команды отображаются карточками с категорией, описанием и кнопкой `Открыть`, которая переключает рабочую вкладку через единый механизм `ACTIVE_MAIN_TAB_KEY`.

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Keyboard shortcuts**.

### Реализовано: UI Modernization Track → Unified Page Layout

Все рабочие вкладки, кроме стартового Dashboard, получили общий `app-page-shell`: единый header, kicker, заголовок, subtitle, status badge, темный инженерный workspace, одинаковые радиусы, тени, границы, отступы и responsive-поведение. Это убирает ощущение разных прототипов внутри одного приложения: Data Management, LAS-редактор, LAS-корреляция, интерпретационные графики и документация теперь открываются в общей визуальной системе.

Для графиков, таблиц, LAS-редактора и расчетов сохранен темный рабочий фон, чтобы брендовая картинка не мешала числам, кривым и инженерным данным. Документация остается брендированной через hero-блок, но тоже помещается в общий shell.

Текущий следующий незавершенный пункт: **UI Modernization Track → Documentation Center v2**.



### Реализовано: UI Modernization Track → Documentation Center v2

Вкладка `Инструкции и документация` переработана в Documentation Center v2. Вместо набора разрозненных блоков добавлены быстрые карточки переходов, внутренняя таблица содержания с anchor-ссылками, разделы быстрого запуска, проверки готовности, рабочего сценария, формата данных, LAS workflow, горячих клавиш, FAQ и troubleshooting.

Hero-блок сохраняет фирменную картинку и логотип, но основной справочный текст размещается на читаемой glass-панели. Пустые темные блоки удалены: пользователь сразу видит структуру справочного центра, быстрые действия и полные markdown-документы проекта в нижних expander-блоках.

Текущий следующий незавершенный пункт: **UI Modernization Track → Quick Actions Wiring**.


### Реализовано: UI Modernization Track → Quick Actions Wiring

Быстрый доступ на стартовой странице переведен на единый реестр `START_ACTIONS`: проект, импорт LAS/CSV/Excel, LAS-редактор, LAS-корреляция, графики и отчеты, инструкции, настройки и лицензия. Все кнопки создаются из одного источника данных, имеют стабильные ключи `dashboard_quick_action_...`, tooltip-подсказки, описание назначения и реальный `target_tab` из `APP_TABS`.

Статические карточки Dashboard теперь строятся через `_dashboard_quick_action_cards_html()` из того же реестра, поэтому визуальные карточки и рабочие Streamlit-кнопки больше не расходятся по названиям и назначению. Нажатие кнопки вызывает `_trigger_quick_action(action)`, сохраняет последнее действие в `DASHBOARD_LAST_QUICK_ACTION_KEY`, переключает активную страницу через общий механизм `ACTIVE_MAIN_TAB_KEY` и выполняет `st.rerun()`.

Добавлены smoke-тесты на полноту реестра, валидность target-tab, наличие рабочих ключей, tooltip и документацию этапа.

### Реализовано: UI Modernization Track → Command Palette Search

Глобальная командная палитра расширена до полноценного поиска по приложению и активному проекту. Теперь она строит результаты из единого набора навигационных разделов, рабочих команд, quick actions, документационных разделов, quick links Documentation Center и объектов дерева проекта. Поиск покрывает команды, проекты, скважины, LAS-файлы, кривые, расчеты, отчеты и документацию.

Добавлены категории поиска `Все`, `Команды`, `Разделы`, `Проекты`, `Скважины`, `LAS`, `Кривые`, `Расчеты`, `Отчеты`, `Документация`, `Недавние` и `Избранное`. Результаты ранжируются по совпадению в названии, категории, ключевых словах, недавности и избранному. Кнопка `Открыть` сохраняет команду в историю и переключает активный раздел приложения, а звездочка позволяет закреплять часто используемые команды. В интерфейсе явно указан сценарий `Ctrl+K`, `Enter` и `Esc`, насколько это возможно в Streamlit без низкоуровневого JavaScript-перехвата.

### Реализовано: UI Modernization Track → Responsive Dashboard Layout

Dashboard получил явную responsive-сетку для целевых экранов: 1366×768, 1440×900, 1600×900, 1920×1080 Full HD, 2560×1440, 3440×1440 ultrawide, 3840×2160 4K, tablet, mobile и narrow mobile. В код добавлен реестр `RESPONSIVE_DASHBOARD_TARGETS`, CSS-переменные `--responsive-dashboard-columns`, `--responsive-card-gap`, `--responsive-dashboard-padding` и отдельные media queries для ноутбуков, больших мониторов, планшетов и телефонов.

На узких экранах Dashboard переходит в одну колонку, quick actions становятся `auto-fit` карточками, sidebar скрывается, второстепенные блоки `Новости`, `Советы` и тяжелый preview-график отключаются, а `overflow-x: hidden` предотвращает горизонтальную прокрутку. На 2K/ultrawide/4K сетка получает ограничение плотности и увеличенные отступы, чтобы приложение не выглядело растянутым.

Текущий следующий незавершенный пункт: **UI Modernization Track → Background Manager Final Pass**.

### Реализовано: UI Modernization Track → Background Manager Final Pass

Финальный проход Background Manager разделил страницы приложения на два режима: брендированные экраны и инженерные рабочие поверхности. В код добавлен реестр `BACKGROUND_MANAGER_RULES` с отдельными правилами для Dashboard, Documentation Center, Data Management, LAS-редактора, LAS-корреляции и интерпретационных графиков. Для брендированных экранов сохранены позиционирование, масштаб и прозрачность фона; для рабочих экранов включен `dark-workspace` без декоративного фонового изображения.

Добавлены presets `BACKGROUND_POSITION_PRESETS` и `BACKGROUND_OPACITY_PRESETS`, чтобы настройки позиции, overlay и glass-прозрачности были централизованы, а не размазаны по CSS. LAS Editor, correlation plots, interpretation graphs, таблицы, отчеты и mapping-панели остаются на темной инженерной поверхности через класс `background-rule-dark-workspace`, `background-image: none !important` и усиленный контраст data/plot surfaces. Это сохраняет фирменный вид приложения на стартовой странице и документации, но не мешает чтению чисел, осей, линий LAS-кривых и табличных данных.

Текущий следующий незавершенный пункт: **UI Modernization Track → Glass UI System**.

### Реализовано: UI Modernization Track → Glass UI System

Добавлена общая glass UI-система для карточек, панелей, hero-блоков, sidebar, navbar, modal и tooltip. В коде появился реестр `GLASS_UI_TOKENS`, единые CSS-переменные прозрачности, границ, теней, blur и контрастного текста: `--glass-card-bg`, `--glass-panel-bg`, `--glass-border-token`, `--glass-shadow-token`, `--glass-blur-token`, `--glass-high-contrast-text` и `--glass-dark-overlay-control`.

Dashboard, Documentation Center и общий page shell теперь используют shared transparency tokens вместо разрозненных локальных значений. Для рабочих инженерных экранов сохранена защита читаемости: в режиме `background-rule-dark-workspace` glass-поверхности становятся почти непрозрачными, blur отключается, а LAS Editor / Graphs / Reports / tables остаются на темном фоне без декоративной картинки. Добавлены smoke-тесты на наличие компонентов `glass-card`, `glass-panel`, `glass-hero`, `glass-sidebar`, `glass-navbar`, `glass-modal`, `glass-tooltip`, readability checks и документацию этапа.

Текущий следующий незавершенный пункт: **UI Modernization Track → Navigation Animations**.

### Реализовано: UI Modernization Track → Navigation Animations

Навигационная система получила общий слой motion-токенов `NAVIGATION_ANIMATION_TOKENS` и реестр возможностей `NAVIGATION_ANIMATION_FEATURES`. Реализованы page fade transition, page slide transition, hover/press-анимации кнопок, hover-анимации карточек, активный underline для выбранного раздела, плавное раскрытие sidebar, анимация открытия/закрытия command palette, skeleton shimmer, progress indicator и smooth scroll.

CSS-анимации вынесены в единые `@keyframes`: `gas-page-fade`, `gas-page-slide`, `gas-active-underline`, `gas-sidebar-expand`, `gas-sidebar-collapse`, `gas-command-open`, `gas-command-close`, `gas-skeleton-shimmer` и `gas-progress-pulse`. Для доступности добавлен `@media (prefers-reduced-motion: reduce)`, который отключает продолжительное движение у пользователей с ограничением анимаций. Навигационные кнопки теперь имеют hover, active/press state и визуальную обратную связь без декоративных нерабочих элементов.

Текущий следующий незавершенный пункт: **UI Modernization Track → Branding Assets**.

### Реализовано: LAS Professional → Curve Manager → Curve metadata editor

LAS-редактор получил metadata-only редактор кривых. Новый модуль `las_editor/curve_metadata.py` формирует карточки metadata для каждой LAS-кривой на основе существующего контекста Curve Manager: alias, группы, категории и единицы измерения. Пользователь может вручную заполнить описание кривой, источник данных, прибор/инструмент, статус, качество и комментарий без изменения числовых значений LAS.

Во вкладке `LAS-редактор` добавлен блок `Curve Manager · Curve metadata editor` со сводкой по статусам и качеству, таблицей всех кривых, выбором кривой и поля metadata, контролируемыми списками для `status`/`quality`, текстовыми полями для описания, источника, инструмента и комментария. Все изменения пишутся в `curve_metadata`, обновляют `manifest`, имеют историю с `timestamp`, `reason`, `source` и поддерживают `Undo последней metadata-правки`.

Добавлены unit-тесты `tests/test_curve_metadata.py`: проверяется построение metadata из контекста Curve Manager, сохранение в manifest, валидация входных данных, no-op при повторном назначении, undo последней операции, строки таблицы, сводка и нормализация metadata-полей.

Текущий следующий незавершенный пункт: **LAS Professional → Curve Manager → Curve mnemonics dictionary**.


### Реализовано: LAS Professional → Curve Manager → Curve duplicate detection

LAS-редактор получил диагностический инструмент поиска дубликатов кривых. Новый модуль `las_editor/curve_duplicates.py` сравнивает пары LAS-кривых по canonical mnemonic/alias, точному совпадению числовых значений, доле совпадающих shared samples и высокой корреляции. Алгоритм возвращает только кандидатов для инженерной проверки и не удаляет, не объединяет и не переименовывает исходные LAS-данные.

Во вкладке `LAS-редактор` добавлен блок `Curve Manager · Curve duplicate detection` после metadata editor и перед merge tools. Пользователь может настроить порог корреляции и порог совпадения значений, запустить диагностику, увидеть сводку по severity (`exact`, `high`, `medium`, `name`) и таблицу кандидатов с причиной, корреляцией, match ratio, alias, группой, категорией, единицей измерения и безопасной рекомендацией.

Добавлены unit-тесты `tests/test_curve_duplicates.py`: проверяется exact numeric duplicate, alias/canonical duplicate, high correlation candidate, форматирование таблицы и summary, а также пустой результат для различных кривых.

Текущий следующий незавершенный пункт: **LAS Professional → Curve Manager → Curve mnemonics dictionary**.

### Curve Manager: Curve quality flags

Статус: реализовано. В LAS-редактор добавлен diagnostic-only блок `Curve Manager · Curve quality flags`. Он проверяет кривые на пропуски, длинные flat-интервалы, spike-кандидаты и нечисловые колонки. Результат выводится как таблица флагов с severity, количеством затронутых точек, группой, категорией, единицей и инженерной рекомендацией. Исходный DataFrame не изменяется.

В этом же этапе выполнена UI-поправка Dashboard: статистика проекта и блок активности адаптированы под ноутбуки 1366×768/1440×900, сетка перестраивается в две колонки без горизонтального переполнения. Масштаб фирменной фоновой картинки уменьшен примерно на 30%, чтобы фон оставался заметным, но не ломал рабочую верстку. README очищен от лишних повторов и оставлен как краткая техническая точка входа.

### Dashboard 3.0 navigation cleanup
- [x] Removed empty decorative rectangles above top navigation buttons.
- [x] Kept one real clickable button per section with a compact caption.
- [x] Added static regression checks to prevent returning empty nav wrappers.

Commit: Clean dashboard navigation cards
