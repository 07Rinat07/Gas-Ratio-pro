# Операторлық калибрлеу пакеттерінің сенімі және тексеруі

Revision 1 · Gas Ratio Pro v225.12

## Мақсаты

Stage 5.3 операторлық калибрлеу пакеттеріне басқарылатын trust workflow қосады. Stage 5.2 бастапқы ZIP өзгермейді. Қолтаңбалар, reviewer шешімдері, қайтару, мерзім, lineage және орталар арасындағы promotion бөлек сақталады.

## Белсенді ету алдындағы талаптар

Қорытынды есеп үшін пакет мына шарттар орындалғанда ғана белсенді болады:

1. ZIP импортталып, Stage 5.2 data-rights/calibration gate-інен өтті.
2. `package_fingerprint` үшін detached Ed25519 қолтаңбасы импортталды.
3. Ашық кілт trust registry ішінде бар, белсенді және жоба/орта үшін рұқсат етілген.
4. `technical_reviewer` пакетті мақұлдады.
5. `data_governance_reviewer` құқықтар мен production use-ты мақұлдады.
6. Пакет `development → validation → production` ретімен өткізілді.
7. Пакет, қолтаңба немесе кілт қайтарылмаған.
8. Деректер құқығы, қолтаңба және кілт мерзімі өтпеген.

## Professional Print Center

Операторлық калибрлеу бөлімінде:

- оператор ZIP импорттау;
- detached signature JSON импорттау;
- reviewer ID, аты, рөлі және шешімін енгізу;
- шешім негіздемесін сақтау;
- келесі ортаға promotion;
- міндетті негіздемемен package revocation;
- environment/signature/review/trust күйі;
- мерзімі аяқталатын құқықтар, қолтаңбалар және кілттер туралы ескерту бар.

Production trust decision өтпейінше пакет белсенді етілмейді.

## Detached signature

Қолтаңба қолданбадан тыс жабық Ed25519 кілтімен жасалады:

```powershell
python scripts/sign_operator_calibration_package.py `
  --package operator-calibration.zip `
  --private-key D:\secure\operator-signing-key.pem `
  --output operator-calibration.signature.json `
  --key-id operator-key-2026 `
  --project-id PROJECT-001 `
  --signer-id signer-001 `
  --signer-name "Жауапты қол қоюшы" `
  --organization-id OPERATOR-ORG
```

Жабық кілт жобада, Git ішінде, құжаттамада немесе release архивінде сақталмайды.

## Trust registry

Ашық кілттер `config/calibration_trust_registry_v225_12.json` ішінде тіркеледі. Әдепкі registry бос; бекітілген кілттер бақыланатын әкімшілік процесс арқылы қосылады.

Кілт contract мыналарды қамтиды: `key_id`, Ed25519 public key, owner, organization, allowed projects, allowed environments, validity period және status.

## Reviewer workflow

- `technical_reviewer` — numerical/calibration evidence және lineage тексереді;
- `data_governance_reviewer` — rights, classification, expiry және production use тексереді.

Жаңа шешім алдыңғы record-ты өшірмейді. Ол previous fingerprint сілтемесі бар жаңа immutable record жасайды.

## Revocation және expiry

Package, key немесе signature қайтарылуы мүмкін. `effective_at` басталғаннан кейін final export бұғатталады. Expiry monitor мерзімі өткен және жақын арада аяқталатын объектілерді бөлек көрсетеді.

## Lineage

Қолдау көрсетілетін қатынастар: `root`, `supersedes`, `derived_from`, `recalibrated_from`. Parent package сол жобада импортталуы керек. Self-reference, cycle және conflicting parent тыйым салынған.

## Қорытынды экспорт

`PresentationModel` жасалғанға дейін production trust қайта тексеріледі. ExportArtifact және Export History v6 trust decision ID, registry fingerprint, signature fingerprint, promotion ID, authorization package ID және operator package fingerprint сақтайды.

Foundation Dual Water `blocked_final_report` күйінде қалады. Trust workflow production formulas өзгертпейді және validation/calibration/report-policy gate-терін айналып өтпейді.
