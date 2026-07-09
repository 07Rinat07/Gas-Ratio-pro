# Формулы Gas Ratio Interpreter v0.4

Формулы v0.4 основаны на открыто опубликованных справочных источниках и проектной методике. Для каждой формулы должен быть указан источник или статус проверки.
Программа выполняет предварительные инженерные расчеты и не формирует окончательное
геологическое заключение без проверки по ГИС, литологии, буровому контексту, фону,
газу СПО, газу наращивания и рециркуляции.

## Суммы компонентов

```text
ΣC4 = iC4 + nC4
ΣC5 = iC5 + nC5
ΣC  = C1 + C2 + C3 + ΣC4 + ΣC5
```

## Газовые коэффициенты

```text
Wh   = (C2 + C3 + ΣC4 + ΣC5) * 100 / ΣC
Bh   = (C1 + C2) / (C3 + ΣC4 + ΣC5)
BAR2 = C1 / C2
```

Деление на 0 возвращает `NaN`, чтобы приложение не падало и инженер видел
проблемное место в данных. Перед интерпретацией нужно проверить mapping, нули,
пропуски и единицы измерения компонентов `C1-C5`: компоненты должны быть в
согласованных единицах внутри одного файла/интервала.

## Oil indicator / inverse oil indicator

```text
Oil indicator         = (C3 + ΣC4 + ΣC5) / C1
Inverse oil indicator = C1 / (C3 + ΣC4 + ΣC5)
```

Эти коэффициенты добавлены как справочные по литературному источнику mud gas
analysis. Источник отмечает, что происхождение oil indicator ratio не раскрыто,
поэтому коэффициенты нельзя использовать как самостоятельную окончательную
классификацию. Деление на 0 возвращает `NaN`.

## Pixler ratios

```text
C1/C2
C1/C3
C1/ΣC4
C1/ΣC5
```

Границы визуальных зон Pixler в v0.3 вынесены в конфиг и должны быть заменены
на точные корпоративные линии после подтверждения методики.

## Ternary ratios

```text
C2/ΣC
C3/ΣC
nC4/ΣC
```

## Ch

В v0.4 режим A приведен к Haworth Character Ratio:

```text
Ch = (ΣC4 + ΣC5) / C3
```

Предыдущее выражение `Ch = (C3 + ΣC4 + ΣC5) / (ΣC4 + ΣC5)` было удалено из основного расчетного контура как неподтвержденное для Haworth Character Ratio. Если в будущем понадобится корпоративный альтернативный Ch, он должен быть добавлен отдельным именованным режимом с собственным источником, тестами и предупреждением в интерфейсе.

## Сравнение с mud gas literature

В `docs/mud_gas_analysis_literature.md` добавлен источник `Application of mud gas analysis for reservoir evaluation`.
Он подтверждает формулы `Wh`, `Bh`, `Ch`, Pixler ratios и oil/inverse oil indicator как справочную базу для будущей сверки.

Важно: все границы классификации являются инженерными ориентирами, а не юридически или методически утвержденной окончательной диагностикой. Итоговая интерпретация требует сверки с ГИС, литологией, условиями бурения, качеством газового каротажа и испытаниями.


## Правила источников и авторского права

- В документации проекта нельзя копировать большие фрагменты статей, таблицы или рисунки из публикаций без разрешения правообладателя.
- В проекте допускается краткое описание общеизвестной расчетной зависимости с обязательной библиографической ссылкой на автора/публикацию.
- Если источник является preprint или учебным материалом, его статус указывается явно.
- Если формула или границы классификации являются корпоративной методикой, их нельзя смешивать с открытыми литературными формулами без отдельного режима расчета.
- Для патентно-чувствительных алгоритмов в проекте используется только открыто опубликованное описание и собственная реализация; перед коммерческим распространением требуется отдельная юридическая проверка freedom-to-operate.

## Bibliography / источники формул

1. Haworth J.H., Sellens M., Whittaker A. (1985). Interpretation of hydrocarbon shows using light C1-C5 hydrocarbon gases from mud-log data. AAPG Bulletin, 69(8), 1305-1310.
2. Pixler B.O. (1969). Formation Evaluation by Analysis of Hydrocarbon Ratios. Journal of Petroleum Technology, 21(6), 665-670, SPE-2254-PA.
3. Archie G.E. (1942). The Electrical Resistivity Log as an Aid in Determining Some Reservoir Characteristics. Transactions of AIME / Journal of Petroleum Technology, DOI 10.2118/942054-G.
4. Simandoux P. (1963). Dielectric measurements on porous media, application to measurement of water saturation: study of the behavior of argillaceous formations. Revue de l’Institut Français du Pétrole.
5. Bardon C., Pied B. (1969). Formation Water Saturation in Shaly Sands. SPWLA Annual Logging Symposium.
6. Poupon A., Leveaux J. (1971). Evaluation of water saturation in shaly formations. The Log Analyst.
7. Muriungi N. (2025). Application of mud gas analysis for reservoir evaluation. EarthArXiv preprint.
