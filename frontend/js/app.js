/**
 * Ana uygulama başlatıcı — tüm modülleri bağlar
 */

document.addEventListener('DOMContentLoaded', async () => {

  // ── Haritayı başlat ──────────────────────────────────────────
  initMap();

  // ── Sınırları yükle: Avrupa NUTS varsa onu, yoksa mevcut Türkiye akışını kullan
  let usingRegions = false;
  if (typeof initRegions === 'function') {
    showLoading('Bölge sınırları yükleniyor...');
    usingRegions = await initRegions();
    hideLoading();
  }
  if (usingRegions) {
    document.querySelectorAll('.region-only').forEach(el => el.classList.remove('hidden'));

    await toggleCountryRegionsLayer(document.getElementById('layer-countries')?.checked);
  } else {
    const provinceCb = document.getElementById('layer-provinces');
    if (provinceCb) provinceCb.checked = true;
    showLoading('İl sınırları yükleniyor...');
    await toggleProvinceLayer(true);
    hideLoading();
  }

  // ── Arka plan verileri ───────────────────────────────────────
  loadGroups();
  loadLabels();
  initPoiControls(usingRegions);
  refreshPoiStatus();

  // ── Rail sidebar panel geçişi ────────────────────────────────
  document.querySelectorAll('.rail-btn').forEach(btn => {
    btn.addEventListener('click', () => switchPanel(btn.dataset.panel));
  });

  // ── Katman checkbox'ları ─────────────────────────────────────
  // Sınır katmanları mutual exclusion kuralları:
  //   Avrupa ülke (layer-countries) ↔ Avrupa bölge (layer-regions-l3) birbirini kapatır
  //   Avrupa ülke (layer-countries) ↔ Türkiye il/ilçe birbirini kapatır
  //   Türkiye içinde: il ↔ ilçe birbirini kapatır
  //   Avrupa bölge (layer-regions-l3) + Türkiye katmanları aynı anda açık olabilir
  document.getElementById('layer-countries')?.addEventListener('change', async function () {
    if (this.checked) {
      await toggleAreaRegionsLayer(false);  setLayerCheckbox('layer-regions-l3', false);
      await toggleProvinceLayer(false);     setLayerCheckbox('layer-provinces', false);
      await toggleDistrictLayer(false);     setLayerCheckbox('layer-districts', false);
    }
    await toggleCountryRegionsLayer(this.checked);
  });

  document.getElementById('layer-regions-l3')?.addEventListener('change', async function () {
    if (this.checked) {
      await toggleCountryRegionsLayer(false); setLayerCheckbox('layer-countries', false);
    }
    await toggleAreaRegionsLayer(this.checked);
  });

  document.getElementById('layer-provinces')?.addEventListener('change', async function () {
    if (this.checked) {
      await toggleDistrictLayer(false);        setLayerCheckbox('layer-districts', false);
      await toggleCountryRegionsLayer(false);  setLayerCheckbox('layer-countries', false);
    }
    await toggleProvinceLayer(this.checked);
  });

  document.getElementById('layer-districts')?.addEventListener('change', async function () {
    if (this.checked) {
      await toggleProvinceLayer(false);        setLayerCheckbox('layer-provinces', false);
      await toggleCountryRegionsLayer(false);  setLayerCheckbox('layer-countries', false);
    }
    await toggleDistrictLayer(this.checked);
  });
  bindLayerCheckbox('layer-mosques',       (v) => togglePoiLayer('mosques', v));
  bindLayerCheckbox('layer-churches',      (v) => togglePoiLayer('churches', v));
  bindLayerCheckbox('layer-worship-other', (v) => togglePoiLayer('worship_other', v));
  bindLayerCheckbox('layer-schools',       (v) => togglePoiLayer('schools', v));
  bindLayerCheckbox('layer-universities',  (v) => togglePoiLayer('universities', v));
  bindLayerCheckbox('layer-kindergartens', (v) => togglePoiLayer('kindergartens', v));
  bindLayerCheckbox('layer-labels',        (v) => toggleLabelsLayer(v));
  bindLayerCheckbox('layer-groups',        (v) => toggleGroupsLayer(v));

  // ── Tile switcher ────────────────────────────────────────────
  document.querySelectorAll('.tile-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tile-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      switchTileLayer(btn.dataset.tile);
    });
  });

  // ── Choropleth metrik chip'leri ─────────────────────────────
  document.querySelectorAll('#choropleth-chips .metric-chip').forEach(chip => {
    chip.addEventListener('click', async () => {
      const metric = chip.dataset.metric;
      const isActive = chip.classList.contains('active');

      // Tüm chip'leri pasifleştir (tek seçim)
      document.querySelectorAll('#choropleth-chips .metric-chip')
        .forEach(c => c.classList.remove('active'));

      if (isActive) {
        // Aynı chip'e tekrar tıklandı → kapat (her iki katmanı da temizle)
        await applyChoropleth('');
        if (typeof applyRegionsChoropleth === 'function') {
          await applyRegionsChoropleth('');
        }
        return;
      }

      chip.classList.add('active');

      const trChecked = document.getElementById('layer-provinces')?.checked || document.getElementById('layer-districts')?.checked;
      const euChecked = document.getElementById('layer-countries')?.checked || document.getElementById('layer-regions-l3')?.checked || document.getElementById('layer-regions-l4')?.checked;

      if (!trChecked && !euChecked) {
        showToast('Renklendirme için lütfen sol menüden Türkiye veya Avrupa sınır katmanlarından birini açın.', 'warn');
        chip.classList.remove('active');
        return;
      }

      // Sadece aktif olan katmanlar için renklendirmeyi çağır
      // (Eğer fonksiyonlara '' gönderirsek, global değişkeni sıfırlayıp efsaneyi (legend) gizliyorlardı!)
      if (trChecked) {
        await applyChoropleth(metric);
      }
      if (euChecked && typeof applyRegionsChoropleth === 'function') {
        await applyRegionsChoropleth(metric);
      }
    });
  });

  // ── Sidebar toggle (panel area collapse) ──────────────────────
  document.getElementById('btn-toggle-sidebar').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('collapsed');
  });

  // ── Excel Modal ───────────────────────────────────────────────
  document.getElementById('btn-upload-excel').addEventListener('click', () => {
    goToStep1();
    openModal('modal-excel');
  });
  initExcelUpload();

  // ── Grup Modal ────────────────────────────────────────────────
  document.getElementById('btn-new-group').addEventListener('click', (e) => {
    e.stopPropagation();
    document.getElementById('group-name-input').value = '';
    document.getElementById('group-color-input').value = '#7c3aed';
    document.getElementById('group-color-preview').style.background = '#7c3aed';
    // Tip seçiciyi varsayılana (Bölge) döndür
    document.querySelectorAll('#group-type-seg .seg-btn')
      .forEach(b => b.classList.toggle('active', b.dataset.type === 'region'));
    openModal('modal-group');
  });
  document.getElementById('btn-save-group').addEventListener('click', createGroup);
  document.getElementById('group-color-input').addEventListener('input', (e) => {
    document.getElementById('group-color-preview').style.background = e.target.value;
  });

  // Grup türü segmented kontrolü
  document.querySelectorAll('#group-type-seg .seg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#group-type-seg .seg-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  // ── Seçim modu çıkış ─────────────────────────────────────────
  document.getElementById('btn-exit-select-mode').addEventListener('click', exitSelectMode);

  // ── Etiket Modal ──────────────────────────────────────────────
  document.getElementById('btn-new-label').addEventListener('click', (e) => {
    e.stopPropagation();
    clearLabelForm();
    openModal('modal-label');
  });
  document.getElementById('btn-save-label').addEventListener('click', saveLabel);
  initLabelModal();

  // Haritadan konum seçme (boş alana / denize tıklama).
  // İl/ilçe üzerine tıklama boundaries.js'te ele alınır.
  map.on('click', (e) => {
    if (window._labelPickerActive) pickLabelLocation(e.latlng);
  });

  // ── Floating Assistant Bubble ─────────────────────────────────
  const bubbleBtn = document.getElementById('assistant-bubble-btn');
  const chatWindow = document.getElementById('assistant-chat-window');
  const closeBtn = document.getElementById('btn-assistant-close');

  bubbleBtn?.addEventListener('click', () => {
    const isOpen = !chatWindow.classList.contains('hidden');
    if (isOpen) {
      chatWindow.classList.add('hidden');
      bubbleBtn.classList.remove('open');
    } else {
      chatWindow.classList.remove('hidden');
      bubbleBtn.classList.add('open');
      document.getElementById('assistant-text')?.focus();
    }
  });

  closeBtn?.addEventListener('click', () => {
    chatWindow.classList.add('hidden');
    bubbleBtn.classList.remove('open');
  });

  // ── Modal kapatma ─────────────────────────────────────────────
  document.querySelectorAll('.modal-close, [data-close-modal]').forEach(el => {
    el.addEventListener('click', () => {
      const modalId = el.dataset.closeModal || el.dataset.modal;
      if (modalId) closeModal(modalId);
    });
  });

  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });

});


// ── Rail panel switcher ───────────────────────────────────────────
function switchPanel(panelId) {
  document.querySelectorAll('.rail-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.panel === panelId);
  });
  document.querySelectorAll('.panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `panel-${panelId}`);
  });
  // Make sure sidebar is not collapsed when a panel is activated
  document.getElementById('sidebar').classList.remove('collapsed');
}


// ── Yardımcı: checkbox bağla ─────────────────────────────────────
function bindLayerCheckbox(id, callback) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('change', () => callback(el.checked));
}

// ── Modal aç/kapat ───────────────────────────────────────────────
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('hidden');
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}
