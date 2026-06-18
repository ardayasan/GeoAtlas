/**
 * Türkiye il ve ilçe sınır katmanları
 */

let provincesLayer = null;
let districtsLayer = null;
let provincesData = null;
let districtsData = null;

const PROVINCE_STYLE = {
  color: Config.COLORS.province.border,
  weight: 1.5,
  fillColor: Config.COLORS.province.fill,
  fillOpacity: Config.COLORS.province.opacity,
};

// Hover only changes border — never overwrites fill (preserves choropleth/group colors)
const PROVINCE_HOVER_WEIGHT = 3;

const DISTRICT_STYLE = {
  color: Config.COLORS.district.border,
  weight: 1,
  fillColor: Config.COLORS.district.fill,
  fillOpacity: Config.COLORS.district.opacity,
};

const DISTRICT_HOVER_WEIGHT = 2.5;

// İlçe görünümünde il'in ince referans çizgisi stili
const PROVINCE_BG_STYLE = {
  color: Config.COLORS.province.border,
  weight: 0.7,
  fillOpacity: 0,
  opacity: 0.4,
};

let _provinceBgMode = false;


async function loadProvinces() {
  if (provincesData) return provincesData;
  try {
    provincesData = await apiFetch('/boundaries/provinces');
    return provincesData;
  } catch (e) {
    console.warn('İl sınırları yüklenemedi:', e.message);
    return null;
  }
}

async function loadDistricts() {
  if (districtsData) return districtsData;
  try {
    districtsData = await apiFetch('/boundaries/districts');
    return districtsData;
  } catch (e) {
    console.warn('İlçe sınırları yüklenemedi:', e.message);
    return null;
  }
}


function buildProvincesLayer(geojson) {
  return L.geoJSON(geojson, {
    smoothFactor: 0,
    style: () => ({ ...PROVINCE_STYLE }),
    onEachFeature: (feature, layer) => {
      const p = feature.properties || {};
      const name = p.il_adi || p.NAME_1 || 'İl';
      const code = p.il_kodu || p.GID_1 || '';

      layer.bindTooltip(name, { sticky: true, className: 'leaflet-tooltip' });

      layer.on('mouseover', function () {
        clearTimeout(this._leaveTimer);
        this.setStyle({ weight: PROVINCE_HOVER_WEIGHT });
        this.bringToFront();
      });
      layer.on('mouseout', function () {
        const self = this;
        this._leaveTimer = setTimeout(() => {
          if (self._groupColor) {
            highlightGroupRegion(self, self._groupColor);
          } else if (activeChoroplethMetric) {
            self.setStyle({ weight: 1, color: '#64748b' });
          } else {
            provincesLayer.resetStyle(self);
          }
        }, 40);
      });
      layer.on('click', function (e) {
        L.DomEvent.stopPropagation(e);
        if (window._labelPickerActive) { pickLabelLocation(e.latlng); return; }
        if (window._selectModeActive) {
          const activeType = typeof normalizeGroupType === 'function'
            ? normalizeGroupType(window._activeGroupType)
            : window._activeGroupType;
          if (activeType && activeType !== 'region') {
            showToast('Bu grup il/bölge seçimi için uygun değil.', 'warn', 2500);
            return;
          }
          addRegionToActiveGroup(window._regionsModeActive ? 'region' : 'il', code, name);
          highlightGroupRegion(layer, window._activeGroupColor);
          return;
        }
        openDemographicPopup(e.latlng, 'province', code, name);
      });

      // Feature'a referans sakla (grup renklendirme için)
      layer._regionCode = code;
      layer._regionType = 'il';
    }
  });
}


function buildDistrictsLayer(geojson) {
  return L.geoJSON(geojson, {
    smoothFactor: 0,
    style: () => ({ ...DISTRICT_STYLE }),
    onEachFeature: (feature, layer) => {
      const p = feature.properties || {};
      const name = p.ilce_adi || p.NAME_2 || 'İlçe';
      const code = p.ilce_kodu || p.GID_2 || '';
      const ilAdi = p.il_adi || p.NAME_1 || '';

      layer.bindTooltip(`${name} / ${ilAdi}`, { sticky: true });

      layer.on('mouseover', function () {
        clearTimeout(this._leaveTimer);
        this.setStyle({ weight: DISTRICT_HOVER_WEIGHT });
        this.bringToFront();
      });
      layer.on('mouseout', function () {
        const self = this;
        this._leaveTimer = setTimeout(() => {
          if (self._groupColor) {
            highlightGroupRegion(self, self._groupColor);
          } else if (districtsLayer) {
            districtsLayer.resetStyle(self);
          }
        }, 40);
      });
      layer.on('click', function (e) {
        L.DomEvent.stopPropagation(e);
        if (window._labelPickerActive) { pickLabelLocation(e.latlng); return; }
        if (window._selectModeActive) {
          const activeType = typeof normalizeGroupType === 'function'
            ? normalizeGroupType(window._activeGroupType)
            : window._activeGroupType;
          if (activeType && activeType !== 'subregion') {
            showToast('Bu grup ilçe/alt bölge seçimi için uygun değil.', 'warn', 2500);
            return;
          }
          addRegionToActiveGroup(window._regionsModeActive ? 'subregion' : 'ilce', code, name);
          highlightGroupRegion(layer, window._activeGroupColor);
          return;
        }
        openDemographicPopup(e.latlng, 'district', code, name);
      });

      layer._regionCode = code;
      layer._regionType = 'ilce';
    }
  });
}


async function toggleProvinceLayer(visible, asBackground = false) {
  if (visible) {
    const isNew = !provincesLayer;
    if (isNew) {
      showLoading('İl sınırları yükleniyor...');
      const data = await loadProvinces();
      hideLoading();
      if (!data) return;
      provincesLayer = buildProvincesLayer(data);
    }
    const modeChanging = _provinceBgMode !== asBackground;
    _provinceBgMode = asBackground;
    // Mevcut katman renkleri (choropleth/grup) korunuyor — sadece yeni yüklenince
    // ya da bg modu değişince genel stili sıfırla
    if (isNew || modeChanging) {
      provincesLayer.setStyle(asBackground ? PROVINCE_BG_STYLE : PROVINCE_STYLE);
    }
    provincesLayer.addTo(map);
  } else {
    if (provincesLayer) {
      map.removeLayer(provincesLayer);
      if (_provinceBgMode) {
        provincesLayer.setStyle(PROVINCE_STYLE);
        _provinceBgMode = false;
      }
    }
  }
}


async function toggleDistrictLayer(visible) {
  if (visible) {
    if (!districtsLayer) {
      showLoading('İlçe sınırları yükleniyor...');
      const data = await loadDistricts();
      hideLoading();
      if (!data) return;
      districtsLayer = buildDistrictsLayer(data);
    }
    districtsLayer.addTo(map);
  } else {
    if (districtsLayer) map.removeLayer(districtsLayer);
  }
}


function handleZoomBasedLayers(zoom) {
  // Checkbox durumlarına bakarak otomatik geçiş yapma —
  // kullanıcı checkboxları kontrol ediyor.
  // Bu fonksiyon gelecekte mahalle katmanı için kullanılabilir.
}


/**
 * Grup renklendir: layer'ı verilen renkle boyar.
 * Hem grup rengi yokken hem de choropleth aktifken çalışır.
 */
function highlightGroupRegion(layer, color) {
  if (!color) return;
  layer._groupColor = color;
  if (activeChoroplethMetric && layer._choroplethColor) {
    // Choropleth aktifken: dolgu choropleth rengi KALIR,
    // grup üyeliği yalnızca kalın renkli kenarlıkla gösterilir.
    layer.setStyle({
      fillColor: layer._choroplethColor,
      fillOpacity: 0.75,
      color: color,
      weight: 3.5,
    });
  } else {
    // Choropleth yokken: klasik renkli dolgu vurgusu.
    layer.setStyle({
      fillColor: color,
      fillOpacity: 0.5,
      color: color,
      weight: 2.5,
    });
  }
}

/**
 * Bir layer'ın grup rengini kaldır, choropleth veya varsayıla döndür.
 */
function _restoreLayerStyle(layer, parentLayer, defaultStyle) {
  delete layer._groupColor;
  if (activeChoroplethMetric && layer._choroplethColor) {
    layer.setStyle({
      fillColor: layer._choroplethColor,
      fillOpacity: 0.75,
      color: '#64748b',
      weight: 1,
    });
  } else if (activeChoroplethMetric) {
    // no-data province under choropleth
    layer.setStyle({ fillColor: '#e2e8f0', fillOpacity: 0.6, color: '#94a3b8', weight: 1 });
  } else {
    parentLayer.resetStyle(layer);
  }
}

/**
 * Sadece grup renklerini kaldır (choropleth korunur).
 */
function clearGroupColors() {
  if (provincesLayer) {
    provincesLayer.eachLayer(l => {
      if (l._groupColor) _restoreLayerStyle(l, provincesLayer, PROVINCE_STYLE);
    });
  }
  if (districtsLayer) {
    districtsLayer.eachLayer(l => {
      if (l._groupColor) _restoreLayerStyle(l, districtsLayer, DISTRICT_STYLE);
    });
  }
}

/**
 * Tüm sınır katmanlarını tamamen sıfırla (choropleth dahil).
 */
function resetAllBoundaryStyles() {
  if (provincesLayer) {
    provincesLayer.eachLayer(l => { delete l._groupColor; delete l._choroplethColor; });
    provincesLayer.setStyle(PROVINCE_STYLE);
  }
  if (districtsLayer) {
    districtsLayer.eachLayer(l => { delete l._groupColor; });
    districtsLayer.setStyle(DISTRICT_STYLE);
  }
}
