const STATIC_DEMO_URL = "/data/cyclequant-dashboard.json";

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
    annualized_volatility: returns.length > 1 ? standardDeviation * Math.sqrt(365) : null,
    approximate_sharpe:
      returns.length > 1 && standardDeviation ? (mean / standardDeviation) * Math.sqrt(365) : null,
  };
}

function fromSupabase(decisionRows, performanceRows) {
  const decisions = decisionRows.map((row) => row.payload);
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
  const firstDate = performance[0]?.date;
  const lastDate = performance.at(-1)?.date;
  const elapsedDays = firstDate && lastDate
    ? Math.max(1, (new Date(lastDate) - new Date(firstDate)) / 86_400_000)
    : 1;
  const series = (key) => performance.map((row) => row[key]).filter((value) => value != null);
  const trades = decisions.filter((decision) => decision.action !== "HOLD");
  const portfolioValue = performance.at(-1)?.cyclequant ?? 1000;
  return {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    mode: "paper-research",
    disclaimer: "Educational research only. Not investment advice or a recommendation to buy or sell Bitcoin.",
    summary: {
      portfolio_value: portfolioValue,
      total_return: portfolioValue / 1000 - 1,
      current_exposure: latest?.order_status === "FILLED" ? latest.target_exposure : latest?.current_exposure ?? 0,
      btc_price: latest ? Number(latest.btc_price) : null,
      signal_score: latest?.signals?.total_score ?? null,
      confidence: latest?.signals?.confidence ?? null,
      latest_action: latest?.action ?? "HOLD",
      last_evaluated_at: latest?.timestamp ?? null,
    },
    performance,
    metrics: {
      cyclequant: metrics(series("cyclequant"), elapsedDays),
      btc_buy_hold: metrics(series("btc_buy_hold"), elapsedDays),
      cash: metrics(series("cash"), elapsedDays),
      ma200: metrics(series("ma200"), elapsedDays),
      trade_count: trades.length,
      filled_trade_count: trades.filter((item) => item.order_status === "FILLED").length,
    },
    latest_decision: latest,
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
  const url = import.meta.env.VITE_SUPABASE_URL?.replace(/\/$/, "");
  const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  if (url && key) {
    try {
      const [decisions, performance] = await Promise.all([
        fetchJson(
          `${url}/rest/v1/cq_public_decisions?select=*&order=decision_date.desc&limit=1000`,
          key,
          signal,
        ),
        fetchJson(`${url}/rest/v1/cq_public_performance?select=*&order=as_of.asc&limit=1000`, key, signal),
      ]);
      if (decisions.length) return fromSupabase(decisions, performance);
    } catch (error) {
      console.warn("CycleQuant cloud data unavailable; showing the deterministic demo.", error);
    }
  }
  const response = await fetch(STATIC_DEMO_URL, { signal });
  if (!response.ok) throw new Error("CycleQuant demo data could not be loaded.");
  return { ...(await response.json()), _source: "demo" };
}
