# v225.4 іске асыру жоспары — Visible Print Center және тікелей DOCX/HTML preview

Күйі: **COMPLETED**.

## Мақсаттар

1. Physical package-ті көрінетін Print Center интерфейсіне қосу.
2. Экспортқа дейін нақты профиль мен әр бетті көрсету.
3. Канондық multi-page preview-ды DOCX/HTML форматына layout-ты қайта құрмай беру.
4. Бірінші бетке silent fallback жасауға тыйым салу.
5. `ru/kk/en` код пен құжаттаманы синхрондау.

## Іске асыру

- `ReportPageAwarePreviewService`;
- `ProfessionalPrintCenterViewModel`;
- page-aware package v1.2;
- preview contract v1.1;
- ортақ strict normalizer;
- Streamlit preflight және page selector;
- PDF/DOCX/HTML/bundle интеграциясы;
- үш тілдегі summary/page/error белгілері.
