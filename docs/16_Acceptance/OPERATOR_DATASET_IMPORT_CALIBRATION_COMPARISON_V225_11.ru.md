# Acceptance v225.11 — Operator Dataset Import & Calibration Comparison

Проверка считается успешной, когда:

- ZIP принимает только три утверждённых root-файла;
- project scope, owner, legal basis, processing/derivative permissions и expiration валидны;
- method-registry fingerprint совпадает с production contract;
- package и rights fingerprints детерминированы;
- `package_id + version` immutable;
- stored-file tampering обнаруживается до расчёта/экспорта;
- comparison охватывает все 10 зарегистрированных методов;
- project authorization допускает 9 final-report eligible методов;
- foundation Dual Water остаётся заблокированным;
- смена активного пакета очищает export caches;
- artifact/history содержат authorization package ID и operator fingerprint;
- без активного operator package работает Stage 5.1 baseline;
- `python scripts/run_petrophysical_stage_5_2_gate.py` создаёт passed evidence;
- Live Workbench и full regression проходят без failures.
