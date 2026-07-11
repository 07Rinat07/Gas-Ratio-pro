# Visualization Viewport Prefetch Queue v113

Добавлена отменяемая FIFO-очередь speculative prefetch для соседних viewport.

Основные свойства:

- новая навигация создаёт новое поколение задач;
- незавершённые задачи предыдущего поколения отменяются;
- очередь ограничивается `max_pending`;
- `process_limit` ограничивает число задач, выполняемых за один pipeline run;
- метрики очереди доступны в `viewport_pipeline.prefetch_queue`;
- вычисления остаются renderer-neutral и не переносятся в UI.
