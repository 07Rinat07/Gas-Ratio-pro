# PDF Renderer Foundation v30

## Назначение

`reports/presentation_pdf.py` добавляет первый PDF-рендерер для профессиональных инженерных отчетов Gas Ratio Pro.

Главное архитектурное правило сохраняется: PDF-рендерер не выполняет расчеты, не запускает интерпретацию и не выбирает интервалы заново. Он получает готовый `EngineeringDocument` и только отображает его в PDF.

## Поток данных

```text
PresentationModel
        ↓
EngineeringDocument
        ↓
PDF Renderer
        ↓
PDF bytes / export package
```

## Поддерживается в v30

- генерация PDF из `PresentationModel`;
- генерация PDF напрямую из `EngineeringDocument`;
- Unicode-шрифт для русскоязычных отчетов при наличии системного TrueType-шрифта;
- A4/A3/Letter;
- portrait/landscape;
- поля страницы в миллиметрах;
- таблицы с повторяемой строкой заголовка;
- notices/примечания;
- placeholder для планшета, чтобы Document Model уже сохранял позицию графического блока;
- PDF export package с manifest JSON.

## Ограничение текущего инкремента

В v30 планшетный график пока не встраивается как изображение. Блок `DocumentPlot` сохраняется в структуре документа и выводится как место для будущего raster/SVG backend. Это осознанный foundation-этап, чтобы сначала стабилизировать общий PDF pipeline без дублирования инженерской логики.

## Следующий шаг

PRS-7: подключить backend вставки планшетов в PDF: SVG/PNG-экспорт Plotly-фигуры, контроль DPI, размеры под A4/A3 и проверка отсутствия обрезки.
