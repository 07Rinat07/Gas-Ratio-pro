# GAS RATIO PRO — GEOLOGICAL MODELING WORKSPACE REDESIGN SPECIFICATION v4.0

## 1. Проблема

Backend геомоделирования уже содержит много foundation-модулей, но пользователь не видит, где и как ими пользоваться.

---

## 2. Geological Modeling Home

Главный экран должен показывать рабочие действия:

- Создать геологическую модель;
- Создать structural framework;
- Добавить горизонты;
- Добавить зоны;
- Добавить контакты;
- Построить фации;
- Построить кубы свойств;
- Рассчитать объемы;
- Проверить модель.

---

## 3. Workspaces

- Structural Modeling;
- Facies Modeling;
- Property Modeling;
- Geostatistics;
- Interpolation;
- Simulation;
- Fluid Contacts;
- Volumetrics;
- Model Validation.

---

## 4. UI элементы

- Model Explorer;
- Object Tree;
- Property Table;
- Parameter Panel;
- Preview Panel;
- Validation Panel;
- Report Panel.

---

## 5. Acceptance Criteria

Геомоделирование считается доступным пользователю только если можно открыть Geological Modeling Workspace и пошагово выполнить минимум:

1. Создать модель.
2. Добавить горизонты/зоны.
3. Создать property cube.
4. Добавить contact.
5. Рассчитать volumetrics.
6. Получить отчет.
