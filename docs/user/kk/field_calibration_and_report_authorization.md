# Далалық калибрлеу және қорытынды есепті авторизациялау

## Мақсаты

Stage 5.1 сандық validation gate үстіне екінші міндетті бақылау деңгейін қосады. Сандық түрде қайталанатын әдіс далалық калибрлеу контракты мен report policy тексерілгеннен кейін ғана қорытынды инженерлік есепке жіберіледі.

## Далалық калибрлеу жинағы

v225.10 нұсқасында **жобаға тиесілі синтетикалық field-surrogate dataset** (`project-owned`) пайдаланылады. Ол үшінші тараптың ұңғымалық деректерін қамтымайды, жобамен бірге таратуға рұқсат етілген және қайталанатын acceptance-жинақ ретінде қызмет етеді. Әр әдіс үшін кірістер, параметрлер, эталондық нәтиже, бірліктер, рұқсаттар және параметр үлестірімдері берілген.

## Professional Print Center диагностикасы

Read-only панель мыналарды көрсетеді:

- әдістің сандық мәртебесі;
- field calibration мәртебесі;
- report policy;
- RMSE және ең үлкен қате;
- uncertainty envelope ені;
- қорытынды есепке рұқсат немесе блоктау;
- validation, calibration және authorization gate идентификаторлары.

Панель орыс, қазақ және ағылшын тілдерінде қолжетімді және бастапқы деректерді немесе формулаларды өзгертпейді.

## Экспортты авторизациялау

Егер есептелген DataFrame machine-readable method context қамтыса, PDF/DOCX/HTML/bundle қорытынды экспорты тек `PetrophysicalReportAuthorizationApplicationService.assert_authorized()` тексеруінен кейін орындалады.

Тексеру **PresentationModel құрылмай тұрып және renderer іске қосылмай тұрып** орындалады. Блокталған жағдайда файл жасалмайды және пайдаланушыға бас тарту себебі көрсетіледі.

## Foundation Dual Water шектеуі

`petrophysics.sw_dual_water_foundation` сандық және диагностикалық калибрлеуден өтеді, бірақ policy `blocked_final_report`. Оны толық өнеркәсіптік Dual Water моделі ретінде қорытынды инженерлік есепке қосуға болмайды.

## Қайталанатын тексеру

```bash
python scripts/run_petrophysical_stage_5_1_gate.py
```

Evidence `artifacts/validation/` ішінде сақталады және contract fingerprints, calibration gate, authorization ID және әдіс деңгейіндегі шешімдерді қамтиды.
