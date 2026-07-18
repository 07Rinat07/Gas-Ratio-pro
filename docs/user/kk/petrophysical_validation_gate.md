# Петрофизикалық validation gate

v225.9 нұсқасында петрофизикалық есептеулер соңғы инженерлік есепте қолданылмас бұрын тексеріледі. Gate формулаларды өзгертпейді: ағымдағы production-функцияларды синтетикалық эталондарда орындайды және нәтижені бекітілген мәндермен салыстырады.

## Іске қосу

```bash
python scripts/run_petrophysical_validation_gate.py
```

## Rules

- Тіркелген 10 әдіс сандық тексеруден өтуі керек.
- Кіріс және шығыс өлшем бірліктері registry-мен сәйкес болуы керек.
- Әр әдісте дереккөз, қолданылу аймағы, шектеулер, tolerance және uncertainty metadata болуы керек.
- `blocked_final_report` policy бар әдіс сандық тексеруден өте алады, бірақ соңғы есепке рұқсат етілмейді.

## Dual Water foundation

`petrophysics.sw_dual_water_foundation` ашық салыстырмалы жуықтау болып қалады. Ол толық Clavier–Coates–Dumanoir моделі емес және соңғы есеп үшін бұғатталған.

## Evidence

Нәтиже `artifacts/validation/petrophysical_validation_v225_9.json` файлына сақталады.
