const $ = (id) => document.getElementById(id);
let selectedInterval = "1h";
let latestSnapshot = null;

const fmt = (value, digits = 2) => value == null || !Number.isFinite(Number(value))
  ? "—" : Number(value).toLocaleString(undefined, {minimumFractionDigits: digits, maximumFractionDigits: digits});
const setText = (id, value) => { const el = $(id); if (el) el.textContent = value; };
const changeClass = (value) => Number(value) > 0 ? "change positive" : Number(value) < 0 ? "change negative" : "change";

function renderMacro(item) {
  if (!item) return;
  const map = {
    broad_usd: ["usd-value", "macro-usd", "macro-usd-date", "index", 3],
    us10y: ["nominal-value", "macro-nominal", "macro-nominal-date", "%", 3],
    real10y: ["real-value", "macro-real", "macro-real-date", "%", 3],
    wti: ["oil-value", "macro-oil", "macro-oil-date", "USD/barrel", 2],
  };
  const ids = map[item.key];
  if (!ids) return;
  const [tickerId, macroId, dateId, unit, digits] = ids;
  const value = item.status === "ok" ? fmt(item.value, digits) : "Unavailable";
  setText(tickerId, value);
  setText(macroId, item.status === "ok" ? `${fmt(item.value, digits)} ${unit}` : "Unavailable");
  setText(dateId, item.status === "ok" ? `FRED · Observed ${item.observed_at}` : "FRED · Source unavailable");
  if (item.status !== "ok") $(macroId).classList.add("unavailable");
}

function renderCrypto(item) {
  if (!item) return;
  const isBtc = item.symbol === "BTCUSDT";
  const priceId = isBtc ? "btc-value" : "eth-value";
  const changeId = isBtc ? "btc-change" : "eth-change";
  const watchId = isBtc ? "watch-btc" : "watch-eth";
  const pctId = isBtc ? "watch-btc-pct" : "watch-eth-pct";
  const status = item.status === "ok";
  setText(priceId, status ? fmt(item.last_price, item.last_price > 100 ? 0 : 2) : "Unavailable");
  setText(changeId, status ? `${item.change_percent >= 0 ? "+" : ""}${fmt(item.change_percent, 2)}% · 24h` : "Feed unavailable");
  setText(watchId, status ? `$${fmt(item.last_price, item.last_price > 100 ? 0 : 2)}` : "Unavailable");
  setText(pctId, status ? `${item.change_percent >= 0 ? "+" : ""}${fmt(item.change_percent, 2)}%` : "—");
  $(pctId).className = status ? changeClass(item.change_percent) : "change";
}

function drawChart(candles) {
  const canvas = $("gold-chart");
  const empty = $("chart-empty");
  const wrap = canvas.parentElement;
  const width = wrap.clientWidth;
  const height = Math.max(260, wrap.clientHeight);
  const dpr = window.devicePixelRatio || 1;
  canvas.width = width * dpr; canvas.height = height * dpr;
  canvas.style.width = width + "px"; canvas.style.height = height + "px";
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);
  if (!candles || candles.length < 2) { empty.classList.remove("hidden"); return; }
  empty.classList.add("hidden");
  const values = candles.map(c => Number(c.close)).filter(Number.isFinite);
  if (values.length < 2) { empty.classList.remove("hidden"); return; }
  const left = 12, right = 70, top = 20, bottom = 28;
  const plotW = width - left - right, plotH = height - top - bottom;
  const min = Math.min(...values), max = Math.max(...values);
  const spread = max - min || Math.abs(max) * 0.005 || 1;
  const lo = min - spread * 0.12, hi = max + spread * 0.12;
  const x = i => left + (i / (values.length - 1)) * plotW;
  const y = v => top + ((hi - v) / (hi - lo)) * plotH;

  ctx.strokeStyle = "rgba(140,164,190,.13)"; ctx.lineWidth = 1;
  ctx.fillStyle = "#74859a"; ctx.font = "10px Segoe UI";
  for (let i = 0; i <= 4; i++) {
    const yy = top + (plotH / 4) * i;
    ctx.beginPath(); ctx.moveTo(left, yy); ctx.lineTo(width - right + 8, yy); ctx.stroke();
    const label = hi - ((hi - lo) / 4) * i;
    ctx.fillText(label.toFixed(2), width - right + 14, yy + 3);
  }
  const gradient = ctx.createLinearGradient(0, top, 0, top + plotH);
  gradient.addColorStop(0, "rgba(87,178,255,.22)"); gradient.addColorStop(1, "rgba(87,178,255,0)");
  ctx.beginPath(); values.forEach((v, i) => i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)));
  ctx.lineTo(x(values.length - 1), top + plotH); ctx.lineTo(x(0), top + plotH); ctx.closePath();
  ctx.fillStyle = gradient; ctx.fill();
  ctx.beginPath(); values.forEach((v, i) => i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)));
  ctx.strokeStyle = "#75baff"; ctx.lineWidth = 2; ctx.stroke();
  const last = values[values.length - 1];
  ctx.beginPath(); ctx.arc(x(values.length - 1), y(last), 3.5, 0, Math.PI * 2);
  ctx.fillStyle = "#b9dcff"; ctx.fill();
  const firstStamp = candles[0].timestamp?.slice(0, 16).replace("T", " ");
  const lastStamp = candles[candles.length - 1].timestamp?.slice(0, 16).replace("T", " ");
  ctx.fillStyle = "#71839a"; ctx.fillText(firstStamp || "", left, height - 7);
  ctx.textAlign = "right"; ctx.fillText(lastStamp || "", width - right + 4, height - 7); ctx.textAlign = "left";
}

function renderGold(gold) {
  const badge = $("gold-badge");
  badge.className = "pill";
  if (gold.status === "ok") {
    badge.textContent = gold.data_mode === "demo" ? "DEMO DATA" : "PROVIDER CONNECTED";
    badge.classList.add(gold.data_mode === "demo" ? "demo" : "ok");
    const last = gold.latest_candle || gold.candles?.[gold.candles.length - 1];
    setText("gold-price", last ? `$${fmt(last.close, 2)}` : "—");
    setText("gold-time", last ? `Last candle · ${new Date(last.timestamp).toLocaleString()}` : "No candle returned");
    setText("chart-caption", `XAU/USD · ${gold.interval.toUpperCase()} · ${gold.provider}`);
    setText("chart-source", `SOURCE: ${gold.provider.toUpperCase()} · ${gold.data_mode.toUpperCase()}`);
    setText("chart-bars", `${gold.candles.length} BARS`);
    const m = gold.measurements || {};
    setText("ema20", fmt(m.ema_20, 2)); setText("ema50", fmt(m.ema_50, 2));
    setText("rsi14", fmt(m.rsi_14, 2)); setText("atr14", fmt(m.atr_14, 2));
    setText("gold-note", "Measurements are descriptive only. They do not determine a trading decision.");
    $("gold-note").className = "notice";
    drawChart(gold.candles);
  } else {
    badge.textContent = gold.data_mode === "demo" ? "DEMO DATA" : "KEY REQUIRED";
    badge.classList.add("warn");
    setText("gold-price", gold.data_mode === "demo" ? "Demo series" : "Unavailable");
    setText("gold-time", gold.reason || "Gold data source unavailable");
    setText("chart-caption", "XAU/USD · no verified live feed");
    setText("chart-source", "SOURCE: NOT CONNECTED");
    setText("chart-bars", "0 BARS");
    setText("ema20", "—"); setText("ema50", "—"); setText("rsi14", "—"); setText("atr14", "—");
    setText("gold-note", gold.reason || "Gold source has not supplied data.");
    $("gold-note").className = "notice warn-text";
    drawChart([]);
  }
}

function renderNews(items) {
  const container = $("news-list");
  container.replaceChildren();
  if (!items?.length) {
    const p = document.createElement("p"); p.className = "loading-row"; p.textContent = "No headlines returned by connected feeds.";
    container.appendChild(p); return;
  }
  for (const item of items) {
    const article = document.createElement("article"); article.className = "news-item";
    const meta = document.createElement("div"); meta.className = "news-meta";
    meta.textContent = `${item.source} · ${item.published_at ? new Date(item.published_at).toLocaleString() : "Date not supplied"}`;
    const link = document.createElement("a"); link.href = item.url; link.target = "_blank"; link.rel = "noopener noreferrer";
    link.textContent = item.title;
    const summary = document.createElement("p"); summary.textContent = item.summary || "Open the original release for full context.";
    article.append(meta, link, summary); container.appendChild(article);
  }
}

function renderSources(feeds, crypto) {
  const status = name => (feeds || []).find(f => f.name === name)?.status === "ok";
  const paint = (id, ok, label) => {
    const row = $(id); row.innerHTML = ""; const dot = document.createElement("i"); const text = document.createElement("span");
    const strong = document.createElement("b"); dot.className = ok ? "ok" : "bad"; text.textContent = label; strong.textContent = ok ? "Online" : "Unavailable";
    row.append(dot, text, strong);
  };
  paint("source-status", status("Federal Reserve"), "Federal Reserve RSS");
  paint("bls-status", status("US Bureau of Labor Statistics"), "U.S. BLS RSS");
  paint("binance-status", (crypto || []).some(x => x.status === "ok"), "Binance spot ticker");
}

async function loadDashboard() {
  $("refresh").disabled = true;
  setText("system-state", "SYNCING SOURCES");
  try {
    const response = await fetch(`/api/v1/terminal/snapshot?interval=${encodeURIComponent(selectedInterval)}&limit=200`, {cache:"no-store"});
    if (!response.ok) throw new Error(`Terminal API returned ${response.status}`);
    const snapshot = await response.json(); latestSnapshot = snapshot;
    renderGold(snapshot.gold);
    (snapshot.macro || []).forEach(renderMacro);
    (snapshot.crypto || []).forEach(renderCrypto);
    renderNews(snapshot.news); renderSources(snapshot.feeds, snapshot.crypto);
    setText("system-state", "SOURCE MONITOR ONLINE");
    setText("updated", `Last sync ${new Date(snapshot.generated_at).toLocaleTimeString()}`);
  } catch (error) {
    setText("system-state", "API CONNECTION ERROR");
    $("news-list").textContent = error.message;
    console.error(error);
  } finally {
    $("refresh").disabled = false;
  }
}

function tick() { setText("clock", `${new Date().toISOString().slice(11, 19)} UTC`); }
$("refresh").addEventListener("click", loadDashboard);
document.querySelectorAll(".tf").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll(".tf").forEach(x => x.classList.remove("active"));
  button.classList.add("active"); selectedInterval = button.dataset.interval; loadDashboard();
}));
window.addEventListener("resize", () => { if (latestSnapshot?.gold?.status === "ok") drawChart(latestSnapshot.gold.candles); });
tick(); setInterval(tick, 1000); loadDashboard(); setInterval(loadDashboard, 60000);
