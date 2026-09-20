# CycleQuant dashboard design system

The generated desktop overview, audit drawer, and mobile concepts in
`docs/design/concepts/` are the visual specification for the dashboard.

## Direction

CycleQuant uses a restrained institutional research-terminal aesthetic. The
interface is data-first and calm: deep ink backgrounds, flat graphite surfaces,
hairline cool-blue borders, crisp typography, and a small semantic palette. It
must not resemble a retail crypto exchange, casino, or neon cyberpunk product.

## Locked visible copy

Desktop navigation: `Overview`, `Journal`, `Methodology`, `PAPER ONLY`, and
`Last evaluated … UTC`.

Primary sections, in order:

1. Portfolio summary rail
2. Performance since inception
3. Signal decomposition
4. Current thesis
5. Allocation changes
6. Decision journal

The selected decision opens an audit drawer headed `Decision — <date>` with
Snapshot, Signal snapshot, Important news considered, AI news summary,
Decision rationale, Execution, integrity timestamp, and Copy record.

No order-entry, deposit, live-trading, or performance-promising copy is allowed.

## Tokens

| Token | Value | Role |
| --- | --- | --- |
| Ink 950 | `#061321` | page background |
| Ink 900 | `#091827` | main surface |
| Ink 850 | `#0d1d2d` | raised/selected surface |
| Border | `#294157` | 1px dividers and outlines |
| Text | `#f2f6fb` | primary copy |
| Muted | `#9db0c6` | secondary copy and axes |
| Teal | `#35d6b2` | CycleQuant, positive, aligned |
| Blue | `#45a7ff` | BTC benchmark and interaction |
| Amber | `#f0bd4f` | caution and AI interpretation |
| Red | `#ff6b6b` | negative/drawdown only |

Surfaces use 8–10px radii, 1px borders, and shadows only where elevation is
functionally required (the audit drawer). No glass blur, ambient glow, or
decorative gradients.

## Typography

- UI/content: `Inter`, then system sans-serif fallbacks.
- Financial figures: tabular numerals; compact values may use the system
  monospace stack.
- Desktop body/control text: 13–16px. Headings: 18–22px. Summary values:
  27–31px.
- Mobile body/control text never intentionally drops below 14px, and primary
  touch controls target at least 44px.
- Labels use sentence case. Uppercase is reserved for `PAPER ONLY`, actions,
  and semantic provenance tags.

## Layout and component families

- `AppShell`: quiet top bar, 16px desktop outer gutter, 18–20px mobile gutter.
- `SummaryRail`: one continuous bordered rail divided by hairlines; mobile
  version scrolls horizontally without causing page overflow.
- `Panel`: purposeful analytical frame, never nested indiscriminately.
- `PerformanceChart`: CycleQuant teal, BTC blue, Cash muted gray, with subtle
  grid, native legend, range controls, tooltip, and optional drawdown strip.
- `SignalBars`: horizontal tracks with a numeric endpoint; no radial gauges.
- `ThesisBand`: open two-column desktop band, single-column mobile flow.
- `DataTable`: compact rows with selected, hover, and keyboard focus states.
- `DecisionDrawer`: fixed desktop right rail and full-screen mobile sheet with
  explicit close/copy actions and grouped audit facts.
- `ProvenanceTag`: small outlined label used only for `DATA`, `SIGNAL`, and
  `AI INTERPRETATION`.

## Icons

Icons are 1.5px outline SVGs with round joins/caps, generally 16–20px. Required
metaphors are menu, close, chevron, copy, external/open, and small status bars.
They inherit `currentColor`; no decorative icon rows are allowed.

## Responsive behavior

- At ≤900px the chart and signal panel stack, the thesis becomes vertical, and
  lower tables become touch-friendly lists.
- At ≤600px desktop navigation collapses to a menu, the summary rail scrolls,
  nonessential chart ticks reduce, and the audit drawer becomes a full-screen
  sheet.
- The page itself never overflows horizontally. Focus rings are clearly visible
  and reduced-motion preferences disable nonessential transitions.

## Motion

Use 140–180ms opacity/border/translate transitions for selection, drawer entry,
and chart tooltip changes. Motion communicates state only; it is disabled under
`prefers-reduced-motion`.
