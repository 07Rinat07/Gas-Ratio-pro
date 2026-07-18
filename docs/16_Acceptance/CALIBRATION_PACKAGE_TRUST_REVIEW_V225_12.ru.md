# Acceptance v225.12 — Calibration Package Trust & Review Workflow

Проверка считается успешной, когда:

- detached Ed25519 signature проверяется для точного `package_fingerprint`;
- tampered envelope или неверный project scope отклоняется;
- ключ должен быть active, иметь signing purpose, project/environment scope и действующий срок;
- validation требует current approval роли `technical_reviewer`;
- production требует current approvals ролей `technical_reviewer` и `data_governance_reviewer`;
- current reject блокирует promotion;
- promotion разрешён только `development → validation → production`;
- environment state без соответствующего immutable promotion record не даёт trust;
- package, key или signature revocation блокирует последующую авторизацию;
- expired rights, signature или key блокирует final report;
- lineage parent существует в том же проекте, cycles/self-reference запрещены;
- activation и final export проверяют production trust до renderer;
- ExportArtifact и Export History v6 содержат trust evidence;
- private keys не сохраняются приложением и отсутствуют в релизном архиве;
- `python scripts/run_petrophysical_stage_5_3_gate.py` создаёт passed evidence;
- production formulas не изменены;
- Live Workbench и full regression проходят без failures.

## Фактический результат

- Stage 5.3 gate: signature **1/1**, reviewer approvals **2/2**, promotion transitions **2/2**, production trust **passed**, private keys persisted **0**;
- Live Workbench Acceptance: **14/14**;
- полный regression-suite: **2934 passed, 0 failed**.
