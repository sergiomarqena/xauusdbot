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
  const netMove = values[values.length - 1] - values[0];
  const trendUp = netMove >= 0;
  const trendColor = trendUp ? "#53e0a2" : "#ff687e";
  const trendGlow = trendUp ? "rgba(50,230,150,.85)" : "rgba(255,66,90,.9)";
  const gradient = ctx.createLinearGradient(0, top, 0, top + plotH);
  gradient.addColorStop(0, trendUp ? "rgba(52,218,145,.23)" : "rgba(255,74,101,.23)"); gradient.addColorStop(1, "rgba(10,20,31,0)");
  ctx.beginPath(); values.forEach((v, i) => i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)));
  ctx.lineTo(x(values.length - 1), top + plotH); ctx.lineTo(x(0), top + plotH); ctx.closePath();
  ctx.fillStyle = gradient; ctx.fill();
  ctx.beginPath(); values.forEach((v, i) => i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)));
  ctx.save(); ctx.strokeStyle = trendColor; ctx.lineWidth = 2.25; ctx.shadowColor = trendGlow; ctx.shadowBlur = 13; ctx.stroke(); ctx.restore();
  const last = values[values.length - 1];
  ctx.beginPath(); ctx.arc(x(values.length - 1), y(last), 3.5, 0, Math.PI * 2);
  ctx.fillStyle = trendColor; ctx.shadowColor = trendGlow; ctx.shadowBlur = 14; ctx.fill(); ctx.shadowBlur = 0;
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
    const toneTag = document.createElement("span");
    const tone = item.headline_tone || "NEUTRAL / UNCLEAR";
    toneTag.className = "news-tone " + (tone === "GOLD SUPPORTIVE" ? "bull" : tone === "GOLD HEADWIND" ? "bear" : "neutral");
    toneTag.textContent = tone;
    article.append(meta, toneTag, link, summary); container.appendChild(article);
  }
}

function renderSources(feeds, crypto, bias) {
  const status = name => (feeds || []).find(f => f.name === name)?.status === "ok";
  const paint = (id, ok, label) => {
    const row = $(id); row.innerHTML = ""; const dot = document.createElement("i"); const text = document.createElement("span");
    const strong = document.createElement("b"); dot.className = ok ? "ok" : "bad"; text.textContent = label; strong.textContent = ok ? "Online" : "Unavailable";
    row.append(dot, text, strong);
  };
  paint("source-status", status("Federal Reserve"), "Federal Reserve RSS");
  paint("bls-status", status("US Bureau of Labor Statistics"), "U.S. BLS RSS");
  paint("binance-status", (crypto || []).some(x => x.status === "ok"), "Binance spot ticker");
  paint("yahoo-status", (bias || []).some(x => x.asset === "OIL" && x.bias !== "UNAVAILABLE"), "WTI futures history");
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
    renderNews(snapshot.news); renderSources(snapshot.feeds, snapshot.crypto, snapshot.bias);
    renderSentiment(snapshot.sentiment); renderBias(snapshot.bias); renderFlow(snapshot.flow);
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


function renderSentiment(sentiment) {
  if (!sentiment) return;
  const support = Number(sentiment.supportive_count || 0);
  const headwind = Number(sentiment.headwind_count || 0);
  const neutral = Number(sentiment.neutral_count || 0);
  const supportFill = Number(sentiment.supportive_fill || 0);
  const headwindFill = Number(sentiment.headwind_fill || 0);
  setText("bull-count", support);
  setText("bear-count", headwind);
  setText("neutral-count", neutral);
  setText("bull-fill", supportFill + "% relative directional weight");
  setText("bear-fill", headwindFill + "% relative directional weight");
  $("bull-bubble").style.setProperty("--fill", supportFill + "%");
  $("bear-bubble").style.setProperty("--fill", headwindFill + "%");
  const total = supportFill + headwindFill || 1;
  $("sentiment-track-bull").style.width = (100 * supportFill / total) + "%";
  $("sentiment-track-bear").style.width = (100 * headwindFill / total) + "%";
  setText("sentiment-dominant", sentiment.dominant || "No clear read");
  setText("sentiment-method", (sentiment.method || "Keyword tags") + " · " + (support + headwind + neutral) + " headlines");
}

function renderBias(rows) {
  const body = $("bias-table");
  body.replaceChildren();
  const assets = ["BTC", "XAU", "OIL"];
  const frames = ["1H", "4H", "1D", "1W"];
  const lookup = new Map((rows || []).map(row => [row.asset + ":" + row.timeframe, row]));
  for (const asset of assets) {
    const tr = document.createElement("tr");
    const label = document.createElement("th");
    label.className = "bias-asset";
    label.textContent = asset;
    tr.appendChild(label);
    for (const frame of frames) {
      const td = document.createElement("td");
      const cell = document.createElement("div");
      const tag = document.createElement("strong");
      const bar = document.createElement("span");
      const inner = document.createElement("i");
      const item = lookup.get(asset + ":" + frame);
      if (!item || item.bias === "UNAVAILABLE") {
        cell.className = "bias-cell unavailable";
        tag.textContent = "N/A";
        bar.className = "alignment-track";
        inner.style.width = "0%";
        if (item && item.reason) cell.title = item.reason;
      } else {
        const kind = item.bias === "BULLISH" ? "bull" : item.bias === "BEARISH" ? "bear" : "mixed";
        cell.className = "bias-cell " + kind;
        tag.textContent = item.bias;
        bar.className = "alignment-track";
        inner.style.width = Math.max(0, Math.min(100, item.alignment || 0)) + "%";
        cell.title = item.source + " · " + (item.basis || "") + " · Last " + fmt(item.last_price, 2);
      }
      bar.appendChild(inner);
      cell.append(tag, bar);
      td.appendChild(cell);
      tr.appendChild(td);
    }
    body.appendChild(tr);
  }
}

function renderFlow(rows) {
  const container = $("flow-rows");
  container.replaceChildren();
  setText("flow-timeframe", selectedInterval.toUpperCase() + " WINDOW");
  for (const asset of ["BTC", "XAU", "OIL"]) {
    const item = (rows || []).find(x => x.asset === asset);
    const section = document.createElement("div");
    section.className = "flow-asset";
    const head = document.createElement("div");
    head.className = "flow-head";
    const name = document.createElement("strong");
    name.textContent = asset;
    const totals = document.createElement("span");
    const available = item && item.status === "ok";
    totals.textContent = available
      ? "BUY " + fmt(item.buy_total, 0) + " / SELL " + fmt(item.sell_total, 0) + " " + (item.unit || "")
      : ((item && item.reason) || "Volume data unavailable");
    head.append(name, totals);
    section.appendChild(head);
    if (available) {
      const bars = document.createElement("div");
      bars.className = "flow-bars";
      const maxValue = Math.max(1, ...(item.points || []).flatMap(point => [point.buy, point.sell]));
      for (const point of item.points || []) {
        const pair = document.createElement("div");
        pair.className = "flow-pair";
        const buy = document.createElement("span");
        buy.className = "flow-buy";
        const sell = document.createElement("span");
        sell.className = "flow-sell";
        buy.style.height = Math.max(3, point.buy / maxValue * 100) + "%";
        sell.style.height = Math.max(3, point.sell / maxValue * 100) + "%";
        buy.title = "Buy-side proxy " + fmt(point.buy, 2);
        sell.title = "Sell-side proxy " + fmt(point.sell, 2);
        pair.append(buy, sell);
        bars.appendChild(pair);
      }
      section.appendChild(bars);
      const legend = document.createElement("div");
      legend.className = "flow-legend";
      const buyLabel = document.createElement("span");
      buyLabel.innerHTML = '<i class="legend-buy"></i> INFLOW / BUY SIDE';
      const sellLabel = document.createElement("span");
      sellLabel.innerHTML = '<i class="legend-sell"></i> OUTFLOW / SELL SIDE';
      const method = document.createElement("span");
      method.textContent = item.method;
      legend.append(buyLabel, sellLabel, method);
      section.appendChild(legend);
    } else {
      const missing = document.createElement("div");
      missing.className = "flow-unavailable";
      missing.textContent = (item && item.reason) || "Source volume not available for this market.";
      section.appendChild(missing);
    }
    container.appendChild(section);
  }
}
