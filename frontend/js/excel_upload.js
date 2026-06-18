/**
 * Excel yükleme UI — 2 adımlı: kapsam seç → dosya yükle
 */

let _selectedExcelFile = null;
let _uploadScope = null;

const SCOPE_INFO = {
  turkey: `<strong>Sheet:</strong> <b>Nufus_Il</b> (iller) + <b>Nufus_Ilce</b> (ilçeler)<br>
<strong>Zorunlu:</strong> il için <b>il_adi</b> + <b>toplam_nufus</b>; ilçe için <b>il_adi</b> + <b>ilce_adi</b> + <b>toplam_nufus</b><br>
<strong>Opsiyonel:</strong> erkek_nufus, kadin_nufus, medyan_yas, nufus_yogunluk, nufus_artis_hizi, yas_0_14/15_64/65_ust<br>
Yükleme <strong>UPSERT</strong>'tir — yalnızca dosyadaki satırlar güncellenir.`,

  europe: `<strong>Sheet:</strong> <b>Region_Stats</b><br>
<strong>Zorunlu:</strong> <b>code</b> (NUTS kodu, örn. DE / TR621), <b>year</b><br>
<strong>Göstergeler (isteğe bağlı):</strong> population, population_m, population_f, density, median_age, growth_rate, erkek_oran, kadin_oran<br>
Yükleme <strong>UPSERT</strong>'tir — mevcut değerlerin üzerine yazar.`,

  labels: `<strong>Sheet:</strong> <b>Disaridan_Etiketler</b><br>
<strong>Zorunlu:</strong> <b>etiket_adi</b>, <b>enlem</b>, <b>boylam</b><br>
<strong>Opsiyonel:</strong> renk (#hex), aciklama, ikon (pin / star / dot)<br>
Her satır haritaya yeni bir etiket olarak eklenir.`,
};

const SCOPE_SUBTITLE = {
  turkey: 'Türkiye — İl ve ilçe nüfus verileri',
  europe: 'Avrupa — Ülke ve bölge istatistikleri',
  labels: 'Etiketler — Toplu konum yükle',
};


function initExcelUpload() {
  // Kapsam kartları
  document.querySelectorAll('.scope-card').forEach(card => {
    card.addEventListener('click', () => selectScope(card.dataset.scope));
  });

  // Geri butonu
  document.getElementById('btn-excel-back').addEventListener('click', goToStep1);

  // Drop zone
  const dropArea = document.getElementById('excel-drop-area');
  const fileInput = document.getElementById('excel-file-input');

  document.getElementById('btn-select-excel-file').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => { if (e.target.files[0]) selectFile(e.target.files[0]); });

  dropArea.addEventListener('dragover', (e) => { e.preventDefault(); dropArea.classList.add('drag-over'); });
  dropArea.addEventListener('dragleave', () => dropArea.classList.remove('drag-over'));
  dropArea.addEventListener('drop', (e) => {
    e.preventDefault();
    dropArea.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) selectFile(e.dataTransfer.files[0]);
  });

  document.getElementById('btn-do-upload-excel').addEventListener('click', doUpload);
}


function selectScope(scope) {
  _uploadScope = scope;
  _selectedExcelFile = null;
  document.getElementById('selected-file-name').textContent = '';
  document.getElementById('excel-file-input').value = '';
  document.getElementById('excel-scope-info').innerHTML = SCOPE_INFO[scope] || '';
  document.getElementById('excel-modal-subtitle').textContent = SCOPE_SUBTITLE[scope] || '';
  document.getElementById('excel-upload-result').classList.add('hidden');
  document.getElementById('excel-upload-result').innerHTML = '';

  document.getElementById('excel-step-1').classList.add('hidden');
  document.getElementById('excel-step-2').classList.remove('hidden');
  document.getElementById('excel-footer-1').classList.add('hidden');
  document.getElementById('excel-footer-2').classList.remove('hidden');
}


function goToStep1() {
  _uploadScope = null;
  _selectedExcelFile = null;
  document.getElementById('excel-file-input').value = '';
  document.getElementById('selected-file-name').textContent = '';
  document.getElementById('excel-modal-subtitle').textContent = 'Veri türünü seçin';
  document.getElementById('excel-upload-result').classList.add('hidden');
  document.getElementById('excel-upload-result').innerHTML = '';

  document.getElementById('excel-step-1').classList.remove('hidden');
  document.getElementById('excel-step-2').classList.add('hidden');
  document.getElementById('excel-footer-1').classList.remove('hidden');
  document.getElementById('excel-footer-2').classList.add('hidden');
}


function selectFile(file) {
  _selectedExcelFile = file;
  document.getElementById('selected-file-name').textContent = file.name;
  document.getElementById('excel-upload-result').classList.add('hidden');
  document.getElementById('excel-upload-result').innerHTML = '';
}


async function doUpload() {
  if (!_selectedExcelFile) {
    showToast('Lütfen önce bir Excel dosyası seçin.', 'warn');
    return;
  }
  if (!_uploadScope) {
    showToast('Kapsam seçilmedi.', 'warn');
    return;
  }

  const resultEl = document.getElementById('excel-upload-result');
  resultEl.className = 'upload-result-card';
  resultEl.innerHTML = '<div class="upload-result-loading">Yükleniyor…</div>';
  resultEl.classList.remove('hidden');

  const uploadBtn = document.getElementById('btn-do-upload-excel');
  uploadBtn.disabled = true;

  const formData = new FormData();
  formData.append('file', _selectedExcelFile);

  try {
    const res = await fetch(`${Config.API_BASE}/excel/upload?scope=${_uploadScope}`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || 'Yükleme hatası');

    resultEl.innerHTML = buildResultHTML(data);

    // Choropleth yenile
    if (_uploadScope === 'turkey') {
      Object.keys(demoCache).forEach(k => delete demoCache[k]);
      await refreshChoroplethIfActive();
    } else if (_uploadScope === 'europe') {
      if (typeof refreshRegionsChoroplethIfActive === 'function')
        await refreshRegionsChoroplethIfActive();
    } else if (_uploadScope === 'labels') {
      if (typeof loadLabels === 'function') loadLabels();
    }

    showToast(uploadSuccessMessage(data), 'success');

  } catch (e) {
    resultEl.innerHTML = `<div class="result-row result-error"><span class="result-icon">✕</span>${e.message}</div>`;
    showToast('Yükleme hatası: ' + e.message, 'error');
  } finally {
    uploadBtn.disabled = false;
  }
}


function buildResultHTML(data) {
  const rows = [];

  if (data.scope === 'turkey') {
    if (data.provinces_imported)
      rows.push(row('ok', `${data.provinces_imported} il güncellendi`));
    if (data.districts_imported)
      rows.push(row('ok', `${data.districts_imported} ilçe güncellendi`));
    if (!data.provinces_imported && !data.districts_imported)
      rows.push(row('warn', 'Eşleşen kayıt bulunamadı'));
  } else if (data.scope === 'europe') {
    if (data.regions_imported)
      rows.push(row('ok', `${data.regions_imported} bölge güncellendi (${data.stats_imported} gösterge)`));
    if (!data.regions_imported)
      rows.push(row('warn', 'Eşleşen bölge bulunamadı'));
  } else if (data.scope === 'labels') {
    if (data.labels_imported)
      rows.push(row('ok', `${data.labels_imported} etiket eklendi`));
    if (!data.labels_imported)
      rows.push(row('warn', 'Eklenecek etiket bulunamadı'));
  }

  const unmatched = data.unmatched || [];
  if (unmatched.length) {
    const preview = unmatched.slice(0, 5).join(', ') + (unmatched.length > 5 ? ` +${unmatched.length - 5} daha` : '');
    rows.push(row('warn', `${unmatched.length} satır eşleşmedi: ${preview}`));
  }

  const errors = data.errors || [];
  if (errors.length) {
    rows.push(row('error', `${errors.length} hata: ${errors[0]}`));
  }

  return rows.join('');
}


function row(type, text) {
  const icons = { ok: '✓', warn: '!', error: '✕' };
  return `<div class="result-row result-${type}"><span class="result-icon">${icons[type]}</span><span>${text}</span></div>`;
}


function uploadSuccessMessage(data) {
  if (data.scope === 'turkey')
    return `${data.provinces_imported} il, ${data.districts_imported} ilçe yüklendi.`;
  if (data.scope === 'europe')
    return `${data.regions_imported} bölge güncellendi.`;
  if (data.scope === 'labels')
    return `${data.labels_imported} etiket eklendi.`;
  return 'Yükleme tamamlandı.';
}
