# Архитектура адаптивного макета отчётов

Revision 1 · Gas Ratio Pro v225.9

## Назначение

Контракт устраняет расхождение между физической ориентацией листа и геометрией содержимого. Renderer не имеет права использовать фиксированную ширину, если фактический page/frame contract уже известен.

## PDF

`reports/presentation_pdf.py` вычисляет `content_width` и `content_height` из размера страницы и полей. Эти значения передаются метаданным, таблицам и графикам. `_AutoScaleRasterImage` и `_AutoScaleSvgDrawing` ограничивают объект реальным ReportLab frame, а не константами 185/160 мм. Raster height выбирается с учётом aspect ratio страницы.

## DOCX

`reports/presentation_docx.py` получает полезную ширину из текущей section: размер страницы минус левое и правое поля. Изображения, metadata tables, document tables, legends и statistics используют эту ширину или пропорциональное распределение колонок.

## HTML

`reports/presentation_html.py` формирует Plotly с `responsive=True`, контейнером шириной 100% и landscape/portrait CSS-классом. HTML не хранит отдельную фиксированную печатную ширину.

## Контракт и rebaseline

Идентификатор управляющего контракта: `print-readability/v1.1`.

`reports/print_readability_contract.py` версии 1.1 фиксирует:

- `layout_width_policy = available-frame`;
- `plot_aspect_policy = page-aware`;
- `landscape_minimum_frame_utilization = 0.90`;
- `narrative_table_width_policy = full-frame`.

Активный semantic baseline находится в `config/visual_rebaseline_contracts_v225_9.json`. Любое изменение geometry/readability policy требует нового manifest, SHA-256 и поведенческого теста.

## Acceptance

`tests/test_report_landscape_frame_utilization_v225_9.py` проверяет A3 landscape PDF, DOCX и HTML. Тест подтверждает, что крайний трек и широкая таблица достигают правой части рабочего фрейма, а DOCX plot использует широкую section.
