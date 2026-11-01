const $ = (id) => document.getElementById(id);
let selectedInterval = "1h";
let latestSnapshot = null;
let chartValues = [];

const fmt = (value, digits = 2) => {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  return Number(value).toLocaleString("en-US", {minimumFractionDigits:digits, maximumFractionDigits:digits});
};
const money = (value, digits) => value == null ? "—" : "$" + fmt(value, digits == null ? (Number(value) >= 1000 ? 2 : 2) : digits);
const setText = (id, value) => { const node = $(id); if (node) node.textContent = value == null ? "—" : String(value); };
const pct = value => value == null ? "—" : (Number(value) > 0 ? "+" : "") + fmt(value, 2) + "%";
const changeClass = value => Number(value) > 0 ? "positive" : Number(value) < 0 ? "negative" : "muted-change";
const safeDate = value => {
  if (!value) return "Timestamp unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
};

function setConnectionState(state, label) {
  ["sidebar-dot", "top-dot"].forEach(id => {
    const node = $(id);
    if (node) node.className = "status-dot " + state;
  });
  setText("sidebar-status", label);
  setText("top-status", label.toUpperCase());
}

function renderCrypto(rows) {
  const list = rows || [];
  const btc = list.find(item => item.symbol === "BTCUSDT");
  const eth = list.find(item => item.symbol === "ETHUSDT");
  [
    {item:btc, price:"btc-value", change:"btc-change", state:"btc-state"},
    {item:eth, price:"eth-value", change:"eth-change", state:"eth-state"}
  ].forEach(entry => {
    const item = entry.item;
    if (!item || item.status !== "ok") {
      setText(entry.price, "Unavailable");
      setText(entry.change, "Binance feed unavailable");
      setText(entry.state, "OFFLINE");
      $(entry.change).className = "ticker-change";
      return;
    }
    const digits = Number(item.last_price) >= 1000 ? 2 : 2;
    setText(entry.price, money(item.last_price, digits));
    setText(entry.change, pct(item.change_percent) + " · 24H");
    setText(entry.state, "BINANCE");
    $(entry.change).className = "ticker-change " + changeClass(item.change_percent);
  });
}

function renderGold(gold) {
  const good = gold && gold.status === "ok" && Array.isArray(gold.candles) && gold.candles.length > 0;
  const badge = $("gold-badge");
  if (good) {
    const last = gold.latest_candle || gold.candles[gold.candles.length - 1];
    setText("gold-price", money(last.close, 2));
    setText("gold-time", "Updated " + safeDate(last.timestamp));
    setText("gold-state", gold.data_mode === "demo" ? "DEMO" : String(gold.provider || "SOURCE").toUpperCase());
    setText("chart-caption", "XAU/USD · " + String(gold.interval || selectedInterval).toUpperCase() + " · " + (gold.provider || "Market feed"));
    setText("chart-source", String(gold.provider || "SOURCE").toUpperCase() + " · " + String(gold.data_mode || "UNKNOWN").toUpperCase());
    setText("chart-bars", gold.candles.length + " BARS");
    badge.textContent = gold.data_mode === "demo" ? "DEMO DATA" : "SOURCE CONNECTED";
    badge.className = "source-chip";
    const change = gold.candles.length > 1
      ? ((Number(last.close) - Number(gold.candles[0].close)) / Number(gold.candles[0].close)) * 100
      : null;
    setText("chart-direction", change == null ? "Insufficient bars" : pct(change) + " across visible bars");
    $("chart-direction").className = "chart-footer";
    drawChart(gold.candles);
  } else {
    setText("gold-price", "Unavailable");
    setText("gold-time", (gold && gold.reason) || "No verified XAU/USD feed");
    setText("gold-state", gold && gold.data_mode === "demo" ? "DEMO" : "NO FEED");
    setText("chart-caption", "XAU/USD · waiting for connected source");
    setText("chart-source", "TWELVE DATA · NOT CONNECTED");
    setText("chart-bars", "0 BARS");
    setText("chart-direction", "No source data");
    badge.textContent = "SOURCE UNAVAILABLE";
    badge.className = "source-chip";
    drawChart([]);
  }
}

function drawChart(candles) {
  const canvas = $("gold-chart");
  if (!canvas) return;
  const wrap = canvas.parentElement;
  const width = Math.max(280, wrap.clientWidth || 600);
  const height = Math.max(180, wrap.clientHeight || 245);
  const ratio = Math.max(1, window.devicePixelRatio || 1);
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  canvas.style.width = width + "px";
  canvas.style.height = height + "px";
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const points = (candles || []).map(item => ({
    value:Number(item.close),
    time:item.timestamp
  })).filter(item => Number.isFinite(item.value));
  chartValues = points;
  const empty = $("chart-empty");
  if (points.length < 2) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");
  const left = 12, right = 66, top = 17, bottom = 23;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const values = points.map(point => point.value);
  const min = Math.min.apply(null, values);
  const max = Math.max.apply(null, values);
  const spread = max - min || Math.max(Math.abs(max) * .002, .01);
  const low = min - spread * .12;
  const high = max + spread * .12;
  const x = index => left + (index / (values.length - 1)) * plotW;
  const y = value => top + (high - value) / (high - low) * plotH;

  ctx.font = "9px DM Sans, sans-serif";
  ctx.fillStyle = "#79718b";
  ctx.strokeStyle = "rgba(157,132,190,.13)";
  ctx.lineWidth = 1;
  for (let index = 0; index <= 4; index++) {
    const yy = top + plotH * index / 4;
    ctx.beginPath();
    ctx.moveTo(left, yy);
    ctx.lineTo(width - right + 4, yy);
    ctx.stroke();
    ctx.fillText(fmt(high - ((high - low) * index / 4), 2), width - right + 10, yy + 3);
  }

  const rising = values[values.length - 1] >= values[0];
  const stroke = rising ? "#bd83ff" : "#ff7188";
  const fill = ctx.createLinearGradient(0, top, 0, top + plotH);
  fill.addColorStop(0, rising ? "rgba(160,82,255,.25)" : "rgba(255,94,122,.22)");
  fill.addColorStop(1, "rgba(18,12,29,0)");
  ctx.beginPath();
  values.forEach((value, index) => index ? ctx.lineTo(x(index), y(value)) : ctx.moveTo(x(index), y(value)));
  ctx.lineTo(x(values.length - 1), top + plotH);
  ctx.lineTo(x(0), top + plotH);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();

  ctx.beginPath();
  values.forEach((value, index) => index ? ctx.lineTo(x(index), y(value)) : ctx.moveTo(x(index), y(value)));
  ctx.save();
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 2.2;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.shadowColor = stroke;
  ctx.shadowBlur = 11;
  ctx.stroke();
  ctx.restore();

  const lastIndex = values.length - 1;
  ctx.beginPath();
  ctx.arc(x(lastIndex), y(values[lastIndex]), 3.7, 0, Math.PI * 2);
  ctx.fillStyle = stroke;
  ctx.shadowColor = stroke;
  ctx.shadowBlur = 12;
  ctx.fill();
  ctx.shadowBlur = 0;

  ctx.fillStyle = "#777087";
  ctx.textAlign = "left";
  ctx.fillText(points[0].time ? String(points[0].time).slice(0, 10) : "Start", left, height - 5);
  ctx.textAlign = "right";
  ctx.fillText(points[points.length - 1].time ? String(points[points.length - 1].time).slice(0, 10) : "Latest", width - right + 5, height - 5);
  ctx.textAlign = "left";
}

function renderMacro(rows) {
  const map = {
    broad_usd:{ticker:"usd-value", tickerTime:"usd-time", tickerState:"usd-state", digits:3, unit:""},
    us10y:{value:"nominal-value", time:"nominal-time", digits:3, unit:"%"},
    real10y:{value:"real-value", time:"real-time", digits:3, unit:"%"},
    wti:{value:"oil-value", time:"oil-time", digits:2, unit:" USD"}
  };
  (rows || []).forEach(item => {
    const config = map[item.key];
    if (!config) return;
    const good = item.status === "ok" && item.value != null;
    const formatted = good ? fmt(item.value, config.digits) : "Unavailable";
    if (config.ticker) {
      setText(config.ticker, formatted);
      setText(config.tickerTime, good ? "FRED · " + (item.observed_at || "latest observation") : "FRED · no observation");
      setText(config.tickerState, "FRED");
    } else {
      setText(config.value, good ? formatted + config.unit : formatted);
      setText(config.time, good ? "Observed " + (item.observed_at || "date unavailable") : "Source unavailable");
    }
  });
}

function renderMovers(cryptoSources) {
  const container = $("movers-list");
  container.replaceChildren();
  const providers = (cryptoSources && cryptoSources.providers) || [];
  const preferred = ["CoinGecko", "CoinMarketCap", "CoinStats"];
  const chosen = preferred.find(name => providers.some(provider => provider.name === name && provider.status === "ok"));
  if (!chosen) {
    setText("movers-provider", "No market-cap provider connected");
    setText("movers-foot", "Configure a provider key to display market movers.");
    container.innerHTML = '<div class="empty-row">Market mover feed unavailable. No placeholder prices are shown.</div>';
    return;
  }
  setText("movers-provider", chosen + " · independent source quotes");
  const assets = (cryptoSources.assets || []).map(asset => {
    const quote = (asset.quotes || []).find(item => item.source === chosen);
    return quote ? {asset:asset, quote:quote} : null;
  }).filter(entry => entry && entry.quote.change_24h_pct != null);
  assets.sort((a,b) => Math.abs(Number(b.quote.change_24h_pct)) - Math.abs(Number(a.quote.change_24h_pct)));
  if (!assets.length) {
    container.innerHTML = '<div class="empty-row">The selected provider returned no usable 24-hour changes.</div>';
    return;
  }
  assets.slice(0, 6).forEach((entry, index) => {
    const row = document.createElement("div");
    row.className = "mover-row";
    const rank = document.createElement("span");
    rank.className = "mover-rank";
    rank.textContent = String(index + 1).padStart(2, "0");
    const name = document.createElement("span");
    name.className = "mover-name";
    const title = document.createElement("strong");
    title.textContent = entry.asset.symbol || "—";
    const sub = document.createElement("small");
    sub.textContent = entry.asset.name || chosen;
    name.append(title, sub);
    const price = document.createElement("span");
    price.className = "mover-price";
    price.textContent = money(entry.quote.price_usd, 2);
    const change = document.createElement("span");
    const value = Number(entry.quote.change_24h_pct);
    change.className = "mover-change " + (value > 0 ? "positive" : value < 0 ? "negative" : "neutral");
    change.textContent = pct(value);
    row.append(rank, name, price, change);
    container.appendChild(row);
  });
  setText("movers-foot", "Quotes shown separately from " + chosen + "; not averaged across providers.");
}

function renderNews(items) {
  const container = $("news-list");
  container.replaceChildren();
  const valid = (items || []).filter(item => item && item.title && item.title !== "Feed temporarily unavailable");
  if (!valid.length) {
    container.innerHTML = '<div class="empty-row">No headlines returned by the official feeds.</div>';
    return;
  }
  valid.slice(0, 5).forEach(item => {
    const article = document.createElement("article");
    article.className = "news-item";
    const meta = document.createElement("div");
    meta.className = "news-meta";
    meta.textContent = (item.source || "Official feed") + " · " + safeDate(item.published_at);
    const link = document.createElement("a");
    link.href = item.url || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = item.title;
    const tone = document.createElement("span");
    const label = item.headline_tone || "NEUTRAL / UNCLEAR";
    tone.className = "news-tone " + (label === "GOLD SUPPORTIVE" ? "bull" : label === "GOLD HEADWIND" ? "bear" : "neutral");
    tone.textContent = label;
    const summary = document.createElement("p");
    summary.textContent = item.summary || "Open the original feed item for more context.";
    article.append(meta, link, tone, summary);
    container.appendChild(article);
  });
}

function renderSentiment(sentiment) {
  const data = sentiment || {};
  const bull = Number(data.supportive_count || 0);
  const bear = Number(data.headwind_count || 0);
  setText("analyst-bull", bull);
  setText("analyst-bear", bear);
  const gold = latestSnapshot && latestSnapshot.gold;
  const bias = (latestSnapshot && latestSnapshot.bias) || [];
  const btc = bias.find(row => row.asset === "BTC" && row.timeframe === "1H");
  const dominant = data.dominant || "No clear headline read";
  let summary = "Headline pressure is currently " + dominant.toLowerCase() + ". ";
  summary += bull + " supportive and " + bear + " headwind headlines were tagged by the transparent keyword method. ";
  if (btc && btc.bias && btc.bias !== "UNAVAILABLE") summary += "BTC 1H structure is " + btc.bias.toLowerCase() + ". ";
  if (gold && gold.status === "ok") summary += "Verified XAU/USD candles are available from " + (gold.provider || "the configured provider") + ".";
  else summary += "XAU/USD candles are not currently available from the connected gold feed.";
  setText("analyst-summary", summary);
  setText("analyst-state", latestSnapshot ? "SOURCE CONTEXT" : "WAITING");
}

function renderBias(rows) {
  const body = $("bias-table");
  body.replaceChildren();
  const assets = ["BTC", "XAU", "OIL"];
  const frames = ["1H", "4H", "1D", "1W"];
  const lookup = new Map((rows || []).map(row => [row.asset + ":" + row.timeframe, row]));
  assets.forEach(asset => {
    const tr = document.createElement("tr");
    const label = document.createElement("th");
    label.className = "bias-asset";
    label.textContent = asset;
    tr.appendChild(label);
    frames.forEach(frame => {
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
        inner.style.width = Math.max(0, Math.min(100, Number(item.alignment || 0))) + "%";
        cell.title = (item.source || "") + " · " + (item.basis || "") + " · Last " + fmt(item.last_price, 2);
      }
      bar.appendChild(inner);
      cell.append(tag, bar);
      td.appendChild(cell);
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function renderFlow(rows) {
  const container = $("flow-rows");
  container.replaceChildren();
  setText("flow-timeframe", selectedInterval.toUpperCase() + " WINDOW");
  ["BTC", "XAU", "OIL"].forEach(asset => {
    const item = (rows || []).find(row => row.asset === asset);
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
      const maxValue = Math.max(1, ...(item.points || []).flatMap(point => [Number(point.buy) || 0, Number(point.sell) || 0]));
      (item.points || []).forEach(point => {
        const pair = document.createElement("div");
        pair.className = "flow-pair";
        const buy = document.createElement("span");
        buy.className = "flow-buy";
        const sell = document.createElement("span");
        sell.className = "flow-sell";
        buy.style.height = Math.max(3, Number(point.buy || 0) / maxValue * 100) + "%";
        sell.style.height = Math.max(3, Number(point.sell || 0) / maxValue * 100) + "%";
        buy.title = "Buy-side proxy " + fmt(point.buy, 2);
        sell.title = "Sell-side proxy " + fmt(point.sell, 2);
        pair.append(buy, sell);
        bars.appendChild(pair);
      });
      section.appendChild(bars);
      const legend = document.createElement("div");
      legend.className = "flow-legend";
      const buyLabel = document.createElement("span");
      buyLabel.innerHTML = '<i class="legend-buy"></i> BUY SIDE';
      const sellLabel = document.createElement("span");
      sellLabel.innerHTML = '<i class="legend-sell"></i> SELL SIDE';
      const method = document.createElement("span");
      method.textContent = item.method || item.source || "";
      legend.append(buyLabel, sellLabel, method);
      section.appendChild(legend);
    } else {
      const missing = document.createElement("div");
      missing.className = "flow-unavailable";
      missing.textContent = (item && item.reason) || "Source volume not available for this instrument.";
      section.appendChild(missing);
    }
    container.appendChild(section);
  });
}

function renderSources(snapshot) {
  const feeds = snapshot.feeds || [];
  const crypto = snapshot.crypto || [];
  const providers = (snapshot.crypto_sources && snapshot.crypto_sources.providers) || [];
  const setStatus = (id, good, unavailableText) => {
    const node = $(id);
    node.textContent = good ? "Connected" : (unavailableText || "Unavailable");
    node.className = good ? "ok" : "bad";
  };
  const fredOk = (snapshot.macro || []).some(item => item.status === "ok");
  const binanceOk = crypto.some(item => item.status === "ok");
  const twelveOk = snapshot.gold && snapshot.gold.status === "ok";
  const newsOk = feeds.some(item => item.status === "ok");
  const getProviderStatus = name => providers.find(item => item.name === name)?.status === "ok";
  setStatus("fred-status", fredOk);
  setStatus("binance-status", binanceOk);
  setStatus("twelve-status", Boolean(twelveOk));
  setStatus("news-status", newsOk);
  setStatus("coingecko-status", getProviderStatus("CoinGecko"));
  setStatus("other-crypto-status", getProviderStatus("CoinMarketCap") || getProviderStatus("CoinStats"));
  setText("source-updated", "Snapshot " + safeDate(snapshot.generated_at));
}

function searchableAssets(snapshot) {
  const items = [];
  (snapshot.crypto || []).forEach(item => {
    if (item.status === "ok") items.push({
      symbol:item.symbol, name:item.symbol === "BTCUSDT" ? "Bitcoin" : item.symbol === "ETHUSDT" ? "Ethereum" : item.symbol,
      price:item.last_price, change:item.change_percent, source:item.source || "Binance", time:item.as_of
    });
  });
  (snapshot.crypto_sources && snapshot.crypto_sources.assets || []).forEach(asset => {
    const quote = (asset.quotes || []).find(item => item.price_usd != null);
    if (quote) items.push({
      symbol:asset.symbol, name:asset.name, price:quote.price_usd, change:quote.change_24h_pct,
      source:quote.source, time:quote.updated_at
    });
  });
  const gold = snapshot.gold;
  if (gold && gold.status === "ok" && gold.latest_candle) items.push({
    symbol:"XAU/USD", name:"Gold Spot", price:gold.latest_candle.close, change:null,
    source:gold.provider || "Twelve Data", time:gold.latest_candle.timestamp
  });
  return items;
}

function runAssetSearch(query, target) {
  if (!latestSnapshot) {
    setText(target, "Dashboard data has not loaded yet.");
    return;
  }
  const text = String(query || "").trim().toLowerCase();
  if (!text) {
    setText(target, "Enter an asset name or symbol to search the latest connected snapshot.");
    return;
  }
  const matches = searchableAssets(latestSnapshot).filter(item =>
    String(item.symbol).toLowerCase().includes(text) || String(item.name).toLowerCase().includes(text)
  ).slice(0, 4);
  if (!matches.length) {
    setText(target, "No matching asset was found in the latest connected provider snapshot.");
    return;
  }
  const summary = matches.map(item =>
    item.symbol + " · " + money(item.price, 2) + " · " + (item.change == null ? "change unavailable" : pct(item.change)) +
    " · " + item.source + " · " + safeDate(item.time)
  ).join(" | ");
  setText(target, summary);
}

function updateSearchSuggestions(query) {
  const box = $("search-results");
  const text = String(query || "").trim().toLowerCase();
  if (!text || !latestSnapshot) {
    box.hidden = true;
    return;
  }
  const matches = searchableAssets(latestSnapshot).filter(item =>
    String(item.symbol).toLowerCase().includes(text) || String(item.name).toLowerCase().includes(text)
  ).slice(0, 5);
  box.replaceChildren();
  if (!matches.length) {
    const row = document.createElement("a");
    row.textContent = "No matching assets in current snapshot";
    row.href = "#market-overview";
    box.appendChild(row);
  } else {
    matches.forEach(item => {
      const link = document.createElement("a");
      link.href = "#market-overview";
      const title = document.createElement("span");
      title.textContent = item.name + " (" + item.symbol + ")";
      const value = document.createElement("small");
      value.textContent = money(item.price, 2);
      link.append(title, value);
      link.addEventListener("click", () => {
        $("asset-search").value = item.symbol;
        runAssetSearch(item.symbol, "terminal-result");
        box.hidden = true;
      });
      box.appendChild(link);
    });
  }
  box.hidden = false;
}

async function loadDashboard() {
  const refresh = $("refresh");
  refresh.disabled = true;
  setText("system-state", "SYNCING SOURCES");
  try {
    const response = await fetch("/api/v1/terminal/snapshot?interval=" + encodeURIComponent(selectedInterval) + "&limit=200", {cache:"no-store"});
    if (!response.ok) throw new Error("Terminal API returned " + response.status);
    const snapshot = await response.json();
    latestSnapshot = snapshot;
    renderCrypto(snapshot.crypto);
    renderGold(snapshot.gold || {});
    renderMacro(snapshot.macro);
    renderMovers(snapshot.crypto_sources || {});
    renderNews(snapshot.news);
    renderSentiment(snapshot.sentiment);
    renderBias(snapshot.bias);
    renderFlow(snapshot.flow);
    renderSources(snapshot);
    setConnectionState("online", "Source monitor online");
    setText("updated", "Last sync " + new Date(snapshot.generated_at).toLocaleTimeString());
  } catch (error) {
    setConnectionState("offline", "API connection issue");
    setText("updated", "Last sync failed");
    $("news-list").textContent = error.message;
    console.error("NORDXAU dashboard load failed:", error);
  } finally {
    refresh.disabled = false;
  }
}

function tick() {
  setText("clock", new Date().toISOString().slice(11, 19) + " UTC");
}

$("refresh").addEventListener("click", loadDashboard);

$("analyst-form").addEventListener("submit", async event => {
  event.preventDefault();
  const question = $("analyst-question").value.trim();
  if (question.length < 3) return;
  const button = $("analyst-form").querySelector("button[type=submit]");
  const output = $("analyst-response");
  button.disabled = true;
  button.textContent = "Analysing…";
  output.classList.add("loading");
  output.textContent = "Sending the latest server-verified market snapshot to Gemini…";
  try {
    const response = await fetch("/api/v1/analyst/ask", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({question})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "AI Analyst request failed.");
    output.textContent = result.answer + "\\n\\nModel: " + result.model + " · Snapshot: " + safeDate(result.market_snapshot_at);
    output.classList.remove("loading");
  } catch (error) {
    output.textContent = error.message;
    output.classList.remove("loading");
  } finally {
    button.disabled = false;
    button.innerHTML = 'Ask Gemini <span>→</span>';
  }
});
document.querySelectorAll(".tf").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll(".tf").forEach(node => node.classList.remove("active"));
  button.classList.add("active");
  selectedInterval = button.dataset.interval;
  loadDashboard();
}));
$("asset-search").addEventListener("input", event => updateSearchSuggestions(event.target.value));
$("asset-search").addEventListener("keydown", event => {
  if (event.key === "Enter") {
    event.preventDefault();
    runAssetSearch(event.target.value, "terminal-result");
    $("search-results").hidden = true;
    $("terminal-query").value = event.target.value;
    $("market-overview").scrollIntoView({behavior:"smooth"});
  }
  if (event.key === "Escape") $("search-results").hidden = true;
});
document.addEventListener("click", event => {
  if (!event.target.closest(".search-wrap")) $("search-results").hidden = true;
});
$("terminal-form").addEventListener("submit", event => {
  event.preventDefault();
  runAssetSearch($("terminal-query").value, "terminal-result");
});
$("mobile-menu").addEventListener("click", () => $("sidebar").classList.toggle("open"));
document.querySelectorAll(".nav-link").forEach(link => link.addEventListener("click", () => {
  if (window.innerWidth <= 760) $("sidebar").classList.remove("open");
}));
window.addEventListener("resize", () => {
  if (latestSnapshot && latestSnapshot.gold && latestSnapshot.gold.status === "ok") drawChart(latestSnapshot.gold.candles);
});
tick();
setInterval(tick, 1000);
loadDashboard();
setInterval(loadDashboard, 60000);
