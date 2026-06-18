/**
 * POI (cami, okul, kilise vb.) katmanları — marker clustering ile
 */

const poiLayers = {};
const poiClusterGroups = {};
const poiLoadingPromises = {};
let poiCatalog = null;
let activePoiCountry = 'TR';

// Her kategori için yapılandırma
const POI_CONFIG = {
  mosques: {
    endpoint: '/poi/mosques',
    markerSvg: `<svg width="13" height="13" viewBox="0 0 20 20" fill="white" xmlns="http://www.w3.org/2000/svg"><path d="M10 2C7.8 2 6 4 6 7h8c0-3-1.8-5-4-5z"/><rect x="4" y="8" width="12" height="2" rx="1"/><rect x="5" y="11" width="10" height="7" rx="1"/></svg>`,
    color: Config.COLORS.mosques,
    label: 'Cami / Mescid',
  },
  churches: {
    endpoint: '/poi/churches',
    markerSvg: `<svg width="12" height="12" viewBox="0 0 20 20" fill="white" xmlns="http://www.w3.org/2000/svg"><rect x="9" y="2" width="2" height="16"/><rect x="4" y="7" width="12" height="2"/></svg>`,
    color: Config.COLORS.churches,
    label: 'Kilise / Katedral',
  },
  worship_other: {
    endpoint: '/poi/worship_other',
    markerSvg: `<svg width="11" height="11" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="10" cy="10" r="7" fill="white"/><circle cx="10" cy="10" r="4" fill="none" stroke="rgba(0,0,0,.25)" stroke-width="1.5"/></svg>`,
    color: Config.COLORS.worship_other,
    label: 'Diğer İbadet Yeri',
  },
  schools: {
    endpoint: '/poi/schools',
    markerSvg: `<svg width="13" height="13" viewBox="0 0 20 20" fill="white" xmlns="http://www.w3.org/2000/svg"><path d="M10 2L2 7l8 5 8-5-8-5z"/><path d="M5 9.5v5c1.5 1.5 8.5 1.5 10 0v-5" fill="none" stroke="white" stroke-width="1.5"/></svg>`,
    color: Config.COLORS.schools,
    label: 'Okul',
  },
  universities: {
    endpoint: '/poi/universities',
    markerSvg: `<svg width="13" height="13" viewBox="0 0 20 20" fill="white" xmlns="http://www.w3.org/2000/svg"><path d="M10 2L2 7l8 5 8-5-8-5z"/><path d="M5 9.5v5c1.5 1.5 8.5 1.5 10 0v-5" fill="none" stroke="white" stroke-width="1.5"/><line x1="16" y1="7" x2="16" y2="13" stroke="white" stroke-width="1.5"/></svg>`,
    color: Config.COLORS.universities,
    label: 'Üniversite',
  },
  kindergartens: {
    endpoint: '/poi/kindergartens',
    markerSvg: `<svg width="12" height="12" viewBox="0 0 20 20" fill="white" xmlns="http://www.w3.org/2000/svg"><polygon points="10,2 12.5,7.5 18.5,7.5 13.8,11.3 15.6,17 10,13.5 4.4,17 6.2,11.3 1.5,7.5 7.5,7.5"/></svg>`,
    color: Config.COLORS.kindergartens,
    label: 'Anaokulu / Kreş',
  },
};

function poiLayerKey(category, country = activePoiCountry) {
  return `${country}:${category}`;
}

function getCheckedPoiCategories() {
  return Object.keys(POI_CONFIG).filter(category => {
    const id = `layer-${category.replace('_', '-')}`;
    return document.getElementById(id)?.checked;
  });
}

function setPoiCheckbox(category, checked) {
  const id = `layer-${category.replace('_', '-')}`;
  const cb = document.getElementById(id);
  if (cb) cb.checked = checked;
}

function getCountryLabel(country) {
  const meta = poiCatalog?.countries?.[country];
  return meta?.name || country;
}

function buildPoiEndpoint(category, country = activePoiCountry) {
  const cfg = POI_CONFIG[category];
  const endpoint = cfg?.endpoint || `/poi/${category}`;
  return `${endpoint}?country=${encodeURIComponent(country)}`;
}

function fitPoiCountry(country) {
  const bbox = poiCatalog?.countries?.[country]?.bbox || regionsIndex?.[country]?.bbox;
  if (!bbox || bbox.length !== 4) return;
  const [minLon, minLat, maxLon, maxLat] = bbox;
  map.fitBounds([[minLat, minLon], [maxLat, maxLon]], { padding: [24, 24] });
}

async function initPoiControls(usingRegions = false) {
  const select = document.getElementById('poi-country-select');
  if (!select) return;

  try {
    poiCatalog = await apiFetch('/poi/catalog');
  } catch (e) {
    console.warn('POI kataloğu alınamadı:', e.message);
  }

  const countries = poiCatalog?.countries || { TR: { name: 'Türkiye' } };
  
  const allowedCodes = ['TR', 'DE', 'FR', 'NL', 'IT', 'ES', 'EL', 'LU'];
  const validCountries = Object.entries(countries).filter(([code]) => allowedCodes.includes(code));

  select.innerHTML = validCountries
    .map(([code, meta]) => {
      // Map EL to GR for display purposes if preferred, but value should remain EL
      const displayCode = code === 'EL' ? 'GR' : code;
      return `<option value="${code}">${meta.name || code} (${displayCode})</option>`;
    })
    .join('');

  // Include GR in the allowed initialization check
  select.value = validCountries.length > 0 ? (countries.TR ? 'TR' : validCountries[0][0]) : 'TR';
  activePoiCountry = select.value;

  if (usingRegions) {
    document.getElementById('poi-scope-section')?.classList.remove('hidden');
  }

  select.addEventListener('change', async () => {
    const previousCountry = activePoiCountry;
    activePoiCountry = select.value || 'TR';

    for (const category of getCheckedPoiCategories()) {
      const previousLayer = poiClusterGroups[poiLayerKey(category, previousCountry)];
      if (previousLayer && map.hasLayer(previousLayer)) {
        map.removeLayer(previousLayer);
      }
    }

    fitPoiCountry(activePoiCountry);
    await refreshPoiStatus();

    for (const category of getCheckedPoiCategories()) {
      await togglePoiLayer(category, true);
    }
  });
}


function buildPoiPopup(props, label) {
  // Name: try multiple OSM fields before falling back to generic label
  const name = props.name
    || props['name:tr']
    || props['official_name']
    || props['name:en']
    || props.operator
    || null;

  const displayName = name || `Adsız ${label}`;
  const unnamed = !name;

  // Address: street + number, district, city, postcode
  const addrParts = [
    props['addr:street'],
    props['addr:housenumber'],
  ].filter(Boolean);
  const addrLine1 = addrParts.join(' ');
  const addrLine2 = [
    props['addr:district'] || props['addr:suburb'],
    props['addr:city'] || props['addr:province'],
    props['addr:postcode'],
  ].filter(Boolean).join(', ');

  // Extra info
  const operator      = props.operator && props.operator !== name ? props.operator : null;
  const operatorType  = props['operator:type'];
  const website       = props.website || props['contact:website'];
  const phone         = props.phone   || props['contact:phone'];
  const education     = props.education;
  const religion      = props.religion;

  // Helper
  const row = (lbl, val) => val
    ? `<div class="popup-row"><span class="popup-label">${lbl}</span><span class="popup-value">${val}</span></div>`
    : '';

  // Operator type label
  const opTypeMap = { government:'Devlet', public:'Kamu', private:'Özel',
                      religious:'Dini', 'private_non_profit':'Vakıf' };
  const opTypeLabel = opTypeMap[operatorType] || operatorType || null;

  // Education level label
  const eduMap = { kindergarten:'Anaokulu', primary:'İlkokul', secondary:'Ortaokul/Lise',
                   university:'Üniversite', college:'Yüksekokul' };
  const eduLabel = eduMap[education] || education || null;

  return `
    <div class="popup-title">${displayName}${unnamed ? '<span style="font-size:10px;font-weight:400;color:#94a3b8;margin-left:4px">(isimsiz)</span>' : ''}</div>
    <hr class="popup-divider" />
    ${row('Tür', label + (opTypeLabel ? ` · ${opTypeLabel}` : ''))}
    ${eduLabel ? row('Eğitim Kademesi', eduLabel) : ''}
    ${religion ? row('Din', religion.charAt(0).toUpperCase() + religion.slice(1)) : ''}
    ${operator ? row('Kurum / Operatör', operator) : ''}
    ${addrLine1 ? row('Adres', addrLine1 + (addrLine2 ? '<br><span style="color:#94a3b8">' + addrLine2 + '</span>' : '')) : ''}
    ${!addrLine1 && addrLine2 ? row('Konum', addrLine2) : ''}
    ${phone ? row('Telefon', `<a href="tel:${phone}" style="color:var(--blue)">${phone}</a>`) : ''}
    ${website ? row('Web', `<a href="${website}" target="_blank" rel="noopener" style="color:var(--blue);word-break:break-all">${website.replace(/^https?:\/\//,'')}</a>`) : ''}
    ${props.osm_id ? `<div class="popup-row" style="margin-top:4px"><span class="popup-label" style="color:#cbd5e1">OSM</span><span class="popup-value" style="color:#cbd5e1">${props.osm_id}</span></div>` : ''}
  `;
}


async function loadPoiLayer(category, country = activePoiCountry) {
  const key = poiLayerKey(category, country);
  if (poiClusterGroups[key]) return true;

  // Aynı anahtar için zaten yükleniyorsa o Promise'i paylaş
  if (key in poiLoadingPromises) return poiLoadingPromises[key];

  const cfg = POI_CONFIG[category];
  if (!cfg) return false;

  const promise = (async () => {
    showProgress();
    let geojson;
    try {
      geojson = await apiFetch(buildPoiEndpoint(category, country));
    } catch (e) {
      hideProgress();
      console.warn(`${category} yüklenemedi:`, e.message);
      showToast(e.message, 'warn', 5000);
      return false;
    }
    hideProgress();

    const icon = makeDivIcon(cfg.markerSvg, cfg.color, 26);

    const cluster = L.markerClusterGroup({
      maxClusterRadius: 60,
      iconCreateFunction: (c) => {
        const count = c.getChildCount();
        return L.divIcon({
          html: `<div style="
            background:${cfg.color};color:white;
            width:36px;height:36px;
            border-radius:50%;border:2px solid white;
            display:flex;align-items:center;justify-content:center;
            font-size:12px;font-weight:700;
            box-shadow:0 1px 4px rgba(0,0,0,0.3);
          ">${count}</div>`,
          className: '',
          iconSize: [36, 36],
          iconAnchor: [18, 18],
        });
      },
    });

    L.geoJSON(geojson, {
      pointToLayer: (feature, latlng) => L.marker(latlng, { icon }),
      onEachFeature: (feature, layer) => {
        const props = feature.properties || {};
        const name = props.name || props['name:tr'] || cfg.label;
        layer.bindTooltip(name, { direction: 'top', offset: [0, -14] });
        layer.bindPopup(buildPoiPopup(props, cfg.label));
      },
    }).addTo(cluster);

    poiClusterGroups[key] = cluster;
    return true;
  })();

  poiLoadingPromises[key] = promise;
  try {
    return await promise;
  } finally {
    delete poiLoadingPromises[key];
  }
}


async function togglePoiLayer(category, visible) {
  const key = poiLayerKey(category);
  const cbId = `layer-${category.replace(/_/g, '-')}`;
  const cb = document.getElementById(cbId);

  if (visible) {
    if (!poiClusterGroups[key]) {
      // Yükleme sırasında çift tıklamayı engelle
      if (cb) cb.disabled = true;
      let loaded = false;
      try {
        loaded = await loadPoiLayer(category);
      } finally {
        if (cb) cb.disabled = false;
      }
      if (!loaded) {
        setPoiCheckbox(category, false);
        return;
      }
    }
    // Async yükleme sırasında kullanıcı kapatmış olabilir
    if (!cb?.checked) return;
    if (poiClusterGroups[key]) {
      poiClusterGroups[key].addTo(map);
    }
  } else {
    if (poiClusterGroups[key]) {
      map.removeLayer(poiClusterGroups[key]);
    }
  }
}


/**
 * POI veri durumunu kontrol et ve sidebar'a yaz.
 */
async function refreshPoiStatus() {
  const container = document.getElementById('poi-status');
  container.innerHTML = `
    <div class="status-loading">
      <div class="mini-spinner"></div>
      <span>Katalog yükleniyor...</span>
    </div>
  `;

  try {
    const catalog = await apiFetch(`/poi/catalog`);

    const CAT_META = {
      mosques:       { label: 'Cami / Mescid',       color: '#10b981' },
      churches:      { label: 'Kilise / Katedral',    color: '#8b5cf6' },
      worship_other: { label: 'Diğer İbadethaneler',  color: '#94a3b8' },
      schools:       { label: 'İlk / Orta / Lise',    color: '#22c55e' },
      universities:  { label: 'Üniversite / MYO',     color: '#ef4444' },
      kindergartens: { label: 'Anaokulu / Kreş',      color: '#06b6d4' },
    };

    const countries = catalog.countries;
    const codes = Object.keys(countries);
    const poiCountries = codes.filter(c => Object.values(countries[c].categories).some(v => v.available));
    const totalPoi = poiCountries.reduce((sum, c) =>
      sum + Object.values(countries[c].categories).reduce((s, v) => s + (v.count || 0), 0), 0);

    // Summary bar
    let html = `
      <div class="veri-summary">
        <div class="veri-summary-stat">
          <span class="veri-summary-val">${codes.length}</span>
          <span class="veri-summary-lbl">Ülke</span>
        </div>
        <div class="veri-summary-divider"></div>
        <div class="veri-summary-stat">
          <span class="veri-summary-val">${poiCountries.length}</span>
          <span class="veri-summary-lbl">POI Verisi</span>
        </div>
        <div class="veri-summary-divider"></div>
        <div class="veri-summary-stat">
          <span class="veri-summary-val">${formatNumber(totalPoi)}</span>
          <span class="veri-summary-lbl">Toplam Nokta</span>
        </div>
      </div>
    `;

    // Country cards
    for (const code of codes) {
      const c = countries[code];
      const isTR = code === 'TR';
      const availableCats = Object.entries(c.categories).filter(([, v]) => v.available);
      const missingCats  = Object.entries(c.categories).filter(([, v]) => !v.available);
      const totalPoints  = availableCats.reduce((s, [, v]) => s + (v.count || 0), 0);

      const catChips = availableCats.map(([k, v]) => {
        const meta = CAT_META[k] || { label: k, color: '#888' };
        return `<div class="veri-cat-chip">
          <span class="veri-cat-dot" style="background:${meta.color}"></span>
          <span class="veri-cat-name">${meta.label}</span>
          <span class="veri-cat-count">${formatNumber(v.count)}</span>
        </div>`;
      }).join('');

      const missingChips = missingCats.map(([k]) => {
        const meta = CAT_META[k] || { label: k };
        return `<span class="veri-missing-chip">${meta.label}</span>`;
      }).join('');

      const demoBadge = isTR
        ? `<span class="veri-badge veri-badge-ok">İl &amp; İlçe</span>`
        : `<span class="veri-badge veri-badge-dim">—</span>`;

      const uid = `country-${code}`;

      html += `
        <div class="veri-card" id="card-${code}">
          <button class="veri-card-header" onclick="toggleVeriCard('${uid}')">
            <div class="veri-card-left">
              <span class="veri-card-flag">${countryFlag(code)}</span>
              <div class="veri-card-info">
                <span class="veri-card-name">${c.name}</span>
                <span class="veri-card-code">${code}</span>
              </div>
            </div>
            <div class="veri-card-right">
              ${totalPoints > 0 ? `<span class="veri-badge veri-badge-blue">${formatNumber(totalPoints)}</span>` : `<span class="veri-badge veri-badge-dim">POI yok</span>`}
              <svg class="veri-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
          </button>
          <div class="veri-card-body hidden" id="${uid}">
            <div class="veri-card-section">
              <span class="veri-section-label">Demografik Veri</span>
              ${demoBadge}
            </div>
            ${catChips ? `
            <div class="veri-card-section" style="flex-direction:column;align-items:stretch;gap:0">
              <span class="veri-section-label" style="margin-bottom:6px">POI Kategorileri</span>
              <div class="veri-cat-list">${catChips}</div>
            </div>` : ''}
            ${missingChips ? `
            <div class="veri-card-section" style="flex-direction:column;align-items:stretch;gap:0">
              <span class="veri-section-label" style="margin-bottom:5px">Eksik Kategoriler</span>
              <div style="display:flex;flex-wrap:wrap;gap:4px">${missingChips}</div>
            </div>` : ''}
          </div>
        </div>
      `;
    }

    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<p class="hint" style="padding:var(--s4)">Katalog alınamadı.</p>';
  }
}


function toggleVeriCard(uid) {
  const body = document.getElementById(uid);
  const card = body?.closest('.veri-card');
  if (!body || !card) return;
  const isOpen = !body.classList.contains('hidden');
  body.classList.toggle('hidden', isOpen);
  card.classList.toggle('veri-card-open', !isOpen);
}


function countryFlag(code) {
  const FLAGS = {
    TR:'🇹🇷', DE:'🇩🇪', FR:'🇫🇷', NL:'🇳🇱', IT:'🇮🇹', ES:'🇪🇸',
    EL:'🇬🇷', LU:'🇱🇺', AL:'🇦🇱', AT:'🇦🇹', BA:'🇧🇦', BE:'🇧🇪',
    BG:'🇧🇬', CH:'🇨🇭', CY:'🇨🇾', CZ:'🇨🇿', DK:'🇩🇰', EE:'🇪🇪',
    FI:'🇫🇮', HR:'🇭🇷', HU:'🇭🇺', IE:'🇮🇪', IS:'🇮🇸', LI:'🇱🇮',
    LT:'🇱🇹', LV:'🇱🇻', ME:'🇲🇪', MK:'🇲🇰', MT:'🇲🇹', NO:'🇳🇴',
    PL:'🇵🇱', PT:'🇵🇹', RO:'🇷🇴', RS:'🇷🇸', SE:'🇸🇪', SI:'🇸🇮',
    SK:'🇸🇰', UA:'🇺🇦', XK:'🇽🇰',
  };
  return FLAGS[code] || '🌐';
}

