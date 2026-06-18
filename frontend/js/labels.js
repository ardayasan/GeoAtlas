/**
 * Özel etiket sistemi
 */

let labelsLayer = null;
let labelsData = [];
let _pickingLabel = false;


async function loadLabels() {
  try {
    labelsData = await apiFetch('/labels');
    renderLabelsList();
    if (document.getElementById('layer-labels').checked) {
      renderLabelsOnMap();
    }
  } catch (e) {
    console.warn('Etiketler yüklenemedi:', e.message);
  }
}


function renderLabelsList() {
  const container = document.getElementById('labels-list');
  if (!labelsData.length) {
    container.innerHTML = '<p class="empty-hint">Henüz etiket yok.</p>';
    return;
  }
  container.innerHTML = labelsData.map(l => `
    <div class="label-item" data-id="${l.id}">
      <div class="group-swatch" style="background:${l.color};border-radius:50%"></div>
      <div class="label-info">
        <div class="label-name">${l.name}</div>
        <div class="label-meta">${Number(l.latitude).toFixed(4)}, ${Number(l.longitude).toFixed(4)}</div>
      </div>
      <div class="item-actions">
        <button class="icon-btn" title="Haritada göster" onclick="flyToLabel(${l.latitude}, ${l.longitude})">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        </button>
        <button class="icon-btn danger" title="Sil" onclick="deleteLabel(${l.id})">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
        </button>
      </div>
    </div>
  `).join('');
}


/**
 * Etiket ikonunu icon_type'a göre üretir.
 * pin → damla şekli; star/circle/flag → renkli rozet içinde beyaz ikon.
 */
function makeLabelIcon(iconType, color) {
  if (!iconType || iconType === 'pin') return makePinIcon(color);
  const svg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="white">${labelIconSvg(iconType)}</svg>`;
  return makeDivIcon(svg, color, 28);
}


/**
 * Harita-seç modunda bir konum seçildiğinde çağrılır (hem boş alan hem
 * il/ilçe üzerine tıklamada). Koordinatı doldurur, önizlemeyi günceller,
 * etiket modalını geri açar.
 */
function pickLabelLocation(latlng) {
  window._labelPickerActive = false;
  document.getElementById('label-lat-input').value = latlng.lat.toFixed(6);
  document.getElementById('label-lon-input').value = latlng.lng.toFixed(6);
  updateLabelPreview();
  openModal('modal-label');
  showToast('Koordinat seçildi.', 'success', 1500);
}


function renderLabelsOnMap() {
  if (labelsLayer) {
    map.removeLayer(labelsLayer);
  }
  labelsLayer = L.layerGroup();

  for (const label of labelsData) {
    const icon = makeLabelIcon(label.icon_type, label.color);
    const marker = L.marker([label.latitude, label.longitude], { icon });
    marker.bindTooltip(label.name, { direction: 'top' });
    marker.bindPopup(`
      <div class="popup-title">${label.name}</div>
      ${label.description ? `<p style="font-size:13px;margin-top:6px">${label.description}</p>` : ''}
      <hr class="popup-divider"/>
      <div class="popup-row">
        <span class="popup-label">Konum</span>
        <span class="popup-value">${Number(label.latitude).toFixed(5)}, ${Number(label.longitude).toFixed(5)}</span>
      </div>
      <div class="popup-row">
        <span class="popup-label">Kaynak</span>
        <span class="popup-value">${label.source === 'excel_import' ? 'Excel' : 'Manuel'}</span>
      </div>
    `);
    labelsLayer.addLayer(marker);
  }

  labelsLayer.addTo(map);
}


function toggleLabelsLayer(visible) {
  if (visible) {
    if (!labelsLayer) renderLabelsOnMap();
    else labelsLayer.addTo(map);
  } else {
    if (labelsLayer) map.removeLayer(labelsLayer);
  }
}


function flyToLabel(lat, lon) {
  map.flyTo([lat, lon], 14, { duration: 1 });
}


async function saveLabel() {
  const name = document.getElementById('label-name-input').value.trim();
  const lat = parseFloat(document.getElementById('label-lat-input').value);
  const lon = parseFloat(document.getElementById('label-lon-input').value);
  const color = document.getElementById('label-color-input').value;
  const icon = document.getElementById('label-icon-input').value;
  const desc = document.getElementById('label-desc-input').value.trim();

  if (!name) { showToast('Etiket adı boş olamaz.', 'warn'); return; }
  if (isNaN(lat) || isNaN(lon)) { showToast('Geçerli koordinat giriniz.', 'warn'); return; }

  try {
    await apiFetch('/labels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, latitude: lat, longitude: lon, color, icon_type: icon, description: desc }),
    });
    closeModal('modal-label');
    clearLabelForm();
    showToast(`"${name}" etiketi eklendi.`, 'success');
    await loadLabels();
    if (document.getElementById('layer-labels').checked) {
      renderLabelsOnMap();
    }
  } catch (e) {
    showToast('Etiket kaydedilemedi: ' + e.message, 'error');
  }
}


async function deleteLabel(id) {
  const label = labelsData.find(l => l.id === id);
  if (!confirm(`"${label?.name || 'Etiket'}" silinsin mi?`)) return;
  try {
    await apiFetch(`/labels/${id}`, { method: 'DELETE' });
    labelsData = labelsData.filter(l => l.id !== id);
    renderLabelsList();
    renderLabelsOnMap();
    showToast('Etiket silindi.', 'success');
  } catch (e) {
    showToast('Silinemedi: ' + e.message, 'error');
  }
}


function clearLabelForm() {
  document.getElementById('label-name-input').value = '';
  document.getElementById('label-lat-input').value = '';
  document.getElementById('label-lon-input').value = '';
  document.getElementById('label-color-input').value = '#f43f5e';
  document.getElementById('label-desc-input').value = '';
  document.getElementById('label-icon-input').value = 'pin';
  // İkon seçici + renk presetleri sıfırla
  document.querySelectorAll('#label-icon-picker .icon-pick')
    .forEach(b => b.classList.toggle('active', b.dataset.icon === 'pin'));
  document.querySelectorAll('#label-color-presets .color-preset')
    .forEach(b => b.classList.toggle('active', b.dataset.color === '#f43f5e'));
  updateLabelPreview();
}


/** Modal içindeki ikon/renk/ad değiştikçe canlı pin önizlemesini günceller. */
function updateLabelPreview() {
  const name  = document.getElementById('label-name-input').value.trim() || 'Yeni Etiket';
  const color = document.getElementById('label-color-input').value;
  const icon  = document.getElementById('label-icon-input').value;
  const lat   = document.getElementById('label-lat-input').value;
  const lon   = document.getElementById('label-lon-input').value;

  const pin = document.getElementById('label-preview-pin');
  if (pin) {
    pin.style.setProperty('--c', color);
    pin.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="white">${labelIconSvg(icon)}</svg>`;
  }
  const nameEl = document.getElementById('label-preview-name');
  if (nameEl) nameEl.textContent = name;
  const coordEl = document.getElementById('label-preview-coord');
  if (coordEl) {
    coordEl.textContent = (lat && lon)
      ? `${Number(lat).toFixed(4)}, ${Number(lon).toFixed(4)}`
      : 'Konum seçilmedi';
  }
}


function labelIconSvg(icon) {
  const paths = {
    pin:    '<path d="M12 2C8 2 5 5 5 9c0 5 7 13 7 13s7-8 7-13c0-4-3-7-7-7z"/>',
    star:   '<polygon points="12,2 15,9 22,9.3 16.5,14 18.5,21 12,17 5.5,21 7.5,14 2,9.3 9,9"/>',
    circle: '<circle cx="12" cy="12" r="8"/>',
    flag:   '<path d="M6 2v20M6 3h12l-2.5 3.5L18 10H6z"/>',
  };
  return paths[icon] || paths.pin;
}


/** Etiket modal'ındaki ikon seçici, renk presetleri ve haritadan-seç düğmesini bağlar. */
function initLabelModal() {
  document.querySelectorAll('#label-icon-picker .icon-pick').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#label-icon-picker .icon-pick').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('label-icon-input').value = btn.dataset.icon;
      updateLabelPreview();
    });
  });

  document.querySelectorAll('#label-color-presets .color-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#label-color-presets .color-preset').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('label-color-input').value = btn.dataset.color;
      updateLabelPreview();
    });
  });

  document.getElementById('label-color-input').addEventListener('input', () => {
    document.querySelectorAll('#label-color-presets .color-preset').forEach(b => b.classList.remove('active'));
    updateLabelPreview();
  });

  document.getElementById('label-name-input').addEventListener('input', updateLabelPreview);

  // Haritadan seç: modal'ı kapat, harita tıklamasını bekle (app.js map click yeniden açar)
  document.getElementById('btn-pick-on-map').addEventListener('click', () => {
    closeModal('modal-label');
    window._labelPickerActive = true;
    showToast('Haritada bir konuma tıklayın.', 'info', 3000);
  });
}


/**
 * Haritaya tıklayarak etiket koordinatını seç.
 */
function startLabelPicking() {
  _pickingLabel = true;
  map.getContainer().style.cursor = 'crosshair';
}

function stopLabelPicking() {
  _pickingLabel = false;
  map.getContainer().style.cursor = '';
}
