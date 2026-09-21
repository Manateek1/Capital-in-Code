# Dashboard fidelity ledger

Visual acceptance was performed against the original dashboard concepts and
the Alpaca-mirror concept in `docs/design/concepts/`.

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
- A factual Alpaca paper-account status strip, managed-sleeve cash and position,
  recent paper orders, deterministic research notes, and explicit guardrails.

## Deliberate differences

- A research-question introduction was added above the terminal surface so the
  dashboard works as a self-explanatory Capital in Code portfolio page.
- The connection state deliberately says `CONNECTION PENDING` until verified
  Alpaca paper credentials are installed. Simulation must never be presented as
  a live broker connection.
- The deterministic fixture uses trend `72` rather than the concept's `63` so
  the displayed weighted component scores reconcile to the composite near 74.
- The implementation adds annualized statistics and a compact exposure-history
  strip required by the project brief.
- Dense historical tables scroll horizontally on narrow screens rather than
  dropping audit fields.

## Verification

- Generated target: `concepts/dashboard-alpaca-mirror-desktop.png`.
- Desktop rendering: accepted at 1440px in
  `qa/dashboard-alpaca-mirror-desktop.png`.
- Narrow/mobile rendering: accepted at 390px in
  `qa/dashboard-alpaca-mirror-mobile.png`.
- Audit drawer: opened and visually checked at desktop and mobile sizes.
- Mobile drawer: `qa/dashboard-alpaca-mirror-mobile-drawer.png`.
- Browser console: no errors; automated accessibility scan reported zero
  violations; desktop and mobile had no page-level horizontal overflow.
