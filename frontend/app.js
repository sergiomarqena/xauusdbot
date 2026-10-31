const byId = (id) => document.getElementById(id);
const number = (value, digits = 2) => value == null ? "—" : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });

async function loadDashboard() {
  byId("api-status").textContent = "Connecting…";
  try {
    const [statusResponse, overviewResponse] = await Promise.all([
      fetch("/api/v1/market/status", { cache: "no-store" }),
      fetch("/api/v1/research/overview", { cache: "no-store" }),
    ]);
    if (!statusResponse.ok || !overviewResponse.ok) throw new Error("API request failed");
    const status = await statusResponse.json();
    const overview = await overviewResponse.json();
    const badge = byId("data-badge");
    badge.textContent = status.data_mode === "provider" ? "EXTERNAL DATA" : "DEMO DATA";
    badge.className = `status ${status.data_mode}`;
    byId("symbol").textContent = overview.symbol;
    byId("interval").textContent = `${overview.interval.toUpperCase()} INTERVAL`;
    byId("provider").textContent = overview.provider;
    byId("data-mode").textContent = overview.data_mode === "demo" ? "Illustrative data only" : "External provider connected";
    byId("market-status").textContent = status.data_mode === "demo" ? "Demo series" : "Provider connected";
    byId("api-status").textContent = "Online";
    byId("observations").textContent = `${overview.candle_count} observations`;
    const latest = overview.latest_candle;
    byId("last-close").textContent = number(latest?.close, 3);
    byId("last-time").textContent = latest ? new Date(latest.timestamp).toLocaleString() : "No candle";
    const m = overview.measurements;
    const change = m.change_percent;
    byId("change").textContent = change == null ? "—" : `${change >= 0 ? "+" : ""}${number(change, 3)}%`;
    byId("change").className = `metric-value ${change < 0 ? "error" : ""}`;
    byId("ema20").textContent = number(m.ema_20, 3);
    byId("ema50").textContent = number(m.ema_50, 3);
    byId("rsi14").textContent = number(m.rsi_14, 2);
    byId("atr14").textContent = number(m.atr_14, 3);
    byId("interpretation").textContent = overview.interpretation;
  } catch (error) {
    byId("api-status").textContent = "Unavailable";
    byId("api-status").className = "error";
    byId("data-badge").textContent = "DATA UNAVAILABLE";
    byId("data-badge").className = "status";
    console.error(error);
  }
}

function tick() { byId("clock").textContent = `${new Date().toISOString().slice(11, 19)} UTC`; }
byId("refresh").addEventListener("click", loadDashboard);
tick(); setInterval(tick, 1000); loadDashboard();
