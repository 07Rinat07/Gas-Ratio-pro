# План реализации v225.11 — Operator Dataset Import & Calibration Comparison

Статус: **IMPLEMENTED / verification pending**.

## Цели

1. Импортировать только operator-owned или legally cleared calibration packages.
2. Зафиксировать immutable source и rights fingerprints.
3. Хранить пакеты только в scope активного проекта.
4. Сравнивать project baseline и версии operator calibration.
5. Формировать versioned project authorization packages до renderer.
6. Сохранить production formulas и Stage 5/5.1 gates без изменений.

## Реализация

- package contract и ZIP security boundary;
- project repository, index и active selection;
- data-rights и expiration validation;
- повторная проверка сохранённых checksums;
- aggregation и comparison metrics;
- project-scoped authorization с baseline fallback;
- export cache isolation по authorization/rights context;
- evidence CLI и tri-language Print Center panel;
- export history schema v5.

## Definition of Done

- import/rights/fingerprint/tamper tests;
- version conflict и comparison tests;
- operator authorization блокирует renderer при недостаточных правах;
- baseline Stage 5.1 остаётся рабочим без активного пакета;
- Live Workbench 14/14;
- full regression 0 failures;
- документация ru/kk/en синхронизирована.
