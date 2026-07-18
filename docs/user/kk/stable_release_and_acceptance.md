# Stable релиз және Workbench acceptance

Revision: 1. Gas Ratio Pro `v225.8` үшін өзекті.

## Қалыпты іске қосу

```powershell
.\run_app.ps1 -ForceRestart
```

Launcher нұсқаны `BUILD_VERSION` файлынан оқиды, портты тексереді, мәжбүрлі қайта іске қосуда Python cache файлдарын тазартады және белсенді жоба каталогындағы `app/streamlit_app.py` файлын іске қосады.

## Stable-релизді автоматты қабылдау

```powershell
.\run_app.ps1 -ForceRestart -Acceptance
```

Gate уақытша loopback Streamlit серверін іске қосып, мыналарды тексереді:

- health endpoint;
- build нұсқасы және абсолютті source path;
- Toolbar;
- Project Explorer;
- Workspace Host;
- Properties;
- Status Bar;
- LAS командасының орындалуы;
- LAS Workspace traceback-сіз ашылуы.

JSON есеп `artifacts/acceptance/live_workbench_acceptance.json` файлына жазылады. Stable релиз тек `passed: true` болғанда және барлық міндетті тексеру өткенде қабылданады.

## Қауіпсіздік

Acceptance пайдаланушының LAS файлдарын импорттамайды және өзгертпейді. Ағымдағы project metadata контексті мен қауіпсіз Workbench навигациясы пайдаланылады. Уақытша сервер тексеруден кейін міндетті түрде тоқтатылады.
