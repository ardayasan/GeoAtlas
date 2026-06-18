/**
 * Demografik popup oluşturma ve veri çekme
 */

// Önbellek: aynı kodu tekrar çekmeyelim
const demoCache = {};


async function openDemographicPopup(latlng, type, code, name) {
  const popup = L.popup({ maxWidth: 300 }).setLatLng(latlng);
  popup.setContent(`<div class="popup-title">${name}</div><p class="hint">Veriler yükleniyor...</p>`);
  popup.openOn(map);

  const cacheKey = `${type}:${code}`;
  let data = demoCache[cacheKey];

  if (!data) {
    try {
      const endpoint = type === 'province'
        ? `/demographics/province/${encodeURIComponent(code)}`
        : `/demographics/district/${encodeURIComponent(code)}`;
      data = await apiFetch(endpoint);
      demoCache[cacheKey] = data;
    } catch (e) {
      popup.setContent(`
        <div class="popup-title">${name}</div>
        <hr class="popup-divider" />
        <p class="hint">Demografik veri bulunamadı.<br>Lütfen Excel dosyası yükleyin.</p>
      `);
      return;
    }
  }

  popup.setContent(buildDemoPopupHTML(name, data, type));
}


function buildDemoPopupHTML(name, d, type) {
  const total = d.toplam_nufus || 0;
  const male = d.erkek_nufus || 0;
  const female = d.kadin_nufus || 0;

  const mPct = total ? (male / total) * 100 : 50;
  const fPct = 100 - mPct;

  const tag = type === 'province' ? 'İl' : 'İlçe';
  const num = (v) => (v == null ? null : v);

  // Yaş dağılımı yalnızca veri varsa (resmi TÜİK Excel ile sonradan eklenebilir)
  const y0 = d.yas_0_14, y1 = d.yas_15_64, y2 = d.yas_65_ust;
  const hasAge = (y0 != null && y1 != null && y2 != null) && (y0 + y1 + y2 > 0);
  const ageSection = hasAge ? `
    <hr class="popup-divider" />
    <div class="popup-section-title">Yaş Dağılımı</div>
    <div class="popup-bar">
      <div class="popup-bar-segment" style="width:${(y0/total*100).toFixed(1)}%;background:#f59e0b"></div>
      <div class="popup-bar-segment" style="width:${(y1/total*100).toFixed(1)}%;background:#10b981"></div>
      <div class="popup-bar-segment" style="width:${(y2/total*100).toFixed(1)}%;background:#6366f1"></div>
    </div>
    <div class="popup-row"><span class="popup-label" style="color:#f59e0b">0–14 yaş</span><span class="popup-value">${toPercent(y0, total)}</span></div>
    <div class="popup-row"><span class="popup-label" style="color:#10b981">15–64 yaş</span><span class="popup-value">${toPercent(y1, total)}</span></div>
    <div class="popup-row"><span class="popup-label" style="color:#6366f1">65+ yaş</span><span class="popup-value">${toPercent(y2, total)}</span></div>
  ` : '';

  // Gerçek TÜİK göstergeleri (il düzeyinde): medyan yaş, yoğunluk, artış hızı
  const rows = [];
  if (type === 'district' && d.il_adi)
    rows.push(`<div class="popup-row"><span class="popup-label">İl</span><span class="popup-value">${d.il_adi}</span></div>`);
  if (num(d.medyan_yas) != null)
    rows.push(`<div class="popup-row"><span class="popup-label">Medyan Yaş</span><span class="popup-value">${d.medyan_yas.toFixed(1)}</span></div>`);
  if (num(d.nufus_yogunluk) != null)
    rows.push(`<div class="popup-row"><span class="popup-label">Nüfus Yoğunluğu</span><span class="popup-value">${formatNumber(Math.round(d.nufus_yogunluk))} kişi/km²</span></div>`);
  if (num(d.nufus_artis_hizi) != null)
    rows.push(`<div class="popup-row"><span class="popup-label">Yıllık Artış Hızı</span><span class="popup-value">% ${(d.nufus_artis_hizi / 10).toFixed(2)}</span></div>`);
  const indicatorSection = rows.length ? `
    <hr class="popup-divider" />
    <div class="popup-section-title">Göstergeler (TÜİK ${d.veri_yili || ''})</div>
    ${rows.join('')}
  ` : '';

  return `
    <div class="popup-title">${name}
      <span style="font-size:10px;font-weight:500;color:var(--subtle);margin-left:6px">${tag} · ${d.veri_yili || '—'}</span>
    </div>

    <div class="popup-hero">
      <span class="popup-hero-value">${formatNumber(total)}</span>
      <span class="popup-hero-label">toplam nüfus</span>
    </div>
    <div class="popup-bar">
      <div class="popup-bar-segment" style="width:${mPct.toFixed(1)}%;background:#3b82f6"></div>
      <div class="popup-bar-segment" style="width:${fPct.toFixed(1)}%;background:#ec4899"></div>
    </div>
    <div class="popup-row">
      <span class="popup-label" style="color:#3b82f6">Erkek</span>
      <span class="popup-value">${formatNumber(male)} · ${toPercent(male, total)}</span>
    </div>
    <div class="popup-row">
      <span class="popup-label" style="color:#ec4899">Kadın</span>
      <span class="popup-value">${formatNumber(female)} · ${toPercent(female, total)}</span>
    </div>
    ${indicatorSection}
    ${ageSection}
  `;
}
