# Presentation Print Layout v28

This increment makes the presentation HTML renderer print-ready.

The renderer still uses the existing `PresentationModel` and does not rebuild interpretation logic. It adds controlled print layout options for paper size, orientation and page margins. The default engineering report remains engineer-first: summary, interval cards, recommendations, limitations and plot before technical appendices.

## Rules

- Keep report sections together when possible.
- Start the professional well-log plot on a new printed page.
- Hide Plotly modebar in print output.
- Sanitize page options before injecting them into CSS.
- Keep expert diagnostics out of the engineering profile unless explicitly requested.
