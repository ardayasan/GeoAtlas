/**
 * Demografi Asistanı — yerel LLM (Ollama) sohbet paneli.
 * /api/chat'e gönderir, cevabı gösterir ve map_action'ı haritaya uygular.
 */

const assistantHistory = [];      // [{role, content}]
let assistantBusy = false;
let _assistantHi = [];            // geçici vurgulanan katmanlar

function initAssistant() {
  const form = document.getElementById('assistant-form');
  const clearBtn = document.getElementById('btn-assistant-clear');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const input = document.getElementById('assistant-text');
    const text = input.value.trim();
    if (text) { input.value = ''; sendAssistantMessage(text); }
  });
  if (clearBtn) clearBtn.addEventListener('click', clearAssistant);
}

function clearAssistant() {
  assistantHistory.length = 0;
  const box = document.getElementById('assistant-messages');
  box.querySelectorAll('.assistant-msg:not(:first-child)').forEach(n => n.remove());
  clearAssistantHighlights();
}

function _addMsg(role, html) {
  const box = document.getElementById('assistant-messages');
  const wrap = document.createElement('div');
  wrap.className = `assistant-msg ${role === 'user' ? 'user' : 'bot'}`;
  const bubble = document.createElement('div');
  bubble.className = 'assistant-bubble';
  bubble.innerHTML = html;
  wrap.appendChild(bubble);
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
  return wrap;
}

function _escape(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Çok basit metin biçimleme: satır sonları + **kalın**
function _format(text) {
  let t = _escape(text);
  t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  return t.replace(/\n/g, '<br>');
}


async function sendAssistantMessage(text) {
  if (assistantBusy) return;
  assistantBusy = true;
  _addMsg('user', _escape(text));
  assistantHistory.push({ role: 'user', content: text });

  const typing = _addMsg('bot', '<span class="assistant-typing"><i></i><i></i><i></i></span>');

  try {
    const res = await fetch(Config.API_BASE + '/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: assistantHistory }),
    });
    const data = await res.json();
    typing.remove();

    if (!res.ok) {
      _addMsg('bot', `<span class="assistant-error">${_escape(data.detail || 'Asistan hatası')}</span>`);
      return;
    }
    _addMsg('bot', _format(data.answer));
    assistantHistory.push({ role: 'assistant', content: data.answer });
    if (data.map_action) applyMapAction(data.map_action);
  } catch (e) {
    typing.remove();
    _addMsg('bot', `<span class="assistant-error">Bağlantı hatası: ${_escape(e.message)}</span>`);
  } finally {
    assistantBusy = false;
  }
}


// ── Harita aksiyonu ────────────────────────────────────────────────────────
function _layersByCodes(codes) {
  const want = new Set(codes.map(String));
  const out = [];
  for (const lyr of [typeof provincesLayer !== 'undefined' ? provincesLayer : null,
                     typeof districtsLayer !== 'undefined' ? districtsLayer : null,
                     typeof window._regionsLayer !== 'undefined' ? window._regionsLayer : null]) {
    if (!lyr) continue;
    lyr.eachLayer(l => { if (want.has(String(l._regionCode))) out.push(l); });
  }
  return out;
}

function clearAssistantHighlights() {
  for (const l of _assistantHi) {
    try { l.setStyle({ weight: 1.5, color: (Config.COLORS?.province?.border) || '#1d4ed8' }); } catch (e) {}
  }
  _assistantHi = [];
}

async function _ensureProvinceLayer() {
  const cb = document.getElementById('layer-provinces');
  if (cb && !cb.checked && typeof toggleProvinceLayer === 'function') {
    cb.checked = true;
    await toggleProvinceLayer(true);
  }
}

async function _ensureDistrictLayer() {
  const cb = document.getElementById('layer-districts');
  if (cb && !cb.checked && !cb.disabled && typeof toggleDistrictLayer === 'function') {
    cb.checked = true;
    await toggleDistrictLayer(true);
  }
}

async function applyMapAction(action) {
  if (!action || typeof map === 'undefined') return;

  if (action.type === 'show_poi' && action.category) {
    if (action.country && typeof activePoiCountry !== 'undefined' && action.country !== activePoiCountry) {
      const select = document.getElementById('poi-country-select');
      if (select) {
        select.value = action.country;
        if (typeof setPoiCheckbox === 'function') setPoiCheckbox(action.category, true);
        select.dispatchEvent(new Event('change'));
        return;
      }
    } else {
      if (typeof setPoiCheckbox === 'function') setPoiCheckbox(action.category, true);
      if (typeof togglePoiLayer === 'function') togglePoiLayer(action.category, true);
      return;
    }
  }

  const codes = (action.codes || action.highlight || []).map(String);
  const hasDistrict = codes.some(c => c.includes('.'));

  await _ensureProvinceLayer();
  if (hasDistrict) await _ensureDistrictLayer();

  // Choropleth: ilgili chip'i aktifleştir (mevcut app.js wiring'i tetikler)
  if (action.type === 'choropleth' && action.metric) {
    const chip = document.querySelector(`#choropleth-chips .metric-chip[data-metric="${action.metric}"]`);
    if (chip && !chip.classList.contains('active')) chip.click();
  }

  clearAssistantHighlights();
  const layers = _layersByCodes(codes);
  if (!layers.length) return;

  // Vurgu (kenarlık) — dolguya dokunmaz, choropleth korunur
  for (const l of layers) {
    try { l.setStyle({ weight: 4, color: '#1d4ed8' }); l.bringToFront(); _assistantHi.push(l); } catch (e) {}
  }

  // Görünüm: tek bölge → odak; çoklu → hepsini sığdır
  try {
    const group = L.featureGroup(layers);
    const b = group.getBounds();
    if (b.isValid()) map.flyToBounds(b, { maxZoom: action.type === 'focus' ? 9 : 7, padding: [40, 40] });
  } catch (e) {}
}


document.addEventListener('DOMContentLoaded', initAssistant);
