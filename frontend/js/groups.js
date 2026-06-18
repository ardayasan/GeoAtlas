/**
 * Gruplandırma sistemi
 */

let groups = [];
let activeGroupId = null;

window._selectModeActive = false;
window._activeGroupColor = null;

const GROUP_TYPE_LABELS = {
  country: 'Ülke',
  region: 'Bölge',
  subregion: 'Alt Bölge',
  il: 'Bölge',
  ilce: 'Alt Bölge',
};

const GROUP_TYPE_CLASS = {
  country: 'country',
  region: 'region',
  subregion: 'subregion',
  il: 'region',
  ilce: 'subregion',
};

// Aktif seçim oturumunda eklenen bölgeler (canlı liste için)
let _sessionSelections = [];
// Inline istatistik açık olan grup id'leri
const _expandedStats = new Set();


async function loadGroups() {
  try {
    groups = await apiFetch('/groups');
    renderGroupsList();
    // Önce checkbox durumunu senkronize et, SONRA renkleri uygula —
    // aksi halde guard erken döner ve ilk yüklemede gruplar görünmez.
    syncGroupsCheckbox();
    reapplyGroupColors();
  } catch (e) {
    console.warn('Gruplar yüklenemedi:', e.message);
  }
}


/**
 * "Bölge Grupları" katman checkbox'ını gerçek duruma göre senkronize eder:
 * bölgesi olan en az bir grup varsa renkler gösterildiği için işaretli olur.
 */
function syncGroupsCheckbox() {
  const cb = document.getElementById('layer-groups');
  if (!cb) return;
  const hasRegions = groups.some(g => (g.regions || []).length > 0);
  cb.checked = hasRegions;
}


function renderGroupsList() {
  const container = document.getElementById('groups-list');
  if (!groups.length) {
    container.innerHTML = `
      <div class="empty-state">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
        </svg>
        <p>Henüz grup yok</p>
        <span>Bölgeleri gruplayarak toplam nüfusu ve demografiyi hesaplayın</span>
      </div>`;
    return;
  }

  container.innerHTML = groups.map(g => {
    const regions = g.regions || [];
    const type = getGroupType(g);
    const typeLabel = getGroupTypeLabel(type);
    const shown = regions.slice(0, 3);
    const rest = regions.length - shown.length;
    const previewTags = regions.length
      ? `<div class="group-regions-preview">
           ${shown.map(r => `<span class="region-chip">${escapeHtml(r.region_name || r.region_code)}</span>`).join('')}
           ${rest > 0 ? `<span class="region-chip more">+${rest} daha</span>` : ''}
         </div>`
      : '';

    return `
    <div class="group-item" data-id="${g.id}" style="--accent:${g.color}">
      <div class="item-main">
        <div class="group-swatch" style="background:${g.color}"></div>
        <div class="group-info">
          <div class="group-name">${escapeHtml(g.name)}</div>
          <div class="group-meta">
            <span class="group-type-badge ${GROUP_TYPE_CLASS[type] || 'region'}">${typeLabel}</span>
            ${regions.length} bölge${regions.length ? '' : ' · boş'}
          </div>
        </div>
        <div class="item-actions">
          <button class="icon-btn" title="Bölge seç" onclick="enterSelectMode(${g.id}, '${g.color}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
          <button class="icon-btn ${_expandedStats.has(g.id) ? 'active' : ''}" title="İstatistikler" onclick="toggleGroupStats(${g.id})">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          </button>
          <button class="icon-btn danger" title="Sil" onclick="requestDeleteGroup(${g.id})">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
          </button>
        </div>
      </div>
      ${previewTags}
      <div class="group-confirm hidden" id="group-confirm-${g.id}">
        <span class="group-confirm-text">"${escapeHtml(g.name)}" silinsin mi?</span>
        <button class="btn btn-sm btn-ghost" onclick="cancelDeleteGroup(${g.id})">İptal</button>
        <button class="btn btn-sm btn-danger" onclick="deleteGroup(${g.id})">Sil</button>
      </div>
      <div class="group-stats-expand hidden" id="group-expand-${g.id}"></div>
    </div>`;
  }).join('');

  // Açık kalan istatistik panellerini geri yükle
  for (const id of _expandedStats) {
    const exp = document.getElementById(`group-expand-${id}`);
    if (exp) { exp.classList.remove('hidden'); loadGroupStatsInto(id); }
  }
}


async function createGroup() {
  const name = document.getElementById('group-name-input').value.trim();
  const color = document.getElementById('group-color-input').value;
  const segActive = document.querySelector('#group-type-seg .seg-btn.active');
  const region_type = segActive ? segActive.dataset.type : 'il';
  if (!name) {
    showToast('Grup adı boş olamaz.', 'warn');
    return;
  }
  try {
    const group = await apiFetch('/groups', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, color, region_type }),
    });
    closeModal('modal-group');
    groups.push(group);
    renderGroupsList();
    syncGroupsCheckbox();
    const tLabel = getGroupTypeLabel(region_type).toLocaleLowerCase('tr-TR');
    showToast(`"${name}" ${tLabel} grubu oluşturuldu. Bölge eklemek için karttaki ✎ düğmesine tıklayın.`, 'success');
  } catch (e) {
    showToast('Grup oluşturulamadı: ' + e.message, 'error');
  }
}


/** Grubun türünü döndürür: kayıtlı region_type, yoksa üyelerin tipi, yoksa 'il'. */
function getGroupType(group) {
  if (!group) return 'region';
  if (group.region_type) return normalizeGroupType(group.region_type);
  const r = (group.regions || [])[0];
  return r ? normalizeGroupType(r.region_type) : 'region';
}


function normalizeGroupType(type) {
  if (type === 'il') return 'region';
  if (type === 'ilce') return 'subregion';
  return type || 'region';
}


function getGroupTypeLabel(type) {
  return GROUP_TYPE_LABELS[normalizeGroupType(type)] || 'Bölge';
}


// ── Inline silme onayı ─────────────────────────────────────────
function requestDeleteGroup(id) {
  // diğer açık onayları kapat
  document.querySelectorAll('.group-confirm').forEach(el => el.classList.add('hidden'));
  const el = document.getElementById(`group-confirm-${id}`);
  if (el) el.classList.remove('hidden');
}

function cancelDeleteGroup(id) {
  const el = document.getElementById(`group-confirm-${id}`);
  if (el) el.classList.add('hidden');
}


async function deleteGroup(id) {
  const group = groups.find(g => g.id === id);
  if (!group) return;
  try {
    await apiFetch(`/groups/${id}`, { method: 'DELETE' });
    groups = groups.filter(g => g.id !== id);
    _expandedStats.delete(id);
    renderGroupsList();
    reapplyGroupColors();
    showToast('Grup silindi.', 'success');
  } catch (e) {
    showToast('Silinemedi: ' + e.message, 'error');
  }
}


// ── Inline istatistik (modal yerine kart içinde expand) ────────
function toggleGroupStats(id) {
  const exp = document.getElementById(`group-expand-${id}`);
  if (!exp) return;
  if (_expandedStats.has(id)) {
    _expandedStats.delete(id);
    exp.classList.add('hidden');
    exp.innerHTML = '';
  } else {
    _expandedStats.add(id);
    exp.classList.remove('hidden');
    loadGroupStatsInto(id);
  }
  // aktif buton stilini güncelle
  const card = document.querySelector(`.group-item[data-id="${id}"]`);
  const statBtn = card?.querySelectorAll('.icon-btn')[1];
  if (statBtn) statBtn.classList.toggle('active', _expandedStats.has(id));
}


async function loadGroupStatsInto(id) {
  const exp = document.getElementById(`group-expand-${id}`);
  if (!exp) return;
  exp.innerHTML = `<div class="loading-inline"><div class="mini-spinner"></div><span>Hesaplanıyor…</span></div>`;
  try {
    const data = await apiFetch(`/groups/${id}`);
    exp.innerHTML = buildGroupStatsHTML(data);
  } catch (e) {
    exp.innerHTML = `<p class="hint" style="padding:8px 0">Veri alınamadı: ${escapeHtml(e.message)}</p>`;
  }
}


function buildGroupStatsHTML(data) {
  const total = data.total_population || 0;
  const regions = data.regions || [];
  const hasDemo = total > 0;
  const avgDensity = data.avg_density;
  const avgMedianAge = data.avg_median_age;
  const years = data.stats_years || {};
  const type = getGroupType(data);
  const typeLabel = getGroupTypeLabel(type).toLocaleLowerCase('tr-TR');

  const demoSection = hasDemo ? `
    <div class="stat-card">
      <div class="stat-card-label">Ortalama Yoğunluk</div>
      <div class="stat-card-value">${avgDensity != null ? formatNumber(Math.round(avgDensity)) : '—'}</div>
      <div class="stat-card-sub">kişi/km²${years.density ? ` · ${years.density}` : ''}</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-label">Ortalama Medyan Yaş</div>
      <div class="stat-card-value">${avgMedianAge != null ? avgMedianAge.toFixed(1) : '—'}</div>
      <div class="stat-card-sub">yaş${years.median_age ? ` · ${years.median_age}` : ''}</div>
    </div>
  ` : `<p class="hint" style="grid-column:1/-1">Seçili bölgeler için sağlanan demografik veri yok.</p>`;

  const memberLabel = `Dahil ${getGroupTypeLabel(type)}ler`;
  const memberSection = regions.length ? `
    <div class="stat-card full-width">
      <div class="stat-card-label">${memberLabel} (${regions.length})</div>
      <div class="member-list">
        ${regions.map(r => `
          <span class="member-chip">${escapeHtml(r.region_name || r.region_code)}
            <button class="member-chip-x" title="Gruptan çıkar"
              onclick="removeRegionFromGroup(${data.id}, '${escapeHtml(String(r.region_code))}')">✕</button>
          </span>`).join('')}
      </div>
    </div>` : '';

  return `
    <div class="group-stats-grid">
      <div class="stat-card highlight full-width">
        <div class="stat-card-label">Toplam Nüfus</div>
        <div class="stat-card-value">${hasDemo ? formatNumber(total) : '—'}</div>
        <div class="stat-card-sub">${regions.length} ${typeLabel}${years.population ? ` · ${years.population}` : ''}</div>
      </div>
      ${demoSection}
      ${memberSection}
    </div>
  `;
}


/** Bir bölgeyi gruptan çıkarır. */
async function removeRegionFromGroup(groupId, code) {
  try {
    await apiFetch(`/groups/${groupId}/regions/${encodeURIComponent(code)}`, { method: 'DELETE' });
    const g = groups.find(x => x.id === groupId);
    if (g) g.regions = (g.regions || []).filter(r => String(r.region_code) !== String(code));
    renderGroupsList();
    reapplyGroupColors();
    syncGroupsCheckbox();
    showToast('Bölge gruptan çıkarıldı.', 'success', 1800);
  } catch (e) {
    showToast('Çıkarılamadı: ' + e.message, 'error');
  }
}


async function enterSelectMode(groupId, color) {
  const group = groups.find(g => g.id === groupId);
  const type = getGroupType(group);

  activeGroupId = groupId;
  window._selectModeActive = true;
  window._activeGroupColor = color;
  window._activeGroupType = type;
  _sessionSelections = [];

  const typeLabel = getGroupTypeLabel(type).toLocaleLowerCase('tr-TR');
  document.getElementById('select-mode-text').textContent =
    `"${group?.name || 'Grup'}" için ${typeLabel} seçin`;
  document.getElementById('select-mode-banner').classList.remove('hidden');
  document.getElementById('layer-groups').checked = true;

  await ensureGroupSelectionLayer(type);
  reapplyGroupColors();

  // Sidebar canlı listesini aç + gruplar paneline geç
  const sess = document.getElementById('select-session');
  if (sess) {
    document.getElementById('select-session-label').textContent =
      `"${group?.name || 'Grup'}" — Seçilen ${getGroupTypeLabel(type)}ler`;
    sess.classList.remove('hidden');
  }
  switchPanel('groups');
  updateSelectSessionUI();
}


async function ensureGroupSelectionLayer(type) {
  const regionsMode = Boolean(window._regionsModeActive);

  // Alt bölge (ilçe) her zaman Türkiye ilçe katmanını açar — regionsMode'dan bağımsız
  if (type === 'subregion') {
    await toggleProvinceLayer(false); setLayerCheckbox('layer-provinces', false);
    setLayerCheckbox('layer-districts', true);
    await toggleDistrictLayer(true);
    return;
  }

  if (regionsMode) {
    // Avrupa modunda: country veya region için NUTS katmanları
    if (type === 'country') {
      await toggleAreaRegionsLayer(false); setLayerCheckbox('layer-regions-l3', false);
      setLayerCheckbox('layer-countries', true);
      await toggleCountryRegionsLayer(true);
    } else {
      await toggleCountryRegionsLayer(false); setLayerCheckbox('layer-countries', false);
      setLayerCheckbox('layer-provinces', true);
      await toggleAreaRegionsLayer(true);
    }
    return;
  }

  // Türkiye modunda: region = il katmanı
  await toggleDistrictLayer(false); setLayerCheckbox('layer-districts', false);
  setLayerCheckbox('layer-provinces', true);
  await toggleProvinceLayer(true);
}


function exitSelectMode() {
  window._selectModeActive = false;
  window._activeGroupColor = null;
  window._activeGroupType = null;
  activeGroupId = null;
  _sessionSelections = [];
  document.getElementById('select-mode-banner').classList.add('hidden');
  const sess = document.getElementById('select-session');
  if (sess) sess.classList.add('hidden');
  loadGroups();
}


async function addRegionToActiveGroup(type, code, name) {
  if (!activeGroupId || !code) return;
  // Aynı oturumda tekrar tıklanırsa atla
  if (_sessionSelections.some(s => s.code === code)) return;
  try {
    await apiFetch(`/groups/${activeGroupId}/regions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ region_type: type, region_code: code, region_name: name }),
    });
    _sessionSelections.push({ code, name });
    updateSelectSessionUI();
  } catch (e) {
    if (e.message.includes('zaten')) {
      // zaten gruptaysa yine de oturum listesine göster
      if (!_sessionSelections.some(s => s.code === code)) {
        _sessionSelections.push({ code, name });
        updateSelectSessionUI();
      }
    } else {
      console.warn('Bölge eklenemedi:', e.message);
    }
  }
}


function updateSelectSessionUI() {
  const n = _sessionSelections.length;
  const badge = document.getElementById('select-mode-count');
  if (badge) badge.textContent = `${n} bölge`;

  const list = document.getElementById('select-session-list');
  if (!list) return;
  if (!n) {
    list.innerHTML = `<span class="select-session-empty">Haritadan bölgeye tıklayın…</span>`;
    return;
  }
  list.innerHTML = _sessionSelections
    .map(s => `<span class="region-chip">${escapeHtml(s.name || s.code)}</span>`)
    .join('');
}


/**
 * Grup renklerini kaldırıp yeniden uygular.
 * Choropleth aktifse choropleth renklerini korur.
 */
function reapplyGroupColors() {
  // "Bölge Grupları" katmanı kapalıysa grup renklerini gösterme
  // (choropleth seçilince grupların geri gelmesi bug'ını önler).
  const cb = document.getElementById('layer-groups');
  if (cb && !cb.checked) { clearAllGroupColors(); return; }
  clearAllGroupColors();
  for (const group of groups) {
    for (const region of (group.regions || [])) {
      forEachGroupTargetLayer(region.region_type, targetLayer => {
        targetLayer.eachLayer(layer => {
          if (layer._regionCode === region.region_code) {
            highlightGroupRegion(layer, group.color);
          }
        });
      });
    }
  }
}


function toggleGroupsLayer(visible) {
  if (visible) {
    reapplyGroupColors();
  } else {
    clearAllGroupColors();
  }
}


function clearAllGroupColors() {
  if (typeof clearGroupColors === 'function') clearGroupColors();
  for (const layerGroup of [countryRegionsLayer, areaRegionsLayer, subareaRegionsLayer]) {
    if (!layerGroup) continue;
    layerGroup.eachLayer(layer => {
      if (!layer._groupColor) return;
      delete layer._groupColor;
      if (typeof restoreRegionLayerStyle === 'function') {
        restoreRegionLayerStyle(layer, layer._regionKind);
      }
    });
  }
}


function forEachGroupTargetLayer(type, callback) {
  const normalized = normalizeGroupType(type);
  if (normalized === 'country') {
    if (countryRegionsLayer) callback(countryRegionsLayer);
  } else if (normalized === 'subregion') {
    if (subareaRegionsLayer) callback(subareaRegionsLayer);
    if (districtsLayer) callback(districtsLayer);
  } else {
    if (areaRegionsLayer) callback(areaRegionsLayer);
    if (provincesLayer) callback(provincesLayer);
  }
}


function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
