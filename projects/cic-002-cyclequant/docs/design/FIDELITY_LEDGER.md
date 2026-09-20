# Dashboard fidelity ledger

Visual acceptance was performed against the generated desktop overview, mobile
overview, and decision-drawer concepts in `docs/design/concepts/`.

## Matched

- Deep ink background, flat graphite panels, cool-blue hairlines, and restrained
  teal/blue/amber semantics.
- Quiet product header with Overview, Journal, Methodology, `PAPER ONLY`, and
  last-evaluated state.
- Continuous summary rail, large performance chart, right-hand signal panel,
  provenance tags, thesis band, allocation table, and decision journal.
- Six horizontal signal bars, high-confidence state, normalized benchmark
  colors, range controls, chart tooltip, and exposure history.
- Fixed desktop audit drawer and full-width mobile sheet with snapshot, signal
  inputs, news, reasoning, execution, integrity metadata, and copy control.
- Mobile summary rail, stacked analysis panels, 44px primary controls, menu,
  horizontal tables, reduced chart ticks, and no page-level overflow.
- Reduced-motion and visible keyboard-focus behavior.

## Deliberate differences

- A research-question introduction was added above the terminal surface so the
  dashboard works as a self-explanatory Capital in Code portfolio page.
- `DEMO DATA` is visibly shown until real RLS-protected cloud rows exist; the
  concept did not include this research-integrity state.
- The deterministic fixture uses trend `72` rather than the concept's `63` so
  the displayed weighted component scores reconcile to the composite near 74.
- The implementation adds annualized statistics and a compact exposure-history
  strip required by the project brief.
- Dense historical tables scroll horizontally on narrow screens rather than
  dropping audit fields.

## Verification

- Desktop rendering: accepted against `dashboard-desktop.png`.
- Narrow/mobile rendering: accepted against `dashboard-mobile.png`.
- Audit drawer: opened and visually checked at desktop and mobile sizes.
- Browser console: no errors in a fresh tab.
- Final browser capture: `docs/design/qa/dashboard-final.png`.
