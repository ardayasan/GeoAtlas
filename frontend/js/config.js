/**
 * Uygulama konfigürasyonu
 */
const Config = {
  API_BASE: 'http://localhost:8000/api',

  MAP: {
    CENTER: [54.0, 15.0],
    ZOOM: 4,
    MIN_ZOOM: 3,
    MAX_ZOOM: 18,
    ZOOM_PROVINCE: 7,
    ZOOM_DISTRICT: 10,
    MAX_BOUNDS: [[24, -31], [72, 45]],
    REGION_LEVELS: [
      { maxZoom: 4, level: 0 },
      { maxZoom: 5, level: 1 },
      { maxZoom: 6, level: 2 },
      { maxZoom: 8, level: 3 },
      { maxZoom: 18, level: 3 },
    ],
  },

  TILE_PROVIDERS: {
    carto_light: {
      label: 'Açık Harita',
      url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanları &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 19,
    },
    carto_dark: {
      label: 'Koyu Harita',
      url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanları &copy; <a href="https://carto.com/attributions">CARTO</a>',
      maxZoom: 19,
    },
    osm: {
      label: 'OpenStreetMap',
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkıda bulunanları',
      maxZoom: 19,
    },
    esri: {
      label: 'Uydu Görüntüsü',
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
      maxZoom: 18,
    },
  },

  DEFAULT_TILE: 'carto_light',

  COLORS: {
    province:    { fill: '#3b82f6', border: '#1d4ed8', opacity: 0.12 },
    district:    { fill: '#f97316', border: '#c2410c', opacity: 0.12 },
    mosques:     '#10b981',
    churches:    '#6366f1',
    worship_other: '#94a3b8',
    schools:     '#22c55e',
    universities: '#ef4444',
    kindergartens: '#38bdf8',
    labels:      '#f43f5e',
  },

  ICON_SIZE: [28, 28],
};
