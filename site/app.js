let seals = [];
const q = document.getElementById('q');
const motifSel = document.getElementById('motif');
const materialSel = document.getElementById('material');
const results = document.getElementById('results');
const count = document.getElementById('count');

fetch('../data/seals.json')
  .then(r => r.json())
  .then(d => { seals = d; render(); })
  .catch(() => {
    // fallback when opened via file:// — try relative path from site root
    fetch('data/seals.json').then(r => r.json()).then(d => { seals = d; render(); });
  });

function matches(s) {
  const query = q.value.trim().toLowerCase();
  const hay = [s.id, s.find_no, s.site, s.mound, s.motif, s.material, s.description, s.source]
    .filter(Boolean).join(' ').toLowerCase();
  if (query && !hay.includes(query)) return false;
  if (motifSel.value && s.motif !== motifSel.value) return false;
  if (materialSel.value && !(s.material || '').includes(materialSel.value)) return false;
  return true;
}

function card(s) {
  return `<article class="card">
    <div class="card-head"><span class="id">${esc(s.id)}</span><span class="motif-tag">${esc(s.motif || '')}</span></div>
    <h2>${esc(s.site)} ${esc(s.find_no && s.find_no !== '—' ? '· ' + s.find_no : '')}</h2>
    <p class="desc">${esc(s.description || '')}</p>
    <dl>
      ${s.material ? `<div><dt>Material</dt><dd>${esc(s.material)}</dd></div>` : ''}
      ${s.size_in ? `<div><dt>Size (in)</dt><dd>${esc(s.size_in)}</dd></div>` : ''}
      ${s.mound ? `<div><dt>Mound</dt><dd>${esc(s.mound)}</dd></div>` : ''}
      ${s.type ? `<div><dt>Type</dt><dd>${esc(s.type)}</dd></div>` : ''}
      ${s.plate ? `<div><dt>Plate</dt><dd>${esc(s.plate)}</dd></div>` : ''}
    </dl>
    <p class="source">Source: ${esc(s.source || '')}</p>
  </article>`;
}

function esc(x){ return String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function render() {
  const list = seals.filter(matches);
  count.textContent = `${list.length} of ${seals.length} seals`;
  results.innerHTML = list.map(card).join('') || '<p class="empty">No seals match. Try a different search.</p>';
}

[q, motifSel, materialSel].forEach(el => el.addEventListener('input', render));
