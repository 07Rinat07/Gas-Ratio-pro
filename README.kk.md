# GAS RATIO PRO

Мұнай-газ саласындағы ұңғымалық, геологиялық-геофизикалық және жобалық деректерді импорттауға, сапасын бақылауға, нұсқаларын басқаруға, талдауға, интерпретациялауға және визуализациялауға арналған кәсіби үш тілді инженерлік платформа.

**Тіл:** [Русский](README.ru.md) · Қазақша · [English](README.en.md)

## Құжаттама

- [Пайдаланушы нұсқаулығы](docs/user/kk/index.md)
- [Әзірлеуші құжаттамасы](docs/developer/kk/index.md)
- [Қолдау көрсетілетін форматтар](docs/user/kk/supported_formats_and_legal_sources.md)
- [Жоба жоспары](docs/project/PROJECT_PLAN.kk.md)
- [Ағымдағы күй](docs/PROJECT_STATUS.kk.md)

## Қолдау көрсетілетін және дамытылатын форматтар

- **LAS 1.x/2.x/3.x** — импорт, ескі файлдармен үйлесімділік, редакциялау, QC, нұсқалар, визуализация және экспорт;
- **Excel/CSV** — импорт, өрістерді сәйкестендіру, есептеулер және визуализация;
- **DLIS/LIS79** — optional `dlisio` адаптері арқылы метадеректерді алдын ала қарау;
- **SEG-Y** — тақырыптарды алдын ала қарау, trace-header inventory және геометрия диагностикасы;
- **PDF/DOCX** — инженерлік және QC есептері;
- **GeoPackage/Shapefile/GeoTIFF, GRDECL/RESQML, HDF5/NetCDF** — Data/GIS/Reservoir Platform келесі кезеңдері.

## Негізгі ішкі жүйелер

- Workbench және Project Explorer;
- Unified Import Pipeline, импорт профильдері және readiness score;
- Data Platform: өзгермейтін артефактілер, Dataset Manifest, SHA-256, provenance және lineage;
- LAS QC Platform және үш тілдегі PDF/DOCX есептері;
- газ-геохимиялық есептеулер және интервалдарды интерпретациялау;
- ұңғымаларды корреляциялау және көпұңғымалық планшеттерге дайындық;
- орыс, қазақ және ағылшын тілдеріндегі интерфейс пен құжаттама.

## Stable релиз v225.8

- Stage 4 **stable** арнасына ауыстырылды;
- Live Workbench Acceptance нақты server health және орындалатын Streamlit session тексереді;
- build/source identity және Workbench-тің бес аймағы расталды;
- LAS command және LAS Workspace traceback-сіз орындалады;
- stable promotion нәтижесі: **14/14 passed**;
- full regression suite: **2858 passed, 0 failed**;
- gate іске қосу: `.\run_app.ps1 -ForceRestart -Acceptance`;
- [пайдаланушы нұсқаулығы](docs/user/kk/stable_release_and_acceptance.md) · [архитектура](docs/developer/kk/live_workbench_acceptance_architecture.md).

## Орнату және іске қосу

Python 3.10+ қажет.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\run_app.ps1
```

## Автор

**Сармулдин Р. Р.** — инженер-бағдарламашы, GAS RATIO PRO авторы.
