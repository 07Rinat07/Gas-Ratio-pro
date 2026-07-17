# Page Chrome & Print Center Contract v225.3

## Мақсат

Ортақ физикалық колонтитулдарды, бет нөмірін және қайталанатын шартты белгілерді қосу, сондай-ақ басып шығару орталығына бір page-aware пакеттен нақты профиль мен page count беру.

## Орындалды

1. `VisualizationPrintLayout` v2.1 header/footer/legend аймақтарын резервтейді.
2. `chrome_primitives` `page_pt` координаттарында бір рет құрылады.
3. SVG және PDF бірдей primitives салады, PNG SVG-ден жасалады.
4. Geometry signature v3 page chrome-ды қамтиды.
5. `VisualizationPageAwarePackage` v1.1 chrome contract және counts береді.
6. `VisualizationPrintCenterService` ru/kk/en тілдерінде жиынтық жасайды.
7. LAS Viewer export SVG/PDF/PNG үшін бір пакетті пайдаланады.
8. QA render-model және page-chrome primitives жиынтығын тексереді.

## Қабылдау критерийлері

- бет нөмірі әр физикалық бетте бар;
- шартты белгілер layout қайта есептелмей қайталанады;
- PDF/SVG/PNG page count және signature бірдей;
- A4/A3 readability floors сақталған;
- single-page fallback өшірілген;
- ru/kk/en құжаттамасы синхрондалған.
