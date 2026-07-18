# v225.7 іске асыру жоспары

## Мақсат

Тоғыз architecture-boundary бұзушылығын жою, brittle source assertion-дарды орындалатын behavior test-пен ауыстыру және regression жасырмай controlled visual rebaseline орындау.

## Орындалған жұмыстар

1. Lifecycle және infrastructure deletion UI қабатынан application service-ке көшірілді.
2. Session-scoped cache telemetry application container-ге берілді.
3. Route/startup/cache-coherence lifecycle runtime diagnostics service иелігіне берілді.
4. Rerun тек бірыңғай gate арқылы орындалады.
5. 26 source assertion behavior/view-model contract-пен ауыстырылды (18 legacy, бір Print Center contract және 7 PDF preview contract).
6. 13 visual contract SHA-256 semantic snapshot manifest-ке көшірілді.
7. Historical version pin current-build identity contract-пен ауыстырылды.
8. 51 legacy contract evidence және replacement test-пен жабылды.

## Definition of Done

- 9 architecture test-тің барлығы өтеді;
- 26 source-contract replacement-тің барлығы өтеді;
- 13 visual snapshot валидациядан өтеді;
- active legacy debt нөлге тең;
- толық regression suite: **2855 passed, 0 failed**;
- кеңейтілген release жиыны: **480 passed**;
- `ru/kk/en` құжаттамасы синхрондалған.
