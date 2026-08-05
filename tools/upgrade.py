from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8-sig')

s = s.replace(
    'smoothWheel: true, smoothTouch: true, touchMultiplier: 1.5, infinite: false,',
    'smoothWheel: true, smoothTouch: false, touchMultiplier: 1.15, infinite: false,'
)

start = s.index('/* ===== 2. CANVAS FRAME PLAYER ===== */')
end = s.index('/* ===== 3. SCROLL ENGINE ===== */')
frame_patch = r'''/* ===== 2. CANVAS FRAME PLAYER — progressive, anti-flash ===== */
const canvas = document.getElementById('frame-canvas');
const ctx = canvas.getContext('2d', { alpha:false, desynchronized:true });
const coarsePointer = matchMedia('(pointer:coarse)').matches;
const frames = new Array(TOTAL_FRAMES).fill(null);
const loadingFrames = new Map();
let currentFrameIndex = 0;
let lastGoodImage = null;
let lastGoodIndex = -1;
let loaderClosed = false;
let scrollStarted = false;
let activeLoads = 0;
const MAX_LOADS = coarsePointer ? 3 : 5;
const INITIAL_READY = coarsePointer ? 10 : 14;
const frameQueue = [];

const loaderFill = document.getElementById('loader-fill');
const loaderPercent = document.getElementById('loader-percent');
const loader = document.getElementById('loader');

function pad(n) { return String(n).padStart(3, '0'); }
function frameUrl(index) { return FRAMES_DIR + pad(index + 1) + '.webp'; }

function resizeCanvas() {
  const dpr = Math.min(coarsePointer ? 1.25 : 1.75, window.devicePixelRatio || 1);
  const width = Math.max(1, Math.round(innerWidth * dpr));
  const height = Math.max(1, Math.round(innerHeight * dpr));
  if (canvas.width === width && canvas.height === height) return;
  canvas.width = width;
  canvas.height = height;
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  drawFrame(currentFrameIndex, true);
}

function nearestLoaded(index) {
  for (let d = 0; d < TOTAL_FRAMES; d++) {
    const before = index - d;
    const after = index + d;
    if (before >= 0 && frames[before]) return before;
    if (after < TOTAL_FRAMES && frames[after]) return after;
  }
  return -1;
}

function paintFrame(image, index) {
  const iw = image.naturalWidth || image.width;
  const ih = image.naturalHeight || image.height;
  if (!canvas.width || !canvas.height || !iw || !ih) return false;
  const scale = Math.max(canvas.width / iw, canvas.height / ih);
  const width = iw * scale;
  const height = ih * scale;
  ctx.drawImage(image, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
  lastGoodImage = image;
  lastGoodIndex = index;
  return true;
}

function drawFrame(index, force = false) {
  index = Math.max(0, Math.min(TOTAL_FRAMES - 1, index | 0));
  if (!force && index === currentFrameIndex && lastGoodImage) return;
  currentFrameIndex = index;
  let image = frames[index];
  let imageIndex = index;
  if (!image) {
    const nearest = nearestLoaded(index);
    if (nearest >= 0) {
      image = frames[nearest];
      imageIndex = nearest;
    }
  }
  if (!image) {
    image = lastGoodImage;
    imageIndex = lastGoodIndex;
  }
  if (image) {
    try {
      if (paintFrame(image, imageIndex)) return;
    } catch (_) {}
  }
  if (!lastGoodImage) {
    ctx.fillStyle = '#070710';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
}

function closeLoader() {
  if (loaderClosed) return;
  loaderClosed = true;
  loader.classList.add('hidden');
  drawFrame(0, true);
  if (!scrollStarted) {
    scrollStarted = true;
    initScrollEngine();
  }
}

function updateLoader() {
  const ready = frames.slice(0, INITIAL_READY).filter(Boolean).length;
  const percent = Math.min(100, Math.round(ready / INITIAL_READY * 100));
  loaderFill.style.width = percent + '%';
  loaderPercent.textContent = percent + '%';
  if (ready >= INITIAL_READY) setTimeout(closeLoader, 120);
}

function enqueueFrame(index, priority = 0) {
  if (index < 0 || index >= TOTAL_FRAMES || frames[index] || loadingFrames.has(index)) return;
  if (!frameQueue.some(item => item.index === index)) frameQueue.push({ index, priority });
  frameQueue.sort((a, b) => b.priority - a.priority);
  pumpQueue();
}

function pumpQueue() {
  while (activeLoads < MAX_LOADS && frameQueue.length) {
    const { index } = frameQueue.shift();
    if (frames[index] || loadingFrames.has(index)) continue;
    activeLoads++;
    const image = new Image();
    image.decoding = 'async';
    loadingFrames.set(index, image);
    image.onload = async () => {
      try { if (image.decode) await image.decode(); } catch (_) {}
      frames[index] = image;
      loadingFrames.delete(index);
      activeLoads--;
      if (index === 0 || Math.abs(index - currentFrameIndex) <= 2) drawFrame(currentFrameIndex, true);
      updateLoader();
      pumpQueue();
    };
    image.onerror = () => {
      loadingFrames.delete(index);
      activeLoads--;
      pumpQueue();
      if (index < INITIAL_READY) setTimeout(() => enqueueFrame(index, 120), 1200);
    };
    image.src = frameUrl(index);
  }
}

function prioritizeAround(index) {
  enqueueFrame(index, 300);
  for (let distance = 1; distance <= 10; distance++) {
    enqueueFrame(index + distance, 250 - distance);
    enqueueFrame(index - distance, 245 - distance);
  }
}

function preloadFrames() {
  resizeCanvas();
  enqueueFrame(0, 1000);
  for (let index = 1; index < INITIAL_READY; index++) enqueueFrame(index, 900 - index);
  setTimeout(closeLoader, 8000);
  setTimeout(() => {
    for (let index = INITIAL_READY; index < TOTAL_FRAMES; index++) enqueueFrame(index, 10);
  }, 700);
}

let resizeTimer;
addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    resizeCanvas();
    drawFrame(currentFrameIndex, true);
    ScrollTrigger.refresh();
  }, 160);
}, { passive:true });

'''
s = s[:start] + frame_patch + s[end:]

s = s.replace(
    "drawFrame(fi);\n      scrollbarFill.style.height = (p * 100) + '%';",
    "prioritizeAround(fi);\n      drawFrame(fi);\n      scrollbarFill.style.height = (p * 100) + '%';"
)

if 'project-type-selector' not in s:
    service_html = '''<div class="project-type-selector" data-reveal aria-label="Tipo de proyecto">
        <button type="button" class="project-type active" data-project="vivienda" data-factor="1">Vivienda</button>
        <button type="button" class="project-type" data-project="ampliacion" data-factor="0.92">Ampliación</button>
        <button type="button" class="project-type" data-project="quincho" data-factor="0.78">Quincho</button>
        <button type="button" class="project-type" data-project="terraza" data-factor="0.58">Terraza</button>
      </div>
      <div class="calc-live-summary" data-reveal>
        <span>Proyecto seleccionado</span><strong id="project-summary">Vivienda · 100 m² · Intermedio</strong>
      </div>
      '''
    s = s.replace('<div class="calc-selector" data-reveal>', service_html + '<div class="calc-selector" data-reveal>', 1)

if '.project-type-selector{' not in s:
    css = '''
.project-type-selector{display:grid;grid-template-columns:repeat(4,1fr);gap:.55rem;max-width:680px;margin:1rem auto 0}
.project-type{border:1px solid var(--line);background:rgba(7,7,16,.76);color:var(--muted);padding:.8rem .45rem;border-radius:6px;font:600 .62rem var(--fb);letter-spacing:.12em;text-transform:uppercase;transition:.25s ease}
.project-type:hover{border-color:var(--accentdim);color:var(--fg)}
.project-type.active{background:var(--accent);border-color:var(--accent);color:var(--bg);box-shadow:0 8px 24px rgba(201,169,110,.2)}
.calc-live-summary{max-width:680px;margin:.8rem auto 0;padding:.7rem 1rem;border:1px solid var(--line);background:rgba(7,7,16,.58);display:flex;align-items:center;justify-content:space-between;gap:1rem;border-radius:6px}
.calc-live-summary span{font-size:.55rem;letter-spacing:.16em;text-transform:uppercase;color:var(--muted2)}
.calc-live-summary strong{font-size:.72rem;color:var(--accent);text-align:right}
@media(max-width:640px){.project-type-selector{grid-template-columns:repeat(2,1fr)}.calc-live-summary{align-items:flex-start;flex-direction:column}.calc-live-summary strong{text-align:left}}
'''
    s = s.replace('</style>', css + '\n</style>', 1)

if 'Calculator project types' not in s:
    calc_patch = r'''
/* Calculator project types */
const baseTierPrices = Object.fromEntries(Object.entries(tierData).map(([key,value]) => [key, { perm2:value.perm2, ufperm2:value.ufperm2 }]));
let selectedProjectLabel = 'Vivienda';
let selectedFactor = 1;
const projectSummary = document.getElementById('project-summary');

function updateProjectSummary(){
  const m2 = Math.max(40, Math.min(500, parseFloat(m2Input.value) || 100));
  const tierName = tierData[selectedTier]?.name || 'Intermedio';
  if(projectSummary) projectSummary.textContent = `${selectedProjectLabel} · ${m2} m² · ${tierName}`;
}

function applyProjectFactor(){
  Object.entries(tierData).forEach(([key,value]) => {
    value.perm2 = Math.round(baseTierPrices[key].perm2 * selectedFactor / 10000) * 10000;
    value.ufperm2 = Math.round(baseTierPrices[key].ufperm2 * selectedFactor * 10) / 10;
    const card = document.querySelector(`.tier-card[data-tier="${key}"]`);
    if(card){
      const price = card.querySelector('.tier-price span:nth-child(2)');
      const uf = card.querySelector('.tier-uf');
      if(price) price.textContent = value.perm2.toLocaleString('es-CL');
      if(uf) uf.textContent = value.ufperm2.toLocaleString('es-CL') + ' UF / m²';
    }
  });
  updateCalc();
  updateProjectSummary();
}

document.querySelectorAll('.project-type').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.project-type').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    selectedProjectLabel = button.textContent.trim();
    selectedFactor = Number(button.dataset.factor || 1);
    applyProjectFactor();
  });
});

m2Input.addEventListener('input', updateProjectSummary);
m2Range.addEventListener('input', updateProjectSummary);
document.querySelectorAll('.tier-card').forEach(card => card.addEventListener('click', updateProjectSummary));
applyProjectFactor();
'''
    s = s.replace('/* ===== 9. START ===== */', calc_patch + '\n\n/* ===== 9. START ===== */')

p.write_text(s, encoding='utf-8')
