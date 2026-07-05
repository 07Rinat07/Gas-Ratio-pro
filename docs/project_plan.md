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
- [ ] Global command palette.
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
- [ ] About dialog redesign.
- [ ] Application identity metadata.
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

## Следующий пункт разработки

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Global command palette**.


### Реализовано: UI Modernization Track → Dashboard background shell

Главная страница получила новый Dashboard shell на основе фонового изображения `assets/dashboard/gas_ratio_brand_background.png`. Изображение используется только на стартовой странице и накрывается темным gradient overlay, чтобы текст, карточки и кнопки оставались читаемыми. Рабочие области с графиками, LAS-кривыми, таблицами и числами не переводятся на фоновую картинку, чтобы не ухудшать видимость инженерных данных.

Dashboard теперь содержит HTML/CSS shell с верхним navbar, glass-панелями, блоком приветствия, недавними проектами, быстрым доступом, динамическими новостями, статистикой проекта, активностью, ежедневным советом и блоком авторских прав. Значения в карточках строятся из реального состояния проекта: списка проектов, LAS-файлов, расчетов, экспортов, скважин и активности, если соответствующие данные уже есть в локальном хранилище.

## Следующий пункт разработки

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Global command palette**.


### Реализовано: UI Modernization Track → Dashboard application shell

Главная страница переработана из узкого прототипа в полноширинный application shell. Streamlit `block-container` в широком режиме больше не ограничивает Dashboard фиксированной шириной, поэтому стартовая область занимает доступное пространство экрана и не оставляет большие пустые поля по бокам.

Dashboard получил современный navbar с брендом, навигационными кнопками, поисковым чипом `Ctrl+K` и чипом активного проекта. Фоновое изображение `assets/dashboard/gas_ratio_brand_background.png` растягивается на всю Dashboard-область, позиционируется по центру/правому краю и перекрывается менее агрессивным затемняющим overlay: карточки остаются читаемыми, но логотип и буровая визуально видны как часть дизайна, а не как скрытая картинка под блоками.

Основные виджеты переведены в адаптивную glass-сетку: приветствие, недавние проекты, быстрый доступ, статистика проекта, активность, новости, полезные советы, mini log preview и лицензия. Статистика, проекты, новости, активность и советы строятся из реального состояния локального проекта и session state. Рабочие модули LAS Editor, графики, таблицы, correlation и reports закрываются темными рабочими панелями для читаемости кривых, чисел и инженерных таблиц.

### Реализовано: UI Modernization Track → Responsive dashboard navigation refresh

После визуальной проверки чернового shell удален неэффективный левый rail-sidebar внутри Dashboard: он занимал место, не давал полезной навигации и ухудшал внешний вид. Быстрый доступ переведен в крупные информативные action-карточки со ссылками-якорями на рабочие разделы: проект/импорт, LAS-редактор, LAS-корреляция, графики/отчеты и инструкции.

Фирменный фирменный Gas Ratio Pro фон теперь доступен как общий бренд-слой приложения. Для рабочих вкладок он приглушается темным overlay, а реальные графики, LAS-кривые, таблицы и редакторы остаются на темных панелях, чтобы фон не мешал данным. Верхние Streamlit-вкладки стилизованы как крупные кнопки с активным состоянием и hover-анимацией, чтобы переключение разделов визуально воспринималось как меню приложения. Добавлены CSS-breakpoints для широкого экрана, обычного монитора и мобильной ширины: dashboard-сетка перестраивается из трех колонок в две и одну колонку.

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Global command palette**.


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

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Global command palette**.


### Реализовано: UI Modernization Track → Documentation hero banner

Вкладка `Инструкции и документация` получила отдельный hero-banner вместо пустого темного прямоугольника. В баннер встроен новый фирменный wide-арт `assets/dashboard/documentation_hero.png` с буровой, логотипом Gas Ratio Pro и авторством Rinat Sarmuldin. Изображение используется как верхний визуальный блок документации, а не как случайный затемненный фон, поэтому пользователь сразу видит фирменную картинку.

Документационный hero использует адаптивную высоту, `background-size: cover`, центрированное позиционирование и мягкий overlay. Заголовок и вводный текст размещены на отдельной glass-панели, чтобы картинка оставалась видимой, а текст читался на ноутбуках, больших мониторах и узких экранах.

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Global command palette**.

### UI Modernization Track — Documentation hero image placement

- [x] Documentation hero image placement

Вкладка `Инструкции и документация` больше не использует пустой темный прямоугольник. Верхний блок документации рендерит изображение `assets/dashboard/documentation_hero.png` напрямую через HTML `<img>`, поэтому фирменная картинка с буровой, названием `GAS RATIO PRO` и авторством отображается внутри верхнего баннера. Поверх изображения оставлен легкий градиент для читаемости, справа добавлен небольшой фирменный логотип-бейдж. Лишняя техническая подпись про использование фонового изображения удалена из карточки `Лицензия и авторские права` на Dashboard.

### Реализовано: UI Modernization Track → Dashboard brand visibility tuning

Стартовый Dashboard получил более прозрачные glass-панели и более легкий общий overlay: фон теперь виден как часть интерфейса, а не как скрытая картинка под темными блоками. Для этого ослаблены затемняющие градиенты, снижена непрозрачность карточек, quick-action tiles, метрик и навигационной панели, а blur оставлен минимальным, чтобы брендовый арт сохранял детали.

Рабочие инженерные экраны пока сохраняют темные читаемые панели. Следующий практический этап по визуальному плану: **Global command palette / Ctrl+K search**.


### Реализовано: UI Modernization Track → Sidebar 2.0 project control center

Левый sidebar переработан из вспомогательного Streamlit-блока в проектный control center. Вверху добавлен фирменный блок Gas Ratio Pro с логотипом, активным проектом и краткой идентификацией продукта. Ниже отображаются проектная сводка, состояние проекта, режим лицензии, быстрые переходы в рабочие разделы и последние материалы активного проекта.

Структура проекта, поиск, перемещение объектов и цветовые метки сохранены, но теперь убраны в свернутый expander, чтобы не занимать постоянное место и не перегружать интерфейс. Sidebar стал информативным: пользователь сразу видит количество скважин, LAS-файлов, расчетов, экспортов, состояние данных и недавние действия.

Текущий следующий незавершенный пункт: **UI Modernization Track → Application Shell → Global command palette**.
