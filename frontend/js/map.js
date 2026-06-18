/**
 * Leaflet harita başlatma ve temel yardımcı fonksiyonlar
 */

let map;
let activeTileLayer = null;
let activeTileKey = Config.DEFAULT_TILE;

function initMap() {
  map = L.map('map', {
    center: Config.MAP.CENTER,
    zoom: Config.MAP.ZOOM,
    minZoom: Config.MAP.MIN_ZOOM,
    maxZoom: Config.MAP.MAX_ZOOM,
    maxBounds: Config.MAP.MAX_BOUNDS || null,
    maxBoundsViscosity: Config.MAP.MAX_BOUNDS ? 0.6 : 0,
    zoomControl: true,
    attributionControl: true,
  });

  // Varsayılan tile katmanı
  switchTileLayer(Config.DEFAULT_TILE);

  map.on('zoomend', onZoomChange);

  return map;
}


function switchTileLayer(key) {
  const provider = Config.TILE_PROVIDERS[key];
  if (!provider) return;

  if (activeTileLayer) map.removeLayer(activeTileLayer);

  activeTileLayer = L.tileLayer(provider.url, {
    attribution: provider.attribution,
    maxZoom: provider.maxZoom || 19,
    // OSM yalnızca a/b/c subdomain'i destekler (d.tile.openstreetmap.org yok).
    // 'abc' hem OSM hem CARTO için geçerli. Provider özel değer verebilir.
    subdomains: provider.subdomains || 'abc',
  }).addTo(map);

  activeTileKey = key;

  // Koyu haritada sınır renklerini güncelle
  const isDark = key === 'carto_dark';
  document.documentElement.setAttribute('data-tile', isDark ? 'dark' : 'light');

  // Tile switcher butonlarını güncelle
  document.querySelectorAll('.tile-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tile === key);
  });
}


function onZoomChange() {
  const z = map.getZoom();
  // Zoom bazlı otomatik sınır geçişi (boundaries.js tarafından da kontrol edilir)
  if (typeof handleZoomBasedLayers === 'function') {
    handleZoomBasedLayers(z);
  }
}


function showLoading(text = 'Yükleniyor...') {
  document.getElementById('loading-text').textContent = text;
  document.getElementById('loading-overlay').classList.remove('hidden');
}

function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden');
}


/**
 * Hafif üst progress bar — POI / ilçe gibi ikincil yüklemeler için.
 * Tam ekran overlay yerine kullanılır (sadece ilk yükleme overlay alır).
 */
let _progressCount = 0;
function showProgress() {
  _progressCount++;
  const el = document.getElementById('top-progress');
  if (el) el.classList.remove('hidden');
}
function hideProgress() {
  _progressCount = Math.max(0, _progressCount - 1);
  if (_progressCount === 0) {
    const el = document.getElementById('top-progress');
    if (el) el.classList.add('hidden');
  }
}


/**
 * Sayıyı Türkçe format ile biçimlendir (1234567 → 1.234.567)
 */
function formatNumber(n) {
  if (n === null || n === undefined || n === '') return '—';
  return Number(n).toLocaleString('tr-TR');
}

/**
 * Yüzde hesapla
 */
function toPercent(part, total) {
  if (!total || total === 0) return '—';
  return ((part / total) * 100).toFixed(1) + '%';
}


/**
 * Basit API fetch yardımcısı
 */
async function apiFetch(path, options = {}) {
  const url = Config.API_BASE + path;
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API hatası');
  }
  return res.json();
}


/**
 * DivIcon oluşturucu — inline SVG icon içerir
 */
function makeDivIcon(innerSvg, color, size = 26) {
  return L.divIcon({
    html: `<div style="
      width:${size}px;height:${size}px;
      background:${color};
      border:2px solid rgba(255,255,255,.9);
      border-radius:50%;
      display:flex;align-items:center;justify-content:center;
      box-shadow:0 2px 6px rgba(0,0,0,.35);
    ">${innerSvg}</div>`,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

/**
 * Pin şeklinde DivIcon
 */
function makePinIcon(color, size = 28) {
  return L.divIcon({
    html: `<div style="
      width:${size}px;height:${size}px;
      position:relative;
    ">
      <div style="
        width:${size}px;height:${size}px;
        background:${color};
        border:2px solid white;
        border-radius:50% 50% 50% 0;
        transform:rotate(-45deg);
        box-shadow:0 1px 4px rgba(0,0,0,0.35);
      "></div>
    </div>`,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}
