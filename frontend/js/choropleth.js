/**
 * Choropleth renklendirme sistemi
 * Demografik verilere göre il/ilçe sınırlarını renklendirir.
 */

// Renk paletleri (5 adım, açıktan koyuya)
const PALETTES = {
  toplam_nufus:    ['#ffffd9', '#edf8b1', '#7fcdbb', '#2c7fb8', '#253494'],
  medyan_yas:      ['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15'],
  nufus_yogunluk:  ['#f2f0f7', '#cbc9e2', '#9e9ac8', '#756bb1', '#54278f'],
  nufus_artis_hizi:['#e5f5e0', '#a1d99b', '#74c476', '#31a354', '#006d2c'],
  kadin_oran:      ['#f7f4f9', '#e7e1ef', '#c994c7', '#df65b0', '#980043'],
  erkek_oran:      ['#eff3ff', '#bdd7e7', '#6baed6', '#2171b5', '#084594'],
};

const METRIC_LABELS = {
  '':               'Kapalı',
  toplam_nufus:    'Toplam Nüfus',
  medyan_yas:      'Medyan Yaş',
  nufus_yogunluk:  'Nüfus Yoğunluğu (kişi/km²)',
  nufus_artis_hizi:'Yıllık Nüfus Artış Hızı (%)',
  kadin_oran:      'Kadın Oranı (%)',
  erkek_oran:      'Erkek Oranı (%)',
};

// Yüzde olmayan, ondalıklı gösterilecek metrikler (legend birimi için)
const DECIMAL_METRICS = { medyan_yas: 1, nufus_artis_hizi: 2, nufus_yogunluk: 0 };

// Tüm il demografik verileri (il_kodu → data)
let choroplethData = {};
let activeChoroplethMetric = '';


/**
 * Tüm il demografik verilerini çek.
 */
async function loadAllProvinceDemographics() {
  try {
    const list = await apiFetch('/demographics/province');
    choroplethData = {};
    for (const d of list) {
      choroplethData[String(d.il_kodu)] = d;
    }
    return choroplethData;
  } catch (e) {
    console.warn('Demografik veri çekilemedi:', e.message);
    return {};
  }
}


/**
 * Bir metrik için değer hesapla.
 */
function computeValue(data, metric) {
  const total = data.toplam_nufus || 0;
  switch (metric) {
    case 'toplam_nufus':     return total || null;
    case 'medyan_yas':       return data.medyan_yas != null ? data.medyan_yas : null;
    case 'nufus_yogunluk':   return data.nufus_yogunluk != null ? data.nufus_yogunluk : null;
    case 'nufus_artis_hizi': return data.nufus_artis_hizi != null ? data.nufus_artis_hizi / 10 : null;
    case 'kadin_oran':       return total ? (data.kadin_nufus / total) * 100 : null;
    case 'erkek_oran':       return total ? (data.erkek_nufus / total) * 100 : null;
    default:                 return null;
  }
}


/**
 * Değer dizisinden 5 quantile break noktası üret.
 */
function quantileBreaks(values) {
  const sorted = values.filter(v => v != null && !isNaN(v)).sort((a, b) => a - b);
  if (sorted.length === 0) return [0, 0, 0, 0, 0, 0];
  const n = sorted.length;
  return [0, 0.2, 0.4, 0.6, 0.8, 1].map(p => sorted[Math.min(Math.floor(p * n), n - 1)]);
}


/**
 * Değere göre renk döndür.
 */
function getColor(value, breaks, palette) {
  if (value == null) return '#cccccc';
  for (let i = palette.length - 1; i >= 0; i--) {
    if (value >= breaks[i]) return palette[i];
  }
  return palette[0];
}


/**
 * Choropleth uygula — il katmanını seçilen metriğe göre renklendir.
 */
async function applyChoropleth(metric) {
  activeChoroplethMetric = metric;

  if (!metric) {
    clearChoropleth();
    hideLegend();
    return;
  }

  if (!provincesLayer) {
    showToast('Önce il sınırlarını yükleyin.', 'warn');
    return;
  }

  // Veri yoksa çek
  if (Object.keys(choroplethData).length === 0) {
    const data = await loadAllProvinceDemographics();
    if (Object.keys(data).length === 0) {
      showToast('Türkiye demografik verisi bulunamadı.', 'warn');
      return;
    }
  }

  const palette = PALETTES[metric] || PALETTES.toplam_nufus;

  // Tüm değerleri hesapla
  const allValues = Object.values(choroplethData)
    .map(d => computeValue(d, metric))
    .filter(v => v != null);

  if (allValues.length === 0) {
    showToast('Seçilen metrik için veri yok.', 'warn');
    return;
  }

  const breaks = quantileBreaks(allValues);

  // Her il katmanını renklendir
  provincesLayer.eachLayer(layer => {
    const code = layer._regionCode;
    if (!code) return;

    // Normalize: '1', '01', 'TUR.1_1' → integer key lookup
    const digits = code.replace(/[^0-9]/g, '');
    const intVal = parseInt(digits, 10);
    const data = choroplethData[String(intVal)]
               || choroplethData[String(intVal).padStart(2, '0')]
               || choroplethData[code];

    if (!data) {
      layer.setStyle({ fillColor: '#e2e8f0', fillOpacity: 0.6, color: '#94a3b8', weight: 1 });
      return;
    }

    const value = computeValue(data, metric);
    const color = getColor(value, breaks, palette);

    layer._choroplethColor = color;
    layer.setStyle({
      fillColor: color,
      fillOpacity: 0.75,
      color: '#64748b',
      weight: 1,
    });
  });

  updateLegend(metric, breaks, palette);

  // Grup renkleri choropleth üstüne yeniden uygula
  if (typeof reapplyGroupColors === 'function') reapplyGroupColors();
}


/**
 * Choropleth'i temizle, varsayılan stile dön.
 */
function clearChoropleth() {
  activeChoroplethMetric = '';
  if (provincesLayer) {
    provincesLayer.eachLayer(layer => { delete layer._choroplethColor; });
    provincesLayer.setStyle({
      color: Config.COLORS.province.border,
      weight: 1.5,
      fillColor: Config.COLORS.province.fill,
      fillOpacity: Config.COLORS.province.opacity,
    });
  }
  hideLegend();
  // Choropleth kaldırıldıktan sonra grup renklerini geri uygula
  if (typeof reapplyGroupColors === 'function') reapplyGroupColors();
}


/**
 * Legend panelini güncelle.
 */
function updateLegend(metric, breaks, palette) {
  const legend = document.getElementById('choropleth-legend');
  if (!legend) return;

  const title = METRIC_LABELS[metric] || metric;
  const isPercent = metric.endsWith('_oran');
  const dec = DECIMAL_METRICS[metric];

  const fmt = (v) => {
    if (isPercent) return `%${v.toFixed(1)}`;
    if (dec != null) return v.toFixed(dec);
    return formatNumber(Math.round(v));
  };

  const steps = palette.map((color, i) => {
    const from = breaks[i];
    const to   = breaks[i + 1];
    let label;
    if (fmt(from) === fmt(to)) {
      label = fmt(from);
    } else if (i === palette.length - 1) {
      label = `${fmt(from)}+`;
    } else {
      label = `${fmt(from)} – ${fmt(to)}`;
    }
    return `
      <div class="legend-row">
        <span class="legend-swatch" style="background:${color}"></span>
        <span class="legend-label">${label}</span>
      </div>`;
  }).join('');

  legend.innerHTML = `
    <div class="legend-title">${title}</div>
    ${steps}
    <div class="legend-na"><span class="legend-swatch" style="background:#dddddd"></span><span class="legend-label">Veri yok</span></div>
  `;
  legend.classList.remove('hidden');
}


function hideLegend() {
  const legend = document.getElementById('choropleth-legend');
  if (legend) legend.classList.add('hidden');
}


function clearMetricSelect() {
  document.querySelectorAll('#choropleth-chips .metric-chip')
    .forEach(c => c.classList.remove('active'));
  activeChoroplethMetric = '';
}


/**
 * Excel yüklenince choropleth'i yenile (eğer aktifse).
 */
async function refreshChoroplethIfActive() {
  choroplethData = {};  // cache temizle
  if (activeChoroplethMetric) {
    await applyChoropleth(activeChoroplethMetric);
  }
}
