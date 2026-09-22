const STATIC_DEMO_URL = "/data/cyclequant-dashboard.json";
// Supabase publishable keys are designed for browser bundles. RLS remains the
// authorization boundary; the private CycleQuant writer token is never sent.
const DEFAULT_SUPABASE_URL = "https://gkaslphhalivcxpweuqm.supabase.co";
const DEFAULT_SUPABASE_PUBLISHABLE_KEY = "sb_publishable_EMazjbjj8zmQjD9MX1r5_g_mm8XsKxz";

function dailyReturns(values) {
  return values.slice(1).map((value, index) => value / values[index] - 1);
}

function maxDrawdown(values) {
  let peak = values[0] ?? 0;
  let worst = 0;
  values.forEach((value) => {
    peak = Math.max(peak, value);
    if (peak) worst = Math.min(worst, value / peak - 1);
  });
  return worst;
}

function metrics(values, elapsedDays) {
  if (!values.length) return {};
  const returns = dailyReturns(values);
  const totalReturn = values.at(-1) / values[0] - 1;
  const mean = returns.length ? returns.reduce((sum, item) => sum + item, 0) / returns.length : 0;
  const variance = returns.length
    ? returns.reduce((sum, item) => sum + (item - mean) ** 2, 0) / returns.length
    : 0;
  const standardDeviation = Math.sqrt(variance);
  return {
    total_return: totalReturn,
    annualized_return:
      elapsedDays >= 30 ? (values.at(-1) / values[0]) ** (365 / elapsedDays) - 1 : null,
    max_drawdown: maxDrawdown(values),
    annualized_volatility: returns.length >= 30 ? standardDeviation * Math.sqrt(365) : null,
    approximate_sharpe:
      returns.length >= 30 && standardDeviation ? (mean / standardDeviation) * Math.sqrt(365) : null,
  };
}

function resolveOrderEvents(decisionRows, orderEventRows) {
  const latestByDecision = new Map();
  orderEventRows.forEach((row) => latestByDecision.set(row.decision_id, row.payload));
  return decisionRows.map((row) => {
    const decision = row.payload;
    const event = latestByDecision.get(row.id);
    if (!event) return decision;
    const filledQuantity = Number(event.filled_quantity || decision.trade_quantity || 0);
    const fillPrice = event.filled_average_price ?? decision.fill_price;
    return {
      ...decision,
      order_status: event.status,
      trade_quantity: filledQuantity,
      fill_price: fillPrice,
      trade_value:
        filledQuantity && fillPrice != null
          ? filledQuantity * Number(fillPrice)
          : decision.trade_value,
    };
  });
}

function fromSupabase(decisionRows, performanceRows, brokerRows, orderEventRows) {
  const decisions = resolveOrderEvents(decisionRows, orderEventRows);
  const paperAccount = brokerRows[0]?.payload ?? null;
  const performance = performanceRows.map((row) => ({
    date: row.as_of,
    cyclequant: Number(row.cyclequant_value),
    btc_buy_hold: Number(row.btc_buy_hold_value),
    cash: Number(row.cash_value),
    ma200: row.ma200_value == null ? null : Number(row.ma200_value),
    btc_price: Number(row.btc_price),
    exposure: Number(row.btc_exposure),
  }));
  const latest = decisions[0] ?? null;
  const mostRecentPerformance = performance.at(-1);
  if (paperAccount && mostRecentPerformance && latest
    && mostRecentPerformance.date === latest.decision_date) {
    const markedPrice = Number(paperAccount.btc_price);
    if (markedPrice > 0 && mostRecentPerformance.btc_price > 0) {
      mostRecentPerformance.btc_buy_hold *= markedPrice / mostRecentPerformance.btc_price;
      mostRecentPerformance.btc_price = markedPrice;
      mostRecentPerformance.cyclequant = Number(paperAccount.strategy_portfolio_value);
      mostRecentPerformance.exposure = Number(
        paperAccount.actual_btc_exposure ?? paperAccount.btc_exposure,
      );
    }
  }
  const firstDate = performance[0]?.date;
  const lastDate = performance.at(-1)?.date;
  const elapsedDays = firstDate && lastDate
    ? Math.max(1, (new Date(lastDate) - new Date(firstDate)) / 86_400_000)
    : 1;
  const series = (key) => performance.map((row) => row[key]).filter((value) => value != null);
  const trades = decisions.filter((decision) => decision.action !== "HOLD");
  const portfolioValue = Number(
    paperAccount?.strategy_portfolio_value ?? performance.at(-1)?.cyclequant ?? 1000,
  );
  const currentExposure = Number(
    paperAccount?.actual_btc_exposure
      ?? paperAccount?.btc_exposure
      ?? (latest?.order_status === "FILLED" ? latest.target_exposure : latest?.current_exposure)
      ?? 0,
  );
  const currentMetrics = metrics(series("cyclequant"), elapsedDays);
  currentMetrics.total_return = portfolioValue / 1000 - 1;
  return {
    schema_version: 2,
    generated_at: new Date().toISOString(),
    mode: "paper-research",
    disclaimer: "Educational research only. Not investment advice or a recommendation to buy or sell Bitcoin.",
    summary: {
      portfolio_value: portfolioValue,
      managed_cash: Number(
        paperAccount?.strategy_cash ?? portfolioValue * (1 - currentExposure / 100),
      ),
      total_return: portfolioValue / 1000 - 1,
      current_exposure: currentExposure,
      btc_price: paperAccount?.btc_price
        ? Number(paperAccount.btc_price)
        : latest ? Number(latest.btc_price) : null,
      signal_score: latest?.signals?.total_score ?? null,
      confidence: latest?.signals?.confidence ?? null,
      latest_action: latest?.action ?? "HOLD",
      last_evaluated_at: latest?.timestamp ?? null,
    },
    performance,
    metrics: {
      cyclequant: currentMetrics,
      btc_buy_hold: metrics(series("btc_buy_hold"), elapsedDays),
      cash: metrics(series("cash"), elapsedDays),
      ma200: metrics(series("ma200"), elapsedDays),
      trade_count: trades.length,
      filled_trade_count: trades.filter((item) => item.order_status === "FILLED").length,
    },
    latest_decision: latest,
    paper_account: paperAccount,
    trade_history: trades,
    decision_journal: decisions,
    source_health: [],
    _source: "supabase",
  };
}

async function fetchJson(url, key, signal) {
  const response = await fetch(url, {
    headers: { apikey: key, Accept: "application/json" },
    signal,
  });
  if (!response.ok) throw new Error(`Data request failed (${response.status})`);
  return response.json();
}

export async function loadCycleQuantData(signal) {
  const url = (import.meta.env.VITE_SUPABASE_URL || DEFAULT_SUPABASE_URL).replace(/\/$/, "");
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || DEFAULT_SUPABASE_PUBLISHABLE_KEY;
  if (import.meta.env.VITE_CYCLEQUANT_DEMO === "true") {
    const response = await fetch(STATIC_DEMO_URL, { signal });
    if (!response.ok) throw new Error("CycleQuant demo data could not be loaded.");
    return { ...(await response.json()), _source: "demo" };
  }
  const [decisions, performance, brokers, orderEvents] = await Promise.all([
    fetchJson(
      `${url}/rest/v1/cq_public_decisions?select=*&order=decision_date.desc&limit=1000`,
      key,
      signal,
    ),
    fetchJson(`${url}/rest/v1/cq_public_performance?select=*&order=as_of.asc&limit=1000`, key, signal),
    fetchJson(
      `${url}/rest/v1/cq_public_broker_snapshots?select=*&order=captured_at.desc&limit=1`,
      key,
      signal,
    ),
    fetchJson(
      `${url}/rest/v1/cq_public_order_events?select=*&order=occurred_at.asc&limit=5000`,
      key,
      signal,
    ),
  ]);
  return fromSupabase(decisions, performance, brokers, orderEvents);
}

export async function loadCycleQuantPreview(signal) {
  const url = (import.meta.env.VITE_SUPABASE_URL || DEFAULT_SUPABASE_URL).replace(/\/$/, "");
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || DEFAULT_SUPABASE_PUBLISHABLE_KEY;
  const [brokers, decisions] = await Promise.all([
    fetchJson(
      `${url}/rest/v1/cq_public_broker_snapshots?select=*&order=captured_at.desc&limit=1`,
      key,
      signal,
    ),
    fetchJson(
      `${url}/rest/v1/cq_public_decisions?select=*&order=decision_date.desc&limit=1`,
      key,
      signal,
    ),
  ]);
  const account = brokers[0]?.payload;
  const decision = decisions[0]?.payload;
  if (!account || !decision) throw new Error("No paper snapshot has been published yet.");
  return {
    equity: Number(account.strategy_portfolio_value),
    exposure: Number(account.actual_btc_exposure ?? account.btc_exposure),
    score: Number(decision.signals.total_score),
    capturedAt: account.captured_at,
    connected: Boolean(
      account.broker_mode === "alpaca-paper"
      && account.connected
      && account.account_status === "ACTIVE"
      && account.trading_enabled
      && !account.trading_blocked
      && !account.account_blocked
      && account.position_reconciled,
    ),
  };
}
