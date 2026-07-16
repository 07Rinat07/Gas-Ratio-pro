# DLIS and LIS79 adapter evaluation

## Decision

Use `dlisio` as an **optional, lazily imported adapter** for DLIS V1/RP66 V1 and LIS79. GAS RATIO PRO must start and provide format capability diagnostics when the dependency is absent.

## Rationale

- The upstream project is purpose-built for DLIS V1 and LIS79.
- It exposes metadata and curves while making limited assumptions about interpretation.
- Its documentation explicitly discusses real-world non-conforming files and TIF-wrapped inputs.
- The LGPL license requires preservation of notices and architectural isolation; the library is not vendored into the application.

## Scope

Initial adapter scope:

1. detect dependency availability;
2. list logical files;
3. count frames/channels for DLIS without materializing curve arrays;
4. expose stable warning codes when the optional adapter is unavailable;
5. preserve the immutable source artifact before any derived conversion.

Out of scope for the first increment:

- LIS84/Enhanced LIS;
- cross-regular-file LIS reels;
- editing source DLIS/LIS in place;
- loading all frame data during metadata scan.

## Security and performance

The adapter is imported only inside the scanner call. When unavailable, at most 4096 bytes are probed. No C-extension object is stored in session state, manifests, or domain models.
