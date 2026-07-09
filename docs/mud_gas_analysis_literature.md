# Mud gas analysis: литературный источник

Этот документ фиксирует источник, который используется как справочная база для
дальнейшего сравнения расчетов, графиков и интерпретации в Gas Ratio Interpreter.
PDF не является корпоративно утвержденной методикой проекта; перед заменой
формул или границ в приложении нужна отдельная сверка с инженером.

## Источник

- Название: `Application of mud gas analysis for reservoir evaluation`.
- Статус: non-peer-reviewed preprint submitted to EarthArXiv.
- Автор в тексте: N. Muriungi, Rhodes University, South Africa.
- Автор в PDF metadata: Nancy Kendi.
- Correspondence: `n.muriungi.geo@gmail.com`.
- ORCID: `https://orcid.org/0009-0003-2634-4813`.
- Файл-источник внутри проекта: `docs/sources/mud-gas-analysis-reservoir-evaluation.pdf`.
- PDF metadata creation date: 2025-04-30.

## Что полезно для проекта

Источник показывает, что mud gas data можно использовать не только для
безопасности бурения, но и как качественный инструмент formation evaluation:

- выделение hydrocarbon-bearing zones;
- определение fluid type и fluid zonation;
- поиск fluid contacts;
- выявление depletion, gas cap, high GOR oil и connectivity;
- выбор точек sampling/well test;
- проверка неоднозначных случаев вместе с resistivity, GR, density/neutron logs.

Основной практический вывод для приложения: интерпретацию нельзя строить по
одному коэффициенту. Нужна совместная проверка нескольких gas ratios и, когда
доступно, сопоставление с ГИС-кривыми и буровым контекстом.

## Формулы из источника

В источнике используются легкие углеводородные компоненты `C1-C5`.
В проекте `C4` и `C5` представлены как суммы изо- и нормальных компонентов:

```text
ΣC4 = iC4 + nC4
ΣC5 = iC5 + nC5
ΣC  = C1 + C2 + C3 + ΣC4 + ΣC5
```

Haworth gas ratios:

```text
Wh = (C2 + C3 + ΣC4 + ΣC5) / ΣC * 100
Bh = (C1 + C2) / (C3 + ΣC4 + ΣC5)
Ch = (ΣC4 + ΣC5) / C3
```

Важно: режим `Ch` в основном расчетном контуре приложения приведен к формуле
Haworth Character Ratio `(ΣC4 + ΣC5) / C3`. Любой альтернативный корпоративный
режим `Ch` должен добавляться отдельным именованным режимом с собственным
источником, тестами и предупреждением в интерфейсе.

Pixler ratios:

```text
C1/C2
C1/C3
C1/ΣC4
C1/ΣC5
```

Oil indicator / inverse oil indicator:

```text
Oil indicator = (C3 + ΣC4 + ΣC5) / C1
Inverse oil indicator = C1 / (C3 + ΣC4 + ΣC5)
```

Источник отмечает, что происхождение oil indicator ratio не объяснено, а C2 в
формуле не используется. Поэтому для приложения этот коэффициент нужно вводить
как справочный и явно помечать его статус.

## Интерпретационные ориентиры

Haworth `Wh/Bh`:

- очень низкая wetness и высокий balance ratio указывают на dry gas/light gas;
- `0.5 <= Wh < 17.5` при `Wh < Bh < 100` указывает на gas, wetness растет при
  сближении кривых;
- `Bh < Wh` при `0.5 <= Wh < 17.5` может указывать на very wet gas,
  condensate или high gravity oil with high GOR;
- `17.5 <= Wh < 40` при `Bh < Wh` используется как ориентир oil zone;
- `Wh >= 40` может указывать на very low gravity oil или residual oil.

`Ch` используется как уточнение: по источнику `Ch < 0.5` подтверждает gas,
а `Ch > 0.5` показывает, что gas indication может быть связан с oil.

Pixler `C1/C2`:

- `< 2` - non-productive residue oil;
- `2-4` - low-gravity oil;
- `4-8` - medium gravity oil;
- `8-15` - high gravity oil;
- `10-20` - gas condensate;
- `15-65` - gas;
- `> 65` - light gas / potentially non-productive;
- `C1 only` - possible saltwater indication.

Oil indicator / inverse oil indicator:

- inverse oil indicator `100-14.3` - dry gas;
- `14.3-10` - condensate/light oil with high GOR;
- `10-2.5` - unsaturated oil;
- `2.5-1` - residual oil.

Эти границы пересекаются и не должны применяться как жесткая автоматическая
классификация без проверки по другим кривым.

## Требования к будущим вкладкам графиков

По структуре рисунков источника приложению нужны depth tracks, где глубина идет
по возрастанию сверху-вниз:

- GR/lithology track;
- total gas track;
- chromatograph components `C1-C5`;
- `Wh`, `Bh`, `Ch`;
- Pixler ratios, особенно `C1/C2`;
- inverse oil indicator;
- resistivity shallow/deep;
- density/neutron porosity;
- interpretation markers by depth;
- таблица выбранных пиков/интервалов с краткой причиной интерпретации.

Дополнительные требования по референсным изображениям:

- параметры берутся не только из расчетных колонок, но и из любых числовых
  LAS/Excel-колонок, которые пользователь выбрал для планшета;
- каждая кривая имеет свой ряд/трек, цвет, подпись, единицы измерения и
  собственный X-scale;
- X-scale должен работать в двух режимах: автоматический по выбранному интервалу
  и ручной `min/max`;
- при любой настройке масштаба и прокрутки глубина остается направленной вниз
  по возрастанию;
- шапка треков должна показывать минимум/максимум шкалы и режим цветовой
  заливки, чтобы печатный планшет читался без интерфейса Streamlit;
- горизонтальные маркеры глубины связываются с таблицей интерпретации под
  графиком, где для каждой метки фиксируется глубина/интервал и причина вывода.

Минимальный безопасный срез уже реализован во вкладке `Интерпретационные
графики`: режим `Планшет` строит выбранные числовые параметры отдельными треками,
поддерживает авто/ручной X-scale по каждому параметру, глубину вниз, маркеры,
таблицу маркеров, units из LAS, индивидуальные цвета/порядок треков и
редактируемые зоны.

Дополнительно добавлен preset `Mud gas analysis`: интерфейс выбирает только те
колонки, которые реально есть в таблице, в порядке из литературного обзора:
`GR/lithology`, `total gas`, `C1-C5`, `Wh/Bh/Ch`, Pixler ratios, inverse oil
indicator, resistivity и density/neutron. Отсутствующие компоненты не
подставляются искусственно.

Кнопка `Добавить mud-gas маркеры` строит справочные depth-маркеры по экстремумам
доступных колонок: максимум `total gas`, максимум `Wh`, минимум `C1/C2` и
максимум `inverse oil indicator`. Эти маркеры являются только подсказкой для
проверки интервала по ГИС, литологии и буровому контексту; они не являются
автоматической финальной классификацией флюида.

Следующие доработки: расширенные режимы заливки по каждому параметру, печатный
отчет и PDF/PNG/SVG экспорт планшета.

## Список литературы из PDF

Источник ссылается на следующие работы, которые стоит сохранить в проектной
библиографии для дальнейшей проверки:

- Allen P.A. & Allen J.R. (2013). Basin Analysis, 3rd edn.
- Blanc P. et al. (2003). SPE 84383.
- Breviere J. et al. (2002). SPWLA 43rd Annual Logging Symposium.
- Capone G. et al. (2012). Indonesian Petroleum Association.
- Ferroni G. et al. (2012). SPWLA 53rd Annual Logging Symposium.
- Hawker D. (2001). AAPG Short Course.
- Hawker D.P. (1999). Hydrocarbon evaluation and Interpretation.
- Haworth J.H., Sellens M. & Whittaker A. (1985). AAPG Bulletin 69.
- Pinna G.N. (2012). SPE talk, Geneva.
- Pinna G.N. & Law D.J. (2008). SPWLA 49th Annual Logging Symposium.
- Pixler B.O. (1969). SPE 2254-PA.
- Melo B., Ferroni G. & Pereira M. (2016). Técnico Lisboa.
- Mode A.W., Anyiam O.A. & Egbuje B.C. (2014). Journal of the Geological Society
  of India.
- Rider M. & Kennedy M. (2011). The geological interpretation of well logs.
- Zhou L. & Blue D. (2009). International Petroleum Conference and Technology
  Conference, Doha.

## Планшет: режимы заливки треков

Для каждого числового параметра планшета можно выбрать отдельный режим заливки:

- без заливки — используется для кривых, где важна только форма линии;
- заливка до нуля — удобна для газовых компонентов и расчетных индикаторов с
  естественной нулевой базой;
- заливка до левой границы шкалы — подходит для треков, где инженер хочет
  визуально выделить рост вправо относительно минимума выбранного X-scale;
- заливка до правой границы шкалы — полезна для обратных индикаторов и случаев,
  когда визуально нужно подчеркнуть уменьшение значения.

Эти режимы являются графическим оформлением планшета и не меняют расчетные
значения, классификацию интервалов или сохраненные исходные данные. Для
статического обсуждения планшет можно выгрузить в PNG, PDF или SVG; HTML-отчет
остается основным вариантом для печати с таблицами маркеров и зон.

