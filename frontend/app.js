'use strict';
const $ = id => document.getElementById(id);
const names = { US: 'United States', GB: 'United Kingdom', EU: 'Europe', IN: 'India' };
const colors = { US: '#365be5', GB: '#46a7ab', EU: '#a58bd5', IN: '#e69451' };
const sourceColors = ['#365be5', '#43a8a8', '#e89752', '#a083ca', '#db7896'];
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = value => Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
let data, selectedProduct = '', descending = true, visible = [];

function filterScores(scores, filters) {
  const query = filters.search.trim().toLowerCase();
  return scores.filter(s => s.fmos >= filters.minimum &&
    (filters.market === 'All' || s.country === filters.market) &&
    (filters.category === 'All' || s.category === filters.category) &&
    (filters.stage === 'All' || s.stage === filters.stage) &&
    s.product.toLowerCase().includes(query));
}
function currentFilters() {
  return Object.fromEntries(['search', 'market', 'category', 'stage', 'minimum'].map(key => [key, $(key).value]));
}
function legend(items) {
  return items.map(([label, color]) => `<span class="legend-item"><i class="legend-swatch" style="background:${color}"></i>${escapeHTML(label)}</span>`).join('');
}
function chooseProduct(product, scroll = false) {
  selectedProduct = product;
  $('product').value = product;
  renderTable();
  renderProduct();
  if (scroll) $('signals').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}
function render() {
  if (!data) return;
  const filters = currentFilters();
  visible = filterScores(data.scores, filters).sort((a, b) => descending ? b.fmos - a.fmos : a.fmos - b.fmos);
  const top = [...visible].sort((a, b) => b.fmos - a.fmos)[0];
  $('min-label').textContent = filters.minimum;
  $('count').textContent = visible.length;
  $('top-score').textContent = top ? fmt(top.fmos) : '—';
  $('top-name').textContent = top ? `${top.product} · ${top.country}` : 'No matching results';
  $('breakouts').textContent = visible.filter(s => s.stage === 'Breakout').length;
  $('market-count').textContent = new Set(visible.map(s => s.country)).size;
  const keys = new Set(visible.map(s => JSON.stringify([s.product, s.country])));
  $('sources-count').textContent = `${new Set(data.history.filter(h => keys.has(JSON.stringify([h.product, h.country]))).map(h => h.source)).size} sources represented`;
  $('result-count').textContent = `${visible.length} results`;
  $('download').disabled = !visible.length;
  const products = [...new Set(visible.map(s => s.product))].sort();
  if (!products.includes(selectedProduct)) selectedProduct = top?.product || '';
  $('product').replaceChildren(...products.map(p => new Option(p, p)));
  $('product').value = selectedProduct;
  $('product').disabled = !products.length;
  renderTable();
  renderScatter();
  renderProduct();
  renderBacktest();
}
function renderTable() {
  $('leaderboard').innerHTML = visible.map(s => `<tr class="${s.product === selectedProduct ? 'selected' : ''}">
    <td><button class="product-button" data-product="${escapeHTML(s.product)}" aria-label="Inspect ${escapeHTML(s.product)}">${escapeHTML(s.product)}</button><span class="product-category">${escapeHTML(s.category)}</span></td>
    <td class="country-cell"><abbr class="country-code" title="${escapeHTML(names[s.country] || s.country)}">${escapeHTML(s.country)}</abbr></td>
    <td class="score-cell">${fmt(s.fmos)}<div class="score-track" aria-hidden="true"><div class="score-fill" style="width:${s.fmos}%"></div></div></td>
    <td><span class="stage stage-${s.stage.toLowerCase()}">${escapeHTML(s.stage)}</span></td><td class="velocity-col">${fmt(s.velocity)}</td></tr>`).join('');
  $('empty').hidden = !!visible.length;
  $('sort-score').textContent = `Score ${descending ? '↓' : '↑'}`;
  $('sort-score').setAttribute('aria-label', `Sort score ${descending ? 'ascending' : 'descending'}`);
  $('sort-score').closest('th').setAttribute('aria-sort', descending ? 'descending' : 'ascending');
}
function renderScatter() {
  const x = v => 48 + v * 2.66, y = v => 276 - v * 2.34;
  let svg = '<svg viewBox="0 0 350 320" role="img" aria-label="Opportunity score versus saturation. Each point represents one product and market.">';
  svg += `<rect x="48" y="42" width="133" height="93.6" rx="3" fill="#eef4ff"/><text class="zone-label" x="58" y="58" style="fill:#7490c3">HIGH OPPORTUNITY</text>`;
  for (const tick of [0, 25, 50, 75, 100]) {
    svg += `<line class="grid" x1="48" x2="314" y1="${y(tick)}" y2="${y(tick)}"/><text x="37" y="${y(tick) + 4}" text-anchor="end">${tick}</text><text x="${x(tick)}" y="295" text-anchor="middle">${tick}</text>`;
  }
  svg += '<text class="axis-title" x="181" y="315" text-anchor="middle">Saturation →</text><text class="axis-title" transform="translate(15,165) rotate(-90)" text-anchor="middle">Opportunity score →</text>';
  svg += visible.map(s => `<circle class="chart-point" cx="${x(s.saturation)}" cy="${y(s.fmos)}" r="${4 + s.velocity / 30}" fill="${colors[s.country] || '#365be5'}" opacity=".78" stroke="white" stroke-width="1.5" tabindex="0" role="button" data-product="${escapeHTML(s.product)}" aria-label="Inspect ${escapeHTML(s.product)}, ${escapeHTML(s.country)}, score ${s.fmos}, saturation ${s.saturation}"><title>${escapeHTML(s.product)} · ${escapeHTML(s.country)}\nScore ${s.fmos} · Saturation ${s.saturation}</title></circle>`).join('');
  if (!visible.length) svg += '<text x="181" y="175" text-anchor="middle">No matching results</text>';
  $('scatter').innerHTML = svg + '</svg>';
  $('market-legend').innerHTML = legend(data.countries.map(c => [names[c] || c, colors[c] || '#365be5']));
}
function renderProduct() {
  $('no-product').hidden = !!selectedProduct;
  $('product-content').hidden = !selectedProduct;
  if (!selectedProduct) return;
  const country = $('market').value;
  const allMarkets = data.scores.filter(s => s.product === selectedProduct).sort((a, b) => b.fmos - a.fmos);
  const inspected = allMarkets.filter(s => country === 'All' || s.country === country);
  $('history-title').textContent = `${selectedProduct} · ${country === 'All' ? 'all markets' : names[country] || country}`;
  const histories = data.history.filter(h => h.product === selectedProduct && (country === 'All' || h.country === country));
  const series = new Map();
  histories.forEach(h => {
    const peak = Math.max(1, ...h.points.map(p => p[1]));
    if (!series.has(h.source)) series.set(h.source, new Map());
    const days = series.get(h.source);
    h.points.forEach(([day, value]) => {
      const previous = days.get(day) || [0, 0];
      days.set(day, [previous[0] + value / peak * 100, previous[1] + 1]);
    });
  });
  const dates = [...new Set(histories.flatMap(h => h.points.map(p => p[0])))].sort();
  $('history-period').textContent = dates.length ? `${dates.length} observation dates` : 'No history';
  const start = Date.parse(dates[0]), end = Date.parse(dates.at(-1));
  const x = day => 43 + (Date.parse(day) - start) / Math.max(1, end - start) * 590;
  const y = value => 206 - value * 1.7;
  let svg = '<svg viewBox="0 0 660 245" role="img" aria-label="Normalized source history for the selected product and market. Each line is a source indexed to its own peak.">';
  [0, 25, 50, 75, 100].forEach(t => { svg += `<line class="grid" x1="43" x2="633" y1="${y(t)}" y2="${y(t)}"/><text x="32" y="${y(t) + 4}" text-anchor="end">${t}</text>`; });
  const sourceList = [...series.keys()].sort();
  sourceList.forEach((source, i) => {
    const points = [...series.get(source)].sort(([a], [b]) => a.localeCompare(b));
    const path = points.map(([day, [sum, count]], j) => `${j ? 'L' : 'M'}${x(day).toFixed(2)},${y(sum / count).toFixed(2)}`).join(' ');
    svg += `<path class="line-path" stroke="${sourceColors[i % sourceColors.length]}" d="${path}"><title>${escapeHTML(source)}</title></path>`;
    if (points.length === 1) svg += `<circle cx="${x(points[0][0])}" cy="${y(points[0][1][0] / points[0][1][1])}" r="3" fill="${sourceColors[i % sourceColors.length]}"/>`;
  });
  [...new Set([0, Math.floor((dates.length - 1) / 2), dates.length - 1])].filter(i => i >= 0 && dates[i]).forEach(i => {
    const label = new Date(dates[i]).toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' });
    svg += `<text x="${x(dates[i])}" y="232" text-anchor="middle">${escapeHTML(label)}</text>`;
  });
  if (!dates.length) svg += '<text x="335" y="125" text-anchor="middle">No source history available</text>';
  $('history-chart').innerHTML = svg + '</svg>';
  $('source-legend').innerHTML = legend(sourceList.map((s, i) => [s.replaceAll('_', ' '), sourceColors[i % sourceColors.length]]));
  $('market-bars').innerHTML = allMarkets.map(s => `<div class="market-bar-row"><div class="market-bar-label"><span>${escapeHTML(names[s.country] || s.country)}</span><strong>${fmt(s.fmos)}</strong></div><div class="market-track"><div class="market-fill" style="width:${s.fmos}%;background:${colors[s.country] || '#365be5'}"></div></div></div>`).join('');
  $('driver-caption').textContent = country === 'All' ? 'Mean component scores across all markets · out of 100' : `${names[country] || country} · component scores out of 100`;
  const components = [['velocity', 'Velocity'], ['confidence', 'Confidence'], ['diffusion', 'Diffusion'], ['commercial', 'Commercial'], ['headroom', 'Headroom']];
  $('drivers').innerHTML = components.map(([key, label]) => {
    const value = inspected.reduce((sum, s) => sum + (key === 'headroom' ? 100 - s.saturation : s[key]), 0) / Math.max(1, inspected.length);
    return `<div class="driver"><div class="driver-name">${label}<span>${Math.round(data.weights[key] * 100)}% weight</span></div><strong class="driver-value">${fmt(value)}</strong><div class="market-track"><div class="market-fill" style="width:${value}%;background:${key === 'headroom' ? '#e59a63' : '#5572df'}"></div></div></div>`;
  }).join('');
}
function renderBacktest() {
  // The published evaluation covers the entire dataset, not today's filtered selections.
  const stats = data.backtest;
  const selected = data.backtests.filter(r => r.predicted_score >= 60);
  $('precision').textContent = selected.length ? `${(stats.precision_at_60 * 100).toFixed(1)}%` : '—';
  $('correlation').textContent = stats.samples > 1 ? stats.rank_correlation.toFixed(3) : '—';
  $('samples').textContent = stats.samples.toLocaleString();
  $('backtest-description').textContent = `${stats.horizon_days}-day outcomes across the full dataset. Filters above do not change this evaluation.`;
  $('validation-note').textContent = !stats.samples ? 'Not enough complete history to evaluate outcomes.' : data.mode === 'demo' || data.mode === 'mixed' ? 'Includes synthetic data. These results do not establish real-world predictive power.' : 'Historical evaluation is not a guarantee of future results. Validate with out-of-sample data.';
}
function csvCell(value) {
  let text = String(value);
  if (/^[=+\-@\t\r\n]/.test(text)) text = "'" + text;
  return '"' + text.replaceAll('"', '""') + '"';
}
function download() {
  const columns = ['country', 'product', 'category', 'fmos', 'stage', 'velocity', 'confidence', 'diffusion', 'commercial', 'saturation'];
  const csv = [columns.join(','), ...visible.map(row => columns.map(c => csvCell(row[c])).join(','))].join('\r\n');
  const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url; link.download = `earlysignal-${String(data.as_of || 'results').slice(0, 10)}.csv`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function load() {
  $('load-error').hidden = true;
  $('data-status').textContent = 'Loading pipeline results…';
  try {
    const response = await fetch('data.json');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const incoming = await response.json();
    if (!Array.isArray(incoming.scores) || !Array.isArray(incoming.history) || !incoming.backtest) throw new Error('Invalid snapshot');
    data = incoming;
    $('market').replaceChildren(new Option('All markets', 'All'), ...data.countries.map(c => new Option(names[c] || c, c)));
    $('category').replaceChildren(new Option('All categories', 'All'), ...[...new Set(data.scores.map(s => s.category))].sort().map(c => new Option(c, c)));
    $('data-status').textContent = { demo: 'Demo dataset · Synthetic signals for exploration, not commercial decisions.', mixed: 'Mixed dataset · Contains synthetic and imported observations.', imported: 'Imported results · Snapshot of the supplied observations, not a live feed.', empty: 'No observations available. Import data and refresh the snapshot.' }[data.mode] || 'Results snapshot';
    $('updated').textContent = data.as_of ? `Data through ${new Date(data.as_of).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })}` : 'No data';
    $('footer-data').textContent = `${data.observation_count.toLocaleString()} observations · Exported ${new Date(data.generated_at).toLocaleDateString()}`;
    render();
  } catch (error) {
    $('load-error').hidden = false;
    $('data-status').textContent = 'Results unavailable';
    $('download').disabled = true;
    console.error('Unable to load dashboard snapshot', error);
  }
}
$('filters').addEventListener('submit', e => e.preventDefault());
$('filters').addEventListener('input', render);
$('filters').addEventListener('reset', () => setTimeout(render, 0));
$('empty-reset').addEventListener('click', () => $('filters').reset());
$('product').addEventListener('change', e => chooseProduct(e.target.value));
$('sort-score').addEventListener('click', () => { descending = !descending; render(); });
$('download').addEventListener('click', download);
$('retry').addEventListener('click', load);
for (const id of ['leaderboard', 'scatter']) {
  $(id).addEventListener('click', e => { const target = e.target.closest('[data-product]'); if (target) chooseProduct(target.dataset.product, true); });
}
$('scatter').addEventListener('keydown', e => {
  if ((e.key === 'Enter' || e.key === ' ') && e.target.dataset.product) { e.preventDefault(); chooseProduct(e.target.dataset.product, true); }
});
document.querySelectorAll('.nav-link').forEach(a => a.addEventListener('click', () => {
  document.querySelectorAll('.nav-link').forEach(link => link.classList.toggle('active', link === a));
}));
// Optional browser-agent access uses the same visible filters and validation.
if (document.modelContext?.registerTool) {
  const lifecycle = new AbortController();
  try {
    Promise.resolve(document.modelContext.registerTool({
      name: 'filter_opportunities', title: 'Filter opportunities',
      description: 'Set the dashboard market and minimum score, then return matching opportunities.',
      inputSchema: { type: 'object', properties: { market: { type: 'string', enum: ['All', 'US', 'GB', 'EU', 'IN'] }, minimum: { type: 'number', minimum: 0, maximum: 100 } }, required: ['market', 'minimum'], additionalProperties: false },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      execute(input) {
        if (!data) throw new Error('Results have not loaded');
        if (!input || !['All', ...data.countries].includes(input.market) || !Number.isFinite(input.minimum) || input.minimum < 0 || input.minimum > 100) throw new Error('Invalid market or minimum score');
        $('market').value = input.market; $('minimum').value = input.minimum;
        render(); return { count: visible.length, opportunities: visible.map(({ product, country, fmos }) => ({ product, country, fmos })) };
      }
    }, { signal: lifecycle.signal })).catch(error => console.warn('Browser tools unavailable', error));
    window.addEventListener('pagehide', () => lifecycle.abort(), { once: true });
  } catch (error) { console.warn('Browser tools unavailable', error); }
}
load();
