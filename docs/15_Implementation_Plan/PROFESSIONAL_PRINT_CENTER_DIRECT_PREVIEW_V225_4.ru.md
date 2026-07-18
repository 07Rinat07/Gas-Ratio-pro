# План реализации v225.4 — Visible Print Center и прямой DOCX/HTML preview

Статус: **COMPLETED**.

## Цели

1. Подключить physical package к видимому Print Center.
2. Показывать точный профиль и каждую страницу до экспорта.
3. Передавать канонический multi-page preview в DOCX/HTML без повторного layout.
4. Запретить silent first-page fallback.
5. Синхронизировать `ru/kk/en` код и документацию.

## Реализация

- `ReportPageAwarePreviewService`;
- `ProfessionalPrintCenterViewModel`;
- page-aware package v1.2;
- preview contract v1.1;
- общий strict normalizer;
- Streamlit preflight и page selector;
- интеграция форматов PDF/DOCX/HTML/bundle;
- трёхъязычные summary/page/error labels.

## Acceptance gates

- все страницы доступны в UI и downstream renderers;
- declared page count совпадает с каноническим массивом;
- raw DataFrame отсутствует в report payload;
- fallback на поле первой страницы запрещён;
- документация и version metadata синхронизированы.
