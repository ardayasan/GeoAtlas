/**
 * Avrupa NUTS/LAU sınır katmanları.
 * Eski Türkiye katman mantığı korunur: checkbox açılırsa katman yüklenir.
 */

let regionsIndex = {};
let countryRegionsLayer = null;
let areaRegionsLayer = null;
let subareaRegionsLayer = null;
let activeRegionsIndicator = '';
let activeRegionLevel = null;
let activeRegionsChoroplethMetric = '';
let _countryBgMode = false;

// Bölge görünümünde ülkenin ince referans çizgisi stili
const COUNTRY_BG_STYLE = {
  color: '#0f766e',
  weight: 1.0,
  fillOpacity: 0,
  opacity: 0.45,
};

const REGION_STYLES = {
  country: {
    color: '#0f766e',
    weight: 1.4,
    fillColor: '#14b8a6',
    fillOpacity: 0.08,
  },
  area: {
    color: '#2563eb',
    weight: 1,
    fillColor: '#3b82f6',
    fillOpacity: 0.12,
  },
  subarea: {
    color: '#c2410c',
    weight: 0.8,
    fillColor: '#f97316',
    fillOpacity: 0.12,
  },
};

const REGION_HOVER_STYLE = {
  weight: 2.6,
  color: '#0f172a',
};

const REGION_METRIC_MAP = {
  toplam_nufus: 'population',
  nufus_yogunluk: 'density',
  medyan_yas: 'median_age',
  kadin_oran: 'kadin_oran',
  erkek_oran: 'erkek_oran',
  nufus_artis_hizi: 'growth_rate',
};

const REGION_PALETTES = {
  population: ['#ffffd9', '#edf8b1', '#7fcdbb', '#2c7fb8', '#253494'],
  density: ['#f2f0f7', '#cbc9e2', '#9e9ac8', '#756bb1', '#54278f'],
  median_age: ['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15'],
  kadin_oran: ['#f7f4f9', '#e7e1ef', '#c994c7', '#df65b0', '#980043'],
  erkek_oran: ['#eff3ff', '#bdd7e7', '#6baed6', '#2171b5', '#084594'],
  growth_rate: ['#e5f5e0', '#a1d99b', '#74c476', '#31a354', '#006d2c'],
};


async function initRegions() {
  try {
    regionsIndex = await apiFetch('/regions/index');
  } catch (e) {
    console.warn('Avrupa bölge indeksi yüklenemedi:', e.message);
    return false;
  }

  if (!regionsIndex || Object.keys(regionsIndex).length === 0) {
    return false;
  }

  window._regionsModeActive = true;
  return true;
}


async function toggleCountryRegionsLayer(visible, asBackground = false) {
  if (visible) {
    if (!countryRegionsLayer) {
      showLoading('Ülke sınırları yükleniyor...');
      try {
        const data = await apiFetch('/regions/boundaries?level=0');
        countryRegionsLayer = buildRegionGeoJsonLayer(data, 'country');
      } catch (e) {
        showToast(`Ülke sınırları yüklenemedi: ${e.message}`, 'error');
        setLayerCheckbox('layer-countries', false);
      } finally {
        hideLoading();
      }
    }
    if (countryRegionsLayer) {
      const isNew = !map.hasLayer(countryRegionsLayer);
      const modeChanging = _countryBgMode !== asBackground;
      _countryBgMode = asBackground;
      if (isNew || modeChanging) {
        countryRegionsLayer.setStyle(asBackground ? { ...COUNTRY_BG_STYLE } : { ...REGION_STYLES.country });
      }
      countryRegionsLayer.addTo(map);
    }
  } else if (countryRegionsLayer) {
    map.removeLayer(countryRegionsLayer);
    if (_countryBgMode) {
      countryRegionsLayer.setStyle({ ...REGION_STYLES.country });
      _countryBgMode = false;
    }
  }
  refreshRegionsChoroplethIfActive();
}


async function toggleAreaRegionsLayer(visible) {
  if (visible) {
    if (!areaRegionsLayer) {
      showLoading('Avrupa bölge sınırları yükleniyor...');
      try {
        const data = await apiFetch('/regions/boundaries?level=3');
        areaRegionsLayer = buildRegionGeoJsonLayer(data, 'area');
      } catch (e) {
        showToast(`Bölge sınırları yüklenemedi: ${e.message}`, 'error');
        setLayerCheckbox('layer-provinces', false);
      } finally {
        hideLoading();
      }
    }
    if (areaRegionsLayer) areaRegionsLayer.addTo(map);
  } else if (areaRegionsLayer) {
    map.removeLayer(areaRegionsLayer);
  }
  refreshRegionsChoroplethIfActive();
}


async function toggleSubareaRegionsLayer(visible) {
  if (visible) {
    if (!subareaRegionsLayer) {
      showLoading('Alt bölge sınırları yükleniyor...');
      try {
        const l4Countries = Object.entries(regionsIndex)
          .filter(([, meta]) => (meta.levels || []).includes(4))
          .map(([country]) => country);
        if (l4Countries.length === 0) {
          showToast('Alt bölge verisi bulunamadı.', 'warn');
          setLayerCheckbox('layer-districts', false);
          return;
        }
        const countries = l4Countries.join(',');
        const data = await apiFetch(`/regions/boundaries?level=4&countries=${encodeURIComponent(countries)}`);
        subareaRegionsLayer = buildRegionGeoJsonLayer(data, 'subarea');
        if (l4Countries.length === 1 && l4Countries[0] === 'TR') {
          showToast('Alt bölge verisi şu anda yalnızca Türkiye ilçeleri için mevcut.', 'info', 3500);
        }
      } catch (e) {
        showToast(`Alt bölge sınırları yüklenemedi: ${e.message}`, 'error');
        setLayerCheckbox('layer-districts', false);
      } finally {
        hideLoading();
      }
    }
    if (subareaRegionsLayer) subareaRegionsLayer.addTo(map);
  } else if (subareaRegionsLayer) {
    map.removeLayer(subareaRegionsLayer);
  }
  refreshRegionsChoroplethIfActive();
}


function setLayerCheckbox(id, checked) {
  const el = document.getElementById(id);
  if (el) el.checked = checked;
}


function buildRegionGeoJsonLayer(data, kind) {
  const baseStyle = REGION_STYLES[kind] || REGION_STYLES.area;
  return L.geoJSON(data, {
    smoothFactor: kind === 'subarea' ? 0.3 : 0.6,
    style: () => ({ ...baseStyle }),
    onEachFeature: (feature, layer) => {
      const p = feature.properties || {};
      const name = p.name_tr || p.name_en || p.code || 'Bölge';
      const code = p.code || '';
      layer.bindTooltip(name, { sticky: true, className: 'leaflet-tooltip' });
      layer.on('mouseover', function () {
        this.setStyle(REGION_HOVER_STYLE);
        this.bringToFront();
      });
      layer.on('mouseout', function () {
        restoreRegionLayerStyle(this, kind);
      });
      layer.on('click', async function (e) {
        L.DomEvent.stopPropagation(e);
        if (window._labelPickerActive) { pickLabelLocation(e.latlng); return; }
        if (window._selectModeActive) {
          const type = regionKindToGroupType(kind);
          if (window._activeGroupType && window._activeGroupType !== type) {
            showToast(`${getGroupTypeLabel(window._activeGroupType)} grubu için ${getGroupTypeLabel(type)} seçilemez.`, 'warn', 2500);
            return;
          }
          await addRegionToActiveGroup(type, code, name);
          highlightGroupRegion(layer, window._activeGroupColor);
          return;
        }
        await openRegionPopup(e.latlng, code, name);
      });
      layer._regionCode = code;
      layer._regionLevel = Number(p.level);
      layer._regionKind = kind;
    },
  });
}


function regionKindToGroupType(kind) {
  if (kind === 'country') return 'country';
  if (kind === 'subarea') return 'subregion';
  return 'region';
}


async function openRegionPopup(latlng, code, fallbackName) {
  const popup = L.popup({ maxWidth: 300 }).setLatLng(latlng);
  popup.setContent(`<div class="popup-title">${fallbackName}</div><p class="hint">Veriler yükleniyor...</p>`);
  popup.openOn(map);

  try {
    const data = await apiFetch(`/regions/${encodeURIComponent(code)}`);
    popup.setContent(buildRegionPopupHTML(data, fallbackName));
  } catch (e) {
    popup.setContent(`
      <div class="popup-title">${fallbackName}</div>
      <hr class="popup-divider" />
      <p class="hint">Bu bölge için detay bulunamadı.</p>
    `);
  }
}


function buildRegionPopupHTML(data, fallbackName) {
  const region = data.region || {};
  const stats = data.stats || {};
  const parent = data.parent || {};
  const name = region.name_tr || region.name_en || fallbackName;
  
  const popTotal = stats.population?.value || 0;
  const male = stats.population_m?.value || 0;
  const female = stats.population_f?.value || 0;
  
  const mPct = popTotal ? (male / popTotal) * 100 : 50;
  const fPct = popTotal ? (female / popTotal) * 100 : 50;
  
  const density = stats.density?.value;
  const medianAge = stats.median_age?.value;
  const growthRate = stats.growth_rate?.value;
  const year = stats.population?.year || stats.density?.year || stats.median_age?.year || '—';

  const rows = [];
  if (density != null) {
    rows.push(`<div class="popup-row"><span class="popup-label">Nüfus Yoğunluğu</span><span class="popup-value">${formatNumber(Math.round(density))} kişi/km²</span></div>`);
  }
  if (medianAge != null) {
    rows.push(`<div class="popup-row"><span class="popup-label">Medyan Yaş</span><span class="popup-value">${Number(medianAge).toFixed(1)}</span></div>`);
  }
  if (growthRate != null) {
    rows.push(`<div class="popup-row"><span class="popup-label">Yıllık Artış Hızı</span><span class="popup-value">% ${(Number(growthRate) / 10).toFixed(2)}</span></div>`);
  }
  if (parent.name_tr || parent.name_en) {
    rows.push(`<div class="popup-row"><span class="popup-label">Üst Bölge</span><span class="popup-value">${parent.name_tr || parent.name_en}</span></div>`);
  }
  
  const indicatorSection = rows.length ? `
    <hr class="popup-divider" />
    <div class="popup-section-title">Göstergeler (Eurostat ${year})</div>
    ${rows.join('')}
  ` : '';

  return `
    <div class="popup-title">${name}
      <span style="font-size:10px;font-weight:500;color:var(--subtle);margin-left:6px">L${region.level} · ${year}</span>
    </div>
    <div class="popup-hero">
      <span class="popup-hero-value">${formatNumber(Math.round(popTotal))}</span>
      <span class="popup-hero-label">toplam nüfus</span>
    </div>
    <div class="popup-bar">
      <div class="popup-bar-segment" style="width:${mPct.toFixed(1)}%;background:#3b82f6"></div>
      <div class="popup-bar-segment" style="width:${fPct.toFixed(1)}%;background:#ec4899"></div>
    </div>
    <div class="popup-row">
      <span class="popup-label" style="color:#3b82f6">Erkek</span>
      <span class="popup-value">${formatNumber(Math.round(male))} · ${mPct.toFixed(1)}%</span>
    </div>
    <div class="popup-row">
      <span class="popup-label" style="color:#ec4899">Kadın</span>
      <span class="popup-value">${formatNumber(Math.round(female))} · ${fPct.toFixed(1)}%</span>
    </div>
    ${indicatorSection}
  `;
}


async function applyRegionsChoropleth(metric) {
  activeRegionsChoroplethMetric = metric;
  activeChoroplethMetric = metric;
  activeRegionsIndicator = REGION_METRIC_MAP[metric] || '';

  if (!metric) {
    clearRegionsChoropleth();
    hideLegend();
    return;
  }

  if (!activeRegionsIndicator) {
    clearRegionsChoropleth();
    hideLegend();
    showToast('Bu metrik Avrupa verisinde sağlanmıyor.', 'warn');
    return;
  }

  const target = getChoroplethTargetLayer();
  if (!target) {
    showToast('Renklendirme için Avrupa sınır katmanı bekleniyor.', 'warn');
    return;
  }

  await paintRegions(target.layer, target.level, activeRegionsIndicator, metric);
}


async function refreshRegionsChoroplethIfActive() {
  if (activeRegionsIndicator) {
    await applyRegionsChoropleth(activeRegionsChoroplethMetric);
  }
}


function getChoroplethTargetLayer() {
  if (subareaRegionsLayer && map.hasLayer(subareaRegionsLayer)) {
    return { layer: subareaRegionsLayer, level: 4 };
  }
  if (areaRegionsLayer && map.hasLayer(areaRegionsLayer)) {
    return { layer: areaRegionsLayer, level: 3 };
  }
  if (countryRegionsLayer && map.hasLayer(countryRegionsLayer) && !_countryBgMode) {
    return { layer: countryRegionsLayer, level: 0 };
  }
  return null;
}


async function paintRegions(layerGroup, level, indicator, metricName) {
  const stats = await apiFetch(`/regions/stats?indicator=${encodeURIComponent(indicator)}&level=${level}`);
  
  if (metricName === 'nufus_artis_hizi') {
    for (let k in stats) {
      if (stats[k] != null && !isNaN(stats[k])) {
        stats[k] = stats[k] / 10;
      }
    }
  }

  const values = Object.values(stats).filter(v => v != null && !isNaN(v));
  if (values.length === 0) {
    clearRegionsChoropleth();
    hideLegend();
    showToast('Seçili katman için bu veri sağlanmıyor.', 'warn');
    return;
  }

  activeRegionLevel = level;
  const breaks = regionsQuantileBreaks(values);
  const palette = REGION_PALETTES[indicator] || REGION_PALETTES.population;

  clearRegionsChoropleth(false);
  layerGroup.eachLayer(featureLayer => {
    const value = stats[featureLayer._regionCode];
    const color = regionsColor(value, breaks, palette);
    featureLayer._choroplethColor = color;
    featureLayer.setStyle({
      fillColor: color,
      fillOpacity: 0.75,
      color: '#64748b',
      weight: 1,
    });
  });

  if (typeof updateLegend === 'function') {
    updateLegend(metricName || activeChoroplethMetric, breaks, palette);
    document.getElementById('choropleth-legend')?.classList.remove('hidden');
  }
}


function clearRegionsChoropleth(resetState = true) {
  for (const layerGroup of [countryRegionsLayer, areaRegionsLayer, subareaRegionsLayer]) {
    if (!layerGroup) continue;
    layerGroup.eachLayer(featureLayer => {
      delete featureLayer._choroplethColor;
      restoreRegionLayerStyle(featureLayer, featureLayer._regionKind);
    });
  }
  if (resetState) {
    activeRegionsIndicator = '';
    activeRegionLevel = null;
    activeRegionsChoroplethMetric = '';
  }
}


function restoreRegionLayerStyle(layer, kind) {
  if (layer._choroplethColor) {
    layer.setStyle({
      fillColor: layer._choroplethColor,
      fillOpacity: 0.75,
      color: '#64748b',
      weight: 1,
    });
  } else {
    layer.setStyle({ ...(REGION_STYLES[kind] || REGION_STYLES.area) });
  }
}


function regionsQuantileBreaks(values) {
  const sorted = values.filter(v => v != null && !isNaN(v)).sort((a, b) => a - b);
  if (!sorted.length) return [0, 0, 0, 0, 0, 0];
  const n = sorted.length;
  return [0, 0.2, 0.4, 0.6, 0.8, 1].map(p => sorted[Math.min(Math.floor(p * n), n - 1)]);
}


function regionsColor(value, breaks, palette) {
  if (value == null || isNaN(value)) return '#dddddd';
  for (let i = palette.length - 1; i >= 0; i--) {
    if (value >= breaks[i]) return palette[i];
  }
  return palette[0];
}
