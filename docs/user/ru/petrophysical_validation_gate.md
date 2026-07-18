# Петрофизический validation gate

В версии v225.9 петрофизические расчёты проверяются до использования в финальном инженерном отчёте. Gate не меняет формулы: он исполняет текущие production-функции на синтетических эталонах и сравнивает результат с утверждёнными значениями.

## Запуск

```bash
python scripts/run_petrophysical_validation_gate.py
```

## Rules

- 10 зарегистрированных методов должны пройти численную проверку.
- Единицы входов и выходов должны совпадать с registry.
- Каждый метод должен иметь источник, область применимости, ограничения, tolerance и uncertainty metadata.
- Метод с policy `blocked_final_report` может пройти численную проверку, но не разрешается для финального отчёта.

## Dual Water foundation

`petrophysics.sw_dual_water_foundation` остаётся прозрачным сравнительным приближением. Оно не является полной моделью Clavier–Coates–Dumanoir и блокируется для финального отчёта.

## Evidence

Результат сохраняется в `artifacts/validation/petrophysical_validation_v225_9.json`.
