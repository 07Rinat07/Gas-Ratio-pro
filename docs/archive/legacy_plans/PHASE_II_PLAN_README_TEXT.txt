GAS RATIO PRO — PHASE II PLAN
Engineering Specification & Architecture
Version: 2.0 Draft

1. ОБЩЕЕ РЕШЕНИЕ

Проект переходит в Phase II — Engineering Specification & Architecture.
На этом этапе мы временно не добавляем крупные новые функциональные модули в код.
Сначала фиксируем профессиональную архитектуру, требования, Roadmap v3.0 и спецификации ключевых подсистем.

Главное правило:
Идея → Анализ → Спецификация → Roadmap → Архитектура → Код → Тесты → Документация.

2. ПОЧЕМУ ЭТО НУЖНО

Текущая версия проекта уже содержит много подсистем:
- Dashboard / Workspace;
- Project Manager;
- Well Manager;
- LAS Explorer;
- LAS Editor foundation;
- Plot Studio;
- Statistics Center;
- Formula Builder;
- Interpretation Workspace;
- Report Studio;
- Correlation Studio;
- Geological Modeling foundation;
- Data Exchange Center;
- Plugin SDK;
- Scripting API foundation;
- Performance & Optimization;
- Release Candidate diagnostics.

Но проект еще рано считать финальным, потому что выявлены важные пробелы:
- LAS Editor пока не умеет полноценно создавать LAS-файл с нуля;
- LAS Platform требует отдельного профессионального расширения;
- нужны Curve Manager, Header Editor, ASCII Editor, LAS Validator и Safe LAS Writer;
- Property Modeling, Facies Modeling, Contacts, Geometry и Reservoir Calculator нужно включить в официальный Roadmap;
- Licensing / Hardware ID / Activation сейчас преждевременны;
- AI Assistant пока не нужен и не входит в текущую версию проекта.

3. ГЛАВНЫЕ ДОКУМЕНТЫ PHASE II

В проект добавляется новый комплект документации:

1) PROJECT_DESIGN_PRINCIPLES.md
Документ с принципами проекта: Documentation First, Specification First, модульность, безопасное редактирование LAS, отказ от преждевременного лицензирования и AI.

2) MASTER_PROJECT_SPECIFICATION_v2.0.md
Главная спецификация проекта. Это основной источник истины для архитектуры, требований и дальнейшего развития.

3) ROADMAP_v3.0.md
Новая дорожная карта вместо старой длинной линейной нумерации этапов.
План теперь делится на блоки: Core, LAS Platform, Well Management, Interpretation, Geological Modeling, Visualization, Data Exchange, Reports, Workflow, Plugin SDK, Performance.

4) SRS_DRAFT.md
Черновик Software Requirements Specification: функциональные и нефункциональные требования.

5) SAD_DRAFT.md
Черновик Software Architecture Document: слои архитектуры, зависимости, правила взаимодействия модулей.

6) LAS_PLATFORM_SPECIFICATION_DRAFT.md
Отдельная спецификация LAS Platform. Это самый приоритетный документ после Master Specification, потому что LAS — ядро проекта.

7) CALCULATION_ENGINE_SPECIFICATION_DRAFT.md
Спецификация вычислительного ядра: формулы, кривые, свойства, статистика, резервуарные расчеты.

8) GEOLOGICAL_MODELING_SPECIFICATION_DRAFT.md
Спецификация геологического моделирования: фации, свойства, контакты, геометрия, вариограммы, расчеты запасов.

9) UI_UX_GUIDELINES_DRAFT.md
Правила интерфейса: Sidebar как основная навигация, Dashboard как рабочее пространство инженера, отсутствие дублирования навигации.

10) DATABASE_SPECIFICATION_DRAFT.md
Правила хранения данных проекта, JSON-схемы, миграции, совместимость.

11) TESTING_SPECIFICATION_DRAFT.md
Стратегия тестирования: unit, integration, regression, preflight.

4. НОВЫЙ ROADMAP v3.0

A. Platform Core
- Core Architecture Review.
- Project Context.
- Command System.
- Diagnostics.

B. LAS Platform Professional
- LAS Creation Wizard.
- LAS Template System.
- Header Editor.
- Curve Manager Professional.
- ASCII Editor.
- Safe LAS Writer.
- LAS Validator.
- Curve import from CSV/XLSX.
- Curve Calculator.
- LAS Quality Control.

C. Well Management
- Well Card Professional.
- Trajectory Support.
- Intervals and Perforations.

D. Interpretation Platform
- Formation Manager Professional.
- Pick Manager.
- Correlation Studio Professional II.
- Crossplot Studio.

E. Geological Modeling Professional
- Structural Framework.
- Facies Modeling.
- Property Manager.
- Property Calculator.
- Petrophysical Modeling.
- Fluid Contact Modeling.
- Geometrical Modeling.
- Reservoir Calculator.
- Function Studio.
- Variogram Studio.

F. Data Quality & Validation
- Data Quality Professional.
- Repair Recommendations.

G. Visualization Professional
- Plot Studio Professional II.
- Grid and Property Preview.
- Map and Section Studio.

H. Data Exchange Professional
- LAS Export Professional.
- Tabular Exchange.
- Geological Exchange.
- Project Exchange.

I. Reports and Documentation
- Report Studio Professional II.
- Documentation Center.

J. Workflow and Automation
- Workflow Engine Professional.
- Batch Processing Professional.
- Scripting API Professional.

K. Extensibility
- Plugin SDK Professional.
- Developer Documentation.

L. Performance and Stabilization
- Performance Final.
- Regression Testing.
- Release Candidate 2.

M. Optional / Deferred
- Licensing and Activation: отложено, опционально.
- AI Assistant: не входит в текущий Roadmap.
- Cloud and Collaboration: отложено.

5. ПЕРВЫЙ ПРИОРИТЕТ ПОСЛЕ ДОКУМЕНТАЦИИ

После утверждения документов первым кодовым направлением должен стать:

B. LAS Platform Professional

Почему:
- LAS — основа проекта;
- сейчас редактор LAS не умеет полноценно создавать LAS с нуля;
- без сильного LAS Platform нельзя стабильно развивать петрофизику, моделирование, отчеты и импорт/экспорт.

Первые задачи:
1. LAS Creation Wizard.
2. LAS Template System.
3. Header Editor.
4. Curve Manager Professional.
5. ASCII Editor.
6. LAS Validator.
7. Safe LAS Writer.
8. Import curves from CSV/XLSX.
9. Curve Calculator.
10. LAS Quality Control.

6. ЧТО НЕ ДЕЛАЕМ СЕЙЧАС

Не делаем сейчас:
- финальный архив;
- финальный релиз;
- Hardware ID;
- License Manager;
- offline activation;
- AI Assistant;
- cloud collaboration;
- enterprise user roles;
- телеметрию.

Эти функции не должны мешать развитию инженерного ядра.

7. КРИТЕРИЙ ЗАВЕРШЕНИЯ PHASE II

Phase II можно считать выполненной, когда:
- созданы и утверждены основные документы;
- Roadmap v3.0 заменил старую линейную схему этапов;
- LAS Platform Professional подробно описан;
- Geological Modeling Professional описан как набор будущих модулей;
- AI Assistant и Licensing явно помечены как отложенные;
- дальнейшая разработка идет только по утвержденной спецификации.

8. ИТОГ

GAS RATIO PRO переходит от разработки отдельными этапами к профессиональной инженерной разработке по спецификациям.
Это уменьшит технический долг, устранит хаотичное добавление функций и позволит сделать проект полноценной инженерной платформой.
