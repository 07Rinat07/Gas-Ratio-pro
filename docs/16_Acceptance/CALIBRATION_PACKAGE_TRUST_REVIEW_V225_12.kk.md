# v225.12 Acceptance — Calibration Package Trust & Review Workflow

Тексеру сәтті деп есептеледі, егер:

- detached Ed25519 signature нақты `package_fingerprint` үшін тексерілсе;
- tampered envelope немесе қате project scope қабылданбаса;
- key active, signing purpose, project/environment scope және жарамды мерзім талаптарына сай болса;
- validation үшін `technical_reviewer` current approval қажет болса;
- production үшін `technical_reviewer` және `data_governance_reviewer` current approvals қажет болса;
- current reject promotion-ды бұғаттаса;
- тек `development → validation → production` реттілігі рұқсат етілсе;
- immutable promotion record-сыз environment state trust бермесе;
- package, key немесе signature revocation authorization-ды бұғаттаса;
- expired rights, signature немесе key final report-ты бұғаттаса;
- lineage parent сол жобада болса, cycles/self-reference тыйым салынса;
- activation/final export renderer алдында production trust тексерсе;
- ExportArtifact және Export History v6 trust evidence сақтаса;
- private keys қолданбада сақталмаса және release ZIP ішінде болмаса;
- `python scripts/run_petrophysical_stage_5_3_gate.py` passed evidence жасаса;
- production formulas өзгермесе;
- Live Workbench және full regression failures жоқ аяқталса.

## Нақты нәтиже

- Stage 5.3 gate: signature **1/1**, reviewer approvals **2/2**, promotion transitions **2/2**, production trust **passed**, private keys persisted **0**;
- Live Workbench Acceptance: **14/14**;
- толық regression-suite: **2934 passed, 0 failed**.
