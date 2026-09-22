import { useEffect, useMemo, useRef, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { loadCycleQuantData } from "./data";
import "./cyclequant.css";

const PROJECT_SOURCE = "https://github.com/Manateek1/Capital-in-Code/tree/main/projects/cic-002-cyclequant";
const PROJECT_REPORT = "https://github.com/Manateek1/Capital-in-Code/blob/main/projects/cic-002-cyclequant/PROJECT_REPORT.md";
const SIGNAL_LABELS = {
  valuation: "Valuation / cycle",
  trend: "Trend / momentum",
  drawdown: "Drawdown / structure",
  onchain: "On-chain / derivatives",
  macro: "Macro / flows",
  news: "News",
};
const HYSTERESIS_LEVELS = {
  0: { up: 35 },
  25: { down: 25, up: 50 },
  50: { down: 40, up: 65 },
  75: { down: 55, up: 80 },
  100: { down: 70 },
};

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const compactMoney = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const percent = (value, digits = 2, showPlus = true) => `${showPlus && value > 0 ? "+" : ""}${(value * 100).toFixed(digits)}%`;
const formatDate = (value, options = {}) => new Intl.DateTimeFormat("en-US", { timeZone: "UTC", month: "short", day: "numeric", year: "numeric", ...options }).format(new Date(value));

function Icon({ name }) {
  if (name === "close") return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5l14 14M19 5L5 19" /></svg>;
  if (name === "copy") return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" /></svg>;
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>;
}

function StatusDot({ state = "fresh" }) {
  return <span className={`cq-status-dot cq-status-${state}`} aria-hidden="true" />;
}

function ProvenanceTag({ children, tone = "data" }) {
  return <span className={`cq-tag cq-tag-${tone}`}>{children}</span>;
}

function EmptyState() {
  return <div className="cq-empty"><strong>No evaluation has been published yet.</strong><span>The dashboard will populate after the first scheduled paper-research run.</span></div>;
}

function LoadingState() {
  return <div className="cq-loading" role="status"><span /><p>Loading the audit journal…</p></div>;
}

function DashboardHeader() {
  return <header className="site-header cq-header">
    <Link className="wordmark" to="/">Capital in Code <img className="mark" src="/brand-mark.png" alt="" aria-hidden="true" /></Link>
    <nav aria-label="Primary navigation">
      <NavLink to="/projects/cic-001-overnight-effect">CIC-001</NavLink>
      <NavLink to="/projects/cic-002-cyclequant">CycleQuant</NavLink>
      <NavLink to="/methods">Methods</NavLink>
      <NavLink to="/about">About</NavLink>
    </nav>
    <a className="github-link" href="https://github.com/Manateek1/Capital-in-Code" target="_blank" rel="noreferrer">GitHub <span aria-hidden="true">↗</span></a>
  </header>;
}

function AccountStatusStrip({ account, decision }) {
  const connected = Boolean(account?.connected && account?.broker_mode === "alpaca-paper");
  const reconciled = Boolean(account?.position_reconciled);
  const coverage = Math.round((decision?.signals?.coverage ?? 0) * 100);
  const updatedAt = account?.captured_at ?? decision?.timestamp;
  const fresh = Boolean(updatedAt && Date.now() - new Date(updatedAt).getTime() <= 2 * 60 * 60 * 1000);
  const systemStatus = !fresh
    ? "Last sync overdue"
    : connected
    ? account.trading_enabled && reconciled
      ? "Paper execution enabled"
      : reconciled
        ? "Execution locked"
        : "Position review required"
    : "Credentials required";
  const items = [
    {
      label: connected && fresh ? "ALPACA PAPER · CONNECTED" : connected ? "ALPACA PAPER · STALE" : "ALPACA PAPER · CONNECTION PENDING",
      detail: connected ? "Private API · public mirror" : "Paper connection unavailable",
      state: connected && fresh ? "fresh" : "warning",
    },
    { label: "PAPER ONLY", detail: "Real-money endpoints blocked", state: "fresh" },
    { label: "Data last updated", detail: updatedAt ? `${formatDate(updatedAt, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false })} UTC` : "Awaiting first sync", state: fresh ? "fresh" : "warning" },
    { label: "Signal coverage", detail: `${coverage}% of configured inputs`, state: coverage >= 80 ? "fresh" : "warning" },
    { label: "System status", detail: systemStatus, state: connected && fresh && account.trading_enabled && reconciled ? "fresh" : "warning" },
  ];
  return <section className="cq-account-strip" aria-label="Paper account status">
    {items.map((item) => <div key={item.label}><StatusDot state={item.state} /><span><b>{item.label}</b><small>{item.detail}</small></span></div>)}
  </section>;
}

function SummaryRail({ summary }) {
  const items = [
    ["Managed equity", money.format(summary.portfolio_value), "isolated paper sleeve"],
    ["Return", percent(summary.total_return), "since inception"],
    ["Managed cash", money.format(summary.managed_cash ?? 0), `${Math.round(((summary.managed_cash ?? 0) / summary.portfolio_value) * 100)}% of sleeve`],
    ["BTC exposure", `${Number(summary.current_exposure).toFixed(1)}%`, "actual paper position"],
    ["BTC / USD", compactMoney.format(summary.btc_price), "latest paper mark"],
    ["Latest action", summary.latest_action, "allocation decision"],
  ];
  return <section className="cq-summary-rail" aria-label="Portfolio summary">
    {items.map(([label, value, detail]) => <div className="cq-summary-item" key={label}>
      <span>{label}</span><strong className={label === "Return" ? "cq-positive" : label === "Latest action" ? "cq-action" : ""}>{value}</strong><small>{detail}</small>
    </div>)}
  </section>;
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return <div className="cq-chart-tooltip"><span>{formatDate(label)}</span>{payload.map((entry) => <div key={entry.dataKey}><i style={{ background: entry.color }} />{entry.name}<b>{money.format(entry.value)}</b></div>)}</div>;
}

function PerformancePanel({ data, metrics }) {
  const [range, setRange] = useState("3M");
  const visible = useMemo(() => {
    const days = range === "1M" ? 30 : range === "3M" ? 90 : data.length;
    return data.slice(-days);
  }, [data, range]);
  const cqMetrics = metrics.cyclequant ?? {};
  return <section className="cq-panel cq-performance" aria-labelledby="performance-title">
    <div className="cq-panel-header">
      <div><p className="cq-eyebrow">BENCHMARKING</p><h2 id="performance-title">Performance since inception</h2><p className="cq-panel-subtitle">{data.length < 30 ? "Early sample; " : "Daily history; "}latest point reflects the paper account mark.</p></div>
      <div className="cq-range" aria-label="Chart date range">{["1M", "3M", "All"].map((item) => <button type="button" className={range === item ? "active" : ""} onClick={() => setRange(item)} key={item}>{item}</button>)}</div>
    </div>
    <div className="cq-chart" aria-label="Portfolio performance chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={visible} margin={{ top: 12, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#dde2e8" vertical={false} />
          <XAxis dataKey="date" stroke="#5f6873" tickLine={false} axisLine={false} minTickGap={44} tickFormatter={(value) => formatDate(value, { year: undefined })} />
          <YAxis stroke="#5f6873" tickLine={false} axisLine={false} width={54} domain={["auto", "auto"]} tickFormatter={(value) => `$${Math.round(value)}`} />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: "#7d8ba0", strokeDasharray: "4 4" }} />
          <Legend verticalAlign="top" align="left" iconType="plainline" wrapperStyle={{ paddingBottom: 14 }} />
          <Line name="CycleQuant" type="monotone" dataKey="cyclequant" stroke="#123675" dot={false} strokeWidth={2.4} activeDot={{ r: 4 }} />
          <Line name="BTC buy & hold" type="monotone" dataKey="btc_buy_hold" stroke="#c77d1e" dot={false} strokeWidth={1.8} />
          <Line name="Cash" type="monotone" dataKey="cash" stroke="#6a7079" dot={false} strokeWidth={1.4} strokeDasharray="5 5" />
        </LineChart>
      </ResponsiveContainer>
    </div>
    <div className="cq-exposure-chart" aria-label="BTC exposure history">
      <span>BTC exposure</span>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={visible} margin={{ top: 3, right: 8, bottom: 3, left: 0 }}>
          <YAxis hide domain={[0, 100]} />
          <Area type="stepAfter" dataKey="exposure" stroke="#123675" fill="#123675" fillOpacity={0.09} strokeWidth={1.5} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
    <div className="cq-metric-strip">
      <span><small>Total return</small><b>{percent(cqMetrics.total_return ?? 0)}</b></span>
      <span><small>Annualized</small><b>{cqMetrics.annualized_return == null ? "—" : percent(cqMetrics.annualized_return)}</b></span>
      <span><small>Max drawdown</small><b>{percent(cqMetrics.max_drawdown ?? 0, 2, false)}</b></span>
      <span><small>Volatility</small><b>{cqMetrics.annualized_volatility == null ? "—" : percent(cqMetrics.annualized_volatility, 2, false)}</b></span>
      <span><small>Approx. Sharpe</small><b>{cqMetrics.approximate_sharpe == null ? "—" : cqMetrics.approximate_sharpe.toFixed(2)}</b></span>
      <span><small>Trades</small><b>{metrics.trade_count}</b></span>
    </div>
  </section>;
}

function SignalPanel({ decision }) {
  const components = decision?.signals?.components ?? {};
  return <section className="cq-panel cq-signals" aria-labelledby="signals-title">
    <div className="cq-thesis-head"><div><p className="cq-eyebrow">TODAY'S THESIS</p><h2>{decision?.action ?? "HOLD"} — maintain {decision?.target_exposure ?? 0}% BTC exposure</h2></div><p>{decision?.reasoning}</p></div>
    <div className="cq-signal-heading"><h3 id="signals-title">Signal score decomposition</h3><strong className="cq-score">{Math.round(decision?.signals?.total_score ?? 0)}<small>/100</small></strong></div>
    <div className="cq-signal-list">{Object.entries(SIGNAL_LABELS).map(([key, label]) => {
      const score = components[key]?.score ?? 0;
      return <div className="cq-signal" key={key}><div><span>{label}</span><b>{Math.round(score)}</b></div><div className="cq-signal-track"><i style={{ width: `${score}%` }} /></div></div>;
    })}</div>
    <div className="cq-confidence"><span><StatusDot />{decision?.signals?.confidence ?? "—"} confidence</span><span>{Math.round((decision?.signals?.coverage ?? 0) * 100)}% source coverage</span></div>
  </section>;
}

function ActionBadge({ action, status }) {
  return <span className={`cq-action-badge cq-action-${action.toLowerCase()}`}>{action}{status && <small>{status}</small>}</span>;
}

function CurrentPosition({ account, summary }) {
  const exposure = Number(account?.actual_btc_exposure ?? summary.current_exposure ?? 0);
  const positionValue = Number(account?.managed_btc_value ?? summary.portfolio_value * exposure / 100);
  const positionQuantity = Number(account?.managed_btc_quantity ?? positionValue / summary.btc_price);
  const managedCash = Number(account?.strategy_cash ?? summary.managed_cash ?? 0);
  const feeValue = Number(account?.btc_fee_quantity ?? 0) * Number(account?.btc_price ?? 0) + Number(account?.usd_fees_paid ?? 0);
  const reconciled = Boolean(account?.position_reconciled);
  return <section className="cq-panel cq-mirror-panel" aria-labelledby="position-title">
    <div className="cq-compact-header"><h2 id="position-title">Current position</h2><span>{account?.captured_at ? `As of ${formatDate(account.captured_at, { hour: "2-digit", minute: "2-digit", hour12: false })} UTC` : "Awaiting broker sync"}</span></div>
    <div className="cq-position-primary"><div><span>BTC position</span><strong>{positionQuantity.toFixed(9)} BTC</strong><small>{money.format(positionValue)} managed value</small></div><div><span>Cash</span><strong>{money.format(managedCash)}</strong><small>{Math.round((managedCash / summary.portfolio_value) * 100)}% of sleeve</small></div></div>
    <dl className="cq-position-facts"><div><dt>Actual portfolio share</dt><dd>{exposure.toFixed(1)}%</dd></div><div><dt>Broker check</dt><dd className={reconciled ? "cq-positive" : "cq-caution"}>{reconciled ? "Reconciled" : "Review required"}</dd></div><div><dt>Environment</dt><dd>Paper only</dd></div></dl>
    {feeValue > 0 && <p className="cq-fee-note">Managed value includes {money.format(feeValue)} in Alpaca paper crypto fees.</p>}
  </section>;
}

function RecentPaperOrders({ trades, onOpen }) {
  const recent = trades.slice(0, 5);
  return <section className="cq-panel cq-mirror-panel cq-orders" aria-labelledby="trades-title">
    <div className="cq-compact-header"><h2 id="trades-title">Recent paper orders</h2><span>{trades.length} allocation changes</span></div>
    {recent.length ? <><p className="cq-mobile-scroll-hint">Swipe across to view order details →</p><div className="cq-orders-wrap" tabIndex="0" aria-label="Recent paper orders; scroll horizontally for more columns"><table><thead><tr><th>Date</th><th>Side</th><th>Quantity</th><th>Fill</th><th>Status</th><th aria-label="Open record" /></tr></thead><tbody>{recent.map((trade) => <tr key={trade.id}><td>{formatDate(trade.decision_date, { year: undefined })}</td><td><ActionBadge action={trade.action} /></td><td>{Number(trade.trade_quantity || 0).toFixed(9)}</td><td>{trade.fill_price ? compactMoney.format(Number(trade.fill_price)) : "—"}</td><td><span className="cq-status-text"><StatusDot state={trade.order_status === "FILLED" ? "fresh" : "warning"} />{trade.order_status}</span></td><td><button type="button" className="cq-row-open" aria-label={`Open decision from ${trade.decision_date}`} onClick={() => onOpen(trade)}><Icon /></button></td></tr>)}</tbody></table></div></> : <div className="cq-orders-empty"><b>No paper orders yet.</b><span>Daily evaluations are running; an order appears only after every allocation rule clears.</span></div>}
  </section>;
}

function researchNotes(decisions) {
  const latest = decisions[0];
  const previous = decisions[1];
  if (!latest) return [];
  const components = Object.entries(latest.signals.components).sort(([, left], [, right]) => right.score - left.score);
  const [strongestName, strongest] = components[0];
  const [weakestName, weakest] = components.at(-1);
  const scoreDelta = previous ? latest.signals.total_score - previous.signals.total_score : 0;
  const exposureChanged = previous && latest.target_exposure !== previous.target_exposure;
  const changed = previous
    ? `Composite ${scoreDelta >= 0 ? "rose" : "fell"} ${Math.abs(scoreDelta).toFixed(1)} points; target exposure ${exposureChanged ? `moved from ${previous.target_exposure}% to ${latest.target_exposure}%` : `held at ${latest.target_exposure}%`}.`
    : `The first published evaluation set a ${latest.target_exposure}% BTC target at ${latest.signals.total_score.toFixed(1)}/100.`;
  const matters = `${SIGNAL_LABELS[strongestName] ?? strongestName} leads at ${Math.round(strongest.score)}/100 while ${SIGNAL_LABELS[weakestName] ?? weakestName} is the main counterweight at ${Math.round(weakest.score)}/100.`;
  const levels = HYSTERESIS_LEVELS[latest.target_exposure] ?? {};
  const thresholds = [levels.down != null ? `≤${levels.down}` : null, levels.up != null ? `≥${levels.up}` : null].filter(Boolean).join(" or ");
  const wouldChange = `A confirmed composite move ${thresholds || "outside the current band"}, fresh required data, and independent signal agreement would permit the next 25-point allocation step.`;
  return [
    ["What changed", changed],
    ["Why it matters", matters],
    ["What would change the decision", wouldChange],
  ];
}

function ResearchNotes({ decisions }) {
  return <section className="cq-panel cq-mirror-panel cq-notes" aria-labelledby="notes-title">
    <div className="cq-compact-header"><h2 id="notes-title">Research notes</h2><span>{decisions[0] ? formatDate(decisions[0].decision_date) : "—"}</span></div>
    <div className="cq-note-list">{researchNotes(decisions).map(([title, body], index) => <article key={title}><span>0{index + 1}</span><div><b>{title}</b><p>{body}</p></div></article>)}</div>
  </section>;
}

function RiskGuardrails() {
  const rules = [
    ["PAPER ONLY", "Live-money host rejected"],
    ["Long-only", "No short positions"],
    ["No leverage", "Cash-backed orders"],
    ["$1,000 sleeve", "Broker balance cannot scale size"],
    ["One daily step", "Maximum 25 percentage points"],
  ];
  return <section className="cq-guardrails" aria-label="Risk guardrails"><h2>Risk guardrails</h2>{rules.map(([title, detail]) => <div key={title}><StatusDot /><span><b>{title}</b><small>{detail}</small></span></div>)}</section>;
}

function DecisionJournal({ decisions, onOpen }) {
  const [visibleCount, setVisibleCount] = useState(12);
  const visible = decisions.slice(0, visibleCount);
  return <section className="cq-panel cq-table-panel" id="journal" aria-labelledby="journal-title">
    <div className="cq-panel-header"><div><p className="cq-eyebrow">IMMUTABLE AUDIT LOG</p><h2 id="journal-title">Decision journal</h2></div><span className="cq-row-count">{decisions.length} daily evaluations</span></div>
    <p className="cq-mobile-scroll-hint">Swipe across to read the decision basis →</p><div className="cq-table-wrap" tabIndex="0" aria-label="Decision journal; scroll horizontally for more columns"><table><thead><tr><th>Date</th><th>Score</th><th>Confidence</th><th>Allocation</th><th>Action</th><th>Decision basis</th><th aria-label="Open record" /></tr></thead><tbody>{visible.map((decision) => <tr key={decision.id}><td>{formatDate(decision.decision_date)}</td><td><b>{Math.round(decision.signals.total_score)}</b><span className="cq-mini-track"><i style={{ width: `${decision.signals.total_score}%` }} /></span></td><td>{decision.signals.confidence}</td><td>{decision.target_exposure}% BTC</td><td><ActionBadge action={decision.action} /></td><td className="cq-reason-cell">{decision.allocation_recommendation?.reason ?? decision.reasoning}</td><td><button type="button" className="cq-row-open" aria-label={`Open decision from ${decision.decision_date}`} onClick={() => onOpen(decision)}><Icon /></button></td></tr>)}</tbody></table></div>
    {visibleCount < decisions.length && <button className="cq-load-more" type="button" onClick={() => setVisibleCount((count) => Math.min(count + 25, decisions.length))}>Load older decisions</button>}
  </section>;
}

function Methodology() {
  return <section className="cq-method" id="methodology" aria-labelledby="method-title"><div><p className="cq-eyebrow">RESEARCH METHOD</p><h2 id="method-title">Rules first. Narrative second.</h2><p>Six independent categories produce a normalized score. Hysteresis, confirmation, breadth, and a one-tier step limit turn that score into one of five permitted allocations.</p></div><ol><li><span>01</span><b>Measure</b><small>Fresh market, cycle, macro, flow, and news inputs.</small></li><li><span>02</span><b>Score</b><small>Deterministic components with versioned weights.</small></li><li><span>03</span><b>Constrain</b><small>Independent paper-only risk and idempotency checks.</small></li><li><span>04</span><b>Record</b><small>Immutable snapshot, rationale, execution, and benchmarks.</small></li></ol></section>;
}

function DecisionDrawer({ decision, onClose }) {
  const [copied, setCopied] = useState(false);
  const closeButton = useRef(null);
  useEffect(() => {
    closeButton.current?.focus();
    const closeOnEscape = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  if (!decision) return null;
  const copy = async () => {
    await navigator.clipboard.writeText(JSON.stringify(decision, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };
  return <div className="cq-drawer-layer"><button type="button" className="cq-drawer-backdrop" aria-label="Close decision record" onClick={onClose} /><aside className="cq-drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title"><header><div><p className="cq-eyebrow">AUDIT RECORD</p><h2 id="drawer-title">Decision — {formatDate(decision.decision_date)}</h2></div><button ref={closeButton} type="button" className="cq-icon-button" onClick={onClose} aria-label="Close decision"><Icon name="close" /></button></header><div className="cq-drawer-body">
    <section><h3>Snapshot</h3><dl><div><dt>BTC price</dt><dd>{compactMoney.format(Number(decision.btc_price))}</dd></div><div><dt>Portfolio</dt><dd>{money.format(Number(decision.portfolio_value))}</dd></div><div><dt>Exposure</dt><dd>{decision.current_exposure}% → {decision.target_exposure}%</dd></div><div><dt>Composite</dt><dd>{decision.signals.total_score.toFixed(1)} / 100</dd></div></dl></section>
    <section><h3>Signal snapshot</h3><div className="cq-drawer-signals">{Object.entries(decision.signals.components).map(([name, item]) => <div key={name}><span>{SIGNAL_LABELS[name] ?? name}</span><b>{Math.round(item.score)}</b><small>{item.rationale}</small></div>)}</div></section>
    <section><h3>Important news considered</h3>{decision.important_news.length ? <ul className="cq-news-list">{decision.important_news.map((item) => <li key={item.id}><span>{item.source}</span>{item.title}</li>)}</ul> : <p>No recent headline passed the relevance threshold.</p>}</section>
    <section><h3>News summary</h3><ProvenanceTag tone="ai">BOUNDED NEWS INPUT</ProvenanceTag><p>{decision.ai_news_summary}</p></section>
    <section><h3>Decision rationale</h3><p>{decision.reasoning}</p><p className="cq-rule-note">{decision.allocation_recommendation?.reason}</p></section>
    <section><h3>Execution</h3><dl><div><dt>Action</dt><dd><ActionBadge action={decision.action} /></dd></div><div><dt>Paper value</dt><dd>{money.format(Number(decision.trade_value))}</dd></div><div><dt>Status</dt><dd>{decision.order_status}</dd></div><div><dt>Fill price</dt><dd>{decision.fill_price ? compactMoney.format(Number(decision.fill_price)) : "—"}</dd></div></dl></section>
    <section className="cq-integrity"><StatusDot /><div><b>Immutable journal record</b><span>{decision.timestamp} · strategy {decision.strategy_version}</span></div></section>
  </div><footer><button type="button" className="cq-copy" onClick={copy}><Icon name="copy" />{copied ? "Copied" : "Copy record"}</button><a href={PROJECT_SOURCE} target="_blank" rel="noreferrer">Inspect source ↗</a></footer></aside></div>;
}

export default function CycleQuantDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [refreshError, setRefreshError] = useState("");
  const [selected, setSelected] = useState(null);
  const dataRef = useRef(null);
  useEffect(() => {
    let controller;
    const refresh = () => {
      controller?.abort();
      controller = new AbortController();
      loadCycleQuantData(controller.signal).then((next) => {
        dataRef.current = next;
        setData(next);
        setError("");
        setRefreshError("");
      }).catch((failure) => {
        if (failure.name === "AbortError") return;
        if (dataRef.current) setRefreshError("The latest paper account update could not be loaded. Showing the last verified snapshot.");
        else setError("The paper account could not be loaded. Please try again shortly.");
      });
    };
    refresh();
    const timer = window.setInterval(refresh, 5 * 60 * 1000);
    const onFocus = () => refresh();
    const onVisible = () => { if (document.visibilityState === "visible") refresh(); };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      controller?.abort();
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);
  if (error) return <div className="cq-app"><DashboardHeader /><div className="cq-fatal"><b>Dashboard data is unavailable.</b><span>{error}</span><Link to="/">Return to Capital in Code</Link></div></div>;
  if (!data) return <div className="cq-app"><DashboardHeader /><LoadingState /></div>;
  return <div className="cq-app">
    <DashboardHeader />
    <main className="cq-main" id="overview">
      <div className="cq-intro"><div><p className="cq-eyebrow">CIC-002 · CYCLEQUANT</p><h1>A Bitcoin paper account, open to inspection.</h1><p className="cq-intro-summary">Daily decisions, paper trades, and results from a rules-based portfolio.</p></div><div><p>CycleQuant checks market conditions once a day and decides how much of a small test portfolio to hold in Bitcoin. Alpaca carries out the paper trades. The account snapshot below is checked against the recorded fills.</p><a className="cq-text-link" href={PROJECT_REPORT} target="_blank" rel="noreferrer">Read the project report <span aria-hidden="true">→</span></a><small>{data.disclaimer}</small></div></div>
      <div className="cq-page-nav"><a href="#overview">Overview</a><a href="#journal">Decision journal</a><a href="#methodology">Method</a><span>Last evaluated {data.summary.last_evaluated_at ? `${formatDate(data.summary.last_evaluated_at, { hour: "2-digit", minute: "2-digit", hour12: false })} UTC` : "—"}{data._source === "demo" ? " · DEMO DATA" : ""}</span></div>
      {refreshError && <p className="cq-refresh-warning" role="status">{refreshError}</p>}
      {data.latest_decision ? <><AccountStatusStrip account={data.paper_account} decision={data.latest_decision} /><SummaryRail summary={data.summary} /><div className="cq-grid"><PerformancePanel data={data.performance} metrics={data.metrics} /><SignalPanel decision={data.latest_decision} /></div><div className="cq-mirror-grid"><CurrentPosition account={data.paper_account} summary={data.summary} /><RecentPaperOrders trades={data.trade_history} onOpen={setSelected} /><ResearchNotes decisions={data.decision_journal} /></div><RiskGuardrails /><DecisionJournal decisions={data.decision_journal} onOpen={setSelected} /><Methodology /></> : <EmptyState />}
    </main>
    <footer className="cq-footer"><Link className="wordmark" to="/">Capital in Code <img className="mark" src="/brand-mark.png" alt="" aria-hidden="true" /></Link><div className="footer-copy"><p>Independent research in quantitative finance, investing, coding, and statistics.</p><p className="disclaimer">Paper trading only. Educational research, not investment advice.</p></div><a href={PROJECT_SOURCE} target="_blank" rel="noreferrer">View source code <span aria-hidden="true">↗</span></a></footer>
    {selected && <DecisionDrawer decision={selected} onClose={() => setSelected(null)} />}
  </div>;
}
