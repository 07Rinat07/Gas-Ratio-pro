# Visualization adaptive prefetch budget v115

Viewport prefetch can now use an adaptive processing budget.

Configuration:

```json
{
  "viewport_prefetch": {
    "adaptive_budget": true,
    "max_process_limit": 2
  }
}
```

The scheduler reduces speculative work when the payload cache is full or when rapid navigation causes excessive task cancellation. Stable navigation with useful cache hits can use a larger budget. Explicit `process_limit` still takes precedence.

Metrics:

- `last_process_budget`
- `budget_adjustments`
