# Операторлық калибрлеу пакеттері — revision 1

Stage 5.2 оператордың жеке калибрлеу деректерін Gas Ratio Pro production формулаларын өзгертпей жобаға қосуға мүмкіндік береді.

## Импортталатын құрам

ZIP түбірінде дәл үш файл болуы керек:

- `manifest.json` — жоба ауқымы, иесі, құқықтық негіз, рұқсаттар және SHA-256;
- `calibration_registry.json` — acceptance thresholds, sensitivity және uncertainty policy;
- `calibration_dataset.json` — калибрлеу жағдайлары, кірістер, параметрлер, бақыланған мәндер және бірліктер.

ZIP ішіндегі каталогтар, қосымша файлдар, абсолюттік жолдар және `..` тыйым салынған.

## Деректер құқықтары

Пакет тек мына шарттарда қабылданады:

- `legal_status`: `operator_owned`, `licensed` немесе `public_domain`;
- иесі мен құқықтық негізі көрсетілген;
- жергілікті өңдеу мен туынды талдауға рұқсат берілген;
- ағымдағы жоба `project_scope` ішінде бар;
- құқық мерзімі аяқталмаған;
- қорытынды есепте пайдалануға рұқсат жеке көрсетілген.

Жергілікті operator-owned пакет үшін тарату құқығы міндетті емес. Мұндай пакет жоба ішінде қалады және релиз архивіне кірмейді.

## Professional Print Center арқылы импорт

1. **Баспа және экспорт орталығын** ашыңыз.
2. **Жобаның операторлық калибрлеуі** бөлімін ашыңыз.
3. ZIP таңдап, **Импорттау және тексеру** түймесін басыңыз.
4. Импортталған нұсқаны таңдап, **Белсенді ету** түймесін басыңыз.
5. **Базалық калибрлеумен салыстыруды** орындаңыз.

Интерфейс операторды, нұсқаны, құқықтық мәртебені, әдістер санын, қорытынды есеп құқығын, белсенді күйді және қысқартылған fingerprint мәнін көрсетеді.

## Өзгермейтіндік және нұсқалар

`package_id + version` басқа fingerprint-пен қайта пайдаланылмайды. Бастапқы ZIP, registry, dataset, rights fingerprint және import evidence жоба ішінде өзгермейтін түрде сақталады. Сақталған файл өзгерсе, салыстыру мен экспорт бұғатталады.

## Салыстыру

Project baseline немесе басқа импортталған нұсқамен салыстыруға болады. Әр әдіс үшін passed/failed, RMSE delta, максималды қате delta, uncertainty envelope delta және `improved`/`degraded`/`equivalent` күйі жазылады.

## Қорытынды экспорт

Белсенді пакет бар болса, export boundary numerical validation, operator calibration, report policy, data-rights және fingerprint мәндерін қайта тексереді. Versioned project authorization package жасалып, оның ID және gate IDs экспорт тарихына жазылады. Диагностикаға ғана рұқсат етілген пакет финалдық PDF/DOCX/HTML renderer іске қосылғанға дейін бұғатталады.

## Пакет құру

```bash
python scripts/build_operator_calibration_package.py \
  --registry calibration_registry.json \
  --dataset calibration_dataset.json \
  --output operator_calibration.zip \
  --package-id operator-field-a \
  --version 1.0.0 \
  --project-id default \
  --operator-name "Example Operator" \
  --organization-id OP-001 \
  --owner "Example Operator" \
  --legal-status operator_owned \
  --legal-basis "Internal approval OP-001" \
  --final-report-use-allowed
```
