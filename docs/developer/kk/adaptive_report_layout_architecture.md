# Есептердің бейімделетін макет архитектурасы

Revision 1 · Gas Ratio Pro v225.9

## Мақсаты

Контракт парақтың физикалық бағыты мен мазмұн геометриясы арасындағы айырмашылықты жояды. Нақты page/frame contract белгілі болса, renderer тұрақты енді қолданбауы тиіс.

## PDF

`reports/presentation_pdf.py` `content_width` және `content_height` мәндерін бет өлшемі мен өрістерден есептейді. Бұл мәндер metadata, кестелер және графиктерге беріледі. `_AutoScaleRasterImage` және `_AutoScaleSvgDrawing` объектіні 185/160 мм константаларымен емес, нақты ReportLab frame арқылы шектейді. Raster height бет aspect ratio бойынша таңдалады.

## DOCX

`reports/presentation_docx.py` пайдалы енді ағымдағы section параметрлерінен алады: бет ені минус сол және оң өрістер. Суреттер, metadata tables, document tables, legends және statistics осы енді немесе пропорционалды баған ендерін пайдаланады.

## HTML

`reports/presentation_html.py` Plotly үшін `responsive=True`, 100% енді контейнер және landscape/portrait CSS-класын қолданады. HTML жеке тұрақты print width сақтамайды.

## Контракт және rebaseline

Басқарушы контракт идентификаторы: `print-readability/v1.1`.

`reports/print_readability_contract.py` 1.1 нұсқасы мыналарды бекітеді:

- `layout_width_policy = available-frame`;
- `plot_aspect_policy = page-aware`;
- `landscape_minimum_frame_utilization = 0.90`;
- `narrative_table_width_policy = full-frame`.

Белсенді semantic baseline: `config/visual_rebaseline_contracts_v225_9.json`. Geometry/readability policy өзгерісі жаңа manifest, SHA-256 және behavioral test арқылы ғана қабылданады.

## Acceptance

`tests/test_report_landscape_frame_utilization_v225_9.py` A3 landscape PDF, DOCX және HTML форматтарын тексереді. Тест соңғы track пен кең кестенің frame оң жағына жетуін және DOCX plot кең section-ды пайдалануын растайды.
