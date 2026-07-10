INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alveoles</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, system-ui, sans-serif;
    background: #0e0f13;
    color: #f4f4f5;
    display: flex;
    justify-content: center;
    padding: 24px 16px 48px;
  }
  main { width: 100%; max-width: 460px; }
  h1 { font-size: 1.5rem; margin: 0 0 4px; }
  .sub { color: #9ca3af; margin: 0 0 24px; font-size: .9rem; }
  label { display: block; font-size: .85rem; color: #c7c7cc; margin: 16px 0 6px; }
  select, input {
    width: 100%;
    padding: 12px;
    font-size: 1rem;
    border-radius: 12px;
    border: 1px solid #2a2c33;
    background: #16181d;
    color: #f4f4f5;
  }
  .field { display: flex; align-items: center; gap: 12px; }
  .field input[type=range] { flex: 1; padding: 0; }
  .field output { min-width: 64px; text-align: right; font-variant-numeric: tabular-nums; color: #ffd166; }
  button {
    width: 100%;
    margin-top: 28px;
    padding: 14px;
    font-size: 1.05rem;
    font-weight: 600;
    border: none;
    border-radius: 14px;
    background: #ffd166;
    color: #1a1a1a;
    cursor: pointer;
  }
  button:active { transform: scale(.99); }
  #status { margin-top: 16px; text-align: center; min-height: 1.2em; font-size: .9rem; color: #9ca3af; }
</style>
</head>
<body>
<main>
  <h1>Alveoles</h1>
  <p class="sub">Pick a program and tune it live.</p>
  <p><a href="/grid" style="color:#ffd166">View grid</a></p>

  <label for="program">Program</label>
  <select id="program"></select>

  <div id="params"></div>

  <button id="apply">Apply</button>
  <div id="status"></div>
</main>

<script>
let PROGRAMS = [];
let STATE = { program: null, kwargs: {} };
let PROGRAM_DRAFTS = {};
let pendingParams = {};
let paramTimer = null;
let sendingParams = false;
const LOG_SLIDER_MIN = 0.001;
const LOG_SLIDER_MAX = 10;
const LOG_SLIDER_STEPS = 1000;

function clamp(v, min, max) {
  return Math.min(max, Math.max(min, v));
}

function toLogSliderPosition(value) {
  const minLog = Math.log(LOG_SLIDER_MIN);
  const maxLog = Math.log(LOG_SLIDER_MAX);
  const pos = (Math.log(value) - minLog) / (maxLog - minLog);
  return clamp(Math.round(pos * LOG_SLIDER_STEPS), 0, LOG_SLIDER_STEPS);
}

function fromLogSliderPosition(position) {
  const minLog = Math.log(LOG_SLIDER_MIN);
  const maxLog = Math.log(LOG_SLIDER_MAX);
  const ratio = clamp(position / LOG_SLIDER_STEPS, 0, 1);
  return Math.exp(minLog + ratio * (maxLog - minLog));
}

function formatValue(param, value) {
  if (param.step >= 1) {
    return String(Math.round(value));
  }
  if (value >= 1) {
    return value.toFixed(3).replace(/\\.?0+$/, '');
  }
  return value.toFixed(4).replace(/\\.?0+$/, '');
}

async function fetchJsonWithTimeout(url, options = {}, timeoutMs = 5000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: ctrl.signal });
    if (!res.ok) throw new Error(await res.text());
    return await res.json();
  } finally {
    clearTimeout(t);
  }
}

async function load() {
  PROGRAMS = await fetchJsonWithTimeout('/api/programs', {}, 8000);
  STATE = await fetchJsonWithTimeout('/api/state', {}, 8000);

  PROGRAM_DRAFTS = {};
  for (const prog of PROGRAMS) {
    PROGRAM_DRAFTS[prog.name] = defaultsForProgram(prog);
  }
  if (STATE.program && PROGRAM_DRAFTS[STATE.program]) {
    Object.assign(PROGRAM_DRAFTS[STATE.program], STATE.kwargs || {});
  }

  const sel = document.getElementById('program');
  sel.innerHTML = '';
  for (const prog of PROGRAMS) {
    const opt = document.createElement('option');
    opt.value = prog.name;
    opt.textContent = prog.label;
    sel.appendChild(opt);
  }
  sel.value = STATE.program || PROGRAMS[0].name;
  sel.onchange = () => {
    renderParams();
    updateApplyButton();
  };
  renderParams();
  updateApplyButton();
}

function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}

function currentProgram() {
  const name = document.getElementById('program').value;
  return PROGRAMS.find(p => p.name === name);
}

function defaultsForProgram(prog) {
  const defaults = {};
  for (const param of prog.params) {
    defaults[param.name] = param.default;
  }
  return defaults;
}

function ensureProgramDraft(name) {
  if (!PROGRAM_DRAFTS[name]) {
    const prog = PROGRAMS.find((p) => p.name === name);
    PROGRAM_DRAFTS[name] = defaultsForProgram(prog);
  }
  return PROGRAM_DRAFTS[name];
}

function updateApplyButton() {
  const applyBtn = document.getElementById('apply');
  const selectedProgram = document.getElementById('program').value;
  applyBtn.disabled = selectedProgram === STATE.program;
}

function renderParams() {
  const prog = currentProgram();
  const box = document.getElementById('params');
  box.innerHTML = '';
  const isActiveProgram = STATE.program === prog.name;
  const draft = ensureProgramDraft(prog.name);

  for (const param of prog.params) {
    const value = draft[param.name] !== undefined ? draft[param.name] : param.default;
    const isLogScale = param.scale === 'log' && param.name !== 'max_intensity';

    const label = document.createElement('label');
    label.textContent = param.label;
    label.htmlFor = 'p_' + param.name;
    box.appendChild(label);

    const field = document.createElement('div');
    field.className = 'field';

    const input = document.createElement('input');
    input.type = 'range';
    input.id = 'p_' + param.name;
    input.dataset.param = param.name;

    if (isLogScale) {
      const safeValue = clamp(Number(value) || LOG_SLIDER_MIN, LOG_SLIDER_MIN, LOG_SLIDER_MAX);
      input.min = 0;
      input.max = LOG_SLIDER_STEPS;
      input.step = 1;
      input.value = toLogSliderPosition(safeValue);
    } else {
      input.min = param.min;
      input.max = param.max;
      input.step = param.step;
      input.value = value;
    }

    const out = document.createElement('output');
    out.textContent = formatValue(param, Number(value));
    input.disabled = false;

    input.oninput = () => {
      const nextValue = isLogScale
        ? fromLogSliderPosition(parseFloat(input.value))
        : parseFloat(input.value);
      out.textContent = formatValue(param, nextValue);
      draft[input.dataset.param] = nextValue;
      if (isActiveProgram) {
        queueParamUpdate(input.dataset.param, nextValue);
      } else {
        setStatus('Draft updated');
      }
    };

    field.appendChild(input);
    field.appendChild(out);
    box.appendChild(field);
  }
}

function queueParamUpdate(name, value) {
  pendingParams[name] = value;
  if (paramTimer) clearTimeout(paramTimer);
  paramTimer = setTimeout(flushParamUpdates, 80);
}

async function flushParamUpdates() {
  if (sendingParams) return;

  const names = Object.keys(pendingParams);
  if (!names.length) return;

  const patch = pendingParams;
  pendingParams = {};
  sendingParams = true;

  try {
    STATE = await fetchJsonWithTimeout('/api/params', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (STATE.program) {
      const activeDraft = ensureProgramDraft(STATE.program);
      Object.assign(activeDraft, STATE.kwargs || {});
    }
    setStatus('Live updated');
  } catch (e) {
    setStatus('Error: ' + e.message);
  } finally {
    sendingParams = false;
    if (Object.keys(pendingParams).length) {
      if (paramTimer) clearTimeout(paramTimer);
      paramTimer = setTimeout(flushParamUpdates, 80);
    }
  }
}

document.getElementById('apply').onclick = async () => {
  const program = document.getElementById('program').value;
  const kwargs = ensureProgramDraft(program);
  setStatus('Applying...');
  try {
    STATE = await fetchJsonWithTimeout('/api/program', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ program: program, kwargs: kwargs }),
    });
    if (STATE.program) {
      const activeDraft = ensureProgramDraft(STATE.program);
      Object.assign(activeDraft, STATE.kwargs || {});
    }
    renderParams();
    updateApplyButton();
    setStatus('Running: ' + program);
  } catch (e) {
    setStatus('Error: ' + e.message);
  }
};

load();
</script>
</body>
</html>
"""


GRID_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alveoles Grid</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, system-ui, sans-serif;
    background: #0e0f13;
    color: #f4f4f5;
    padding: 20px 12px 32px;
    display: flex;
    justify-content: center;
  }
  main { width: 100%; max-width: 760px; }
  h1 { margin: 0 0 6px; font-size: 1.4rem; }
  .sub { margin: 0 0 14px; color: #9ca3af; }
  a { color: #ffd166; text-decoration: none; }
  .card {
    background: #16181d;
    border: 1px solid #2a2c33;
    border-radius: 14px;
    padding: 10px;
  }
  svg {
    width: 100%;
    height: auto;
    display: block;
  }
  .edge { stroke: #3b82f6; stroke-width: 2; opacity: 0.65; }
  .node { fill: #ffd166; stroke: #1a1a1a; stroke-width: 1.5; }
  .label {
    fill: #111827;
    font-size: 11px;
    font-weight: 700;
    text-anchor: middle;
    dominant-baseline: middle;
  }
  .legend {
    margin-top: 10px;
    font-size: 0.88rem;
    color: #c7c7cc;
  }
</style>
</head>
<body>
<main>
  <h1>Grid view</h1>
  <p class="sub">COORDS and adjacency used by the LED programs. <a href="/">Back</a></p>
  <div class="card">
    <svg id="grid" viewBox="0 0 760 520" preserveAspectRatio="xMidYMid meet"></svg>
  </div>
  <div class="legend" id="legend">Loading...</div>
</main>

<script>
async function loadGrid() {
  const res = await fetch('/api/grid');
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  draw(data.coords, data.edges);
}

function draw(coords, edges) {
  const svg = document.getElementById('grid');
  svg.innerHTML = '';

  const scaleX = 90;
  const scaleY = 70;
  const padX = 70;
  const padY = 60;

  // Build offset-grid coordinates, then rotate 90 degrees the other way.
  const lattice = coords.map(([row, col], idx) => {
    const gx = col + (row % 2) * 0.5;
    const gy = row;
    const rx = gy;
    const ry = -gx;
    return { idx, rx, ry };
  });

  const minRx = Math.min(...lattice.map((p) => p.rx));
  const minRy = Math.min(...lattice.map((p) => p.ry));

  const pos = lattice.map((p) => {
    const x = padX + (p.rx - minRx) * scaleX;
    const y = padY + (p.ry - minRy) * scaleY;
    return { idx: p.idx, x, y };
  });

  for (const [a, b] of edges) {
    const p1 = pos[a];
    const p2 = pos[b];
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', p1.x);
    line.setAttribute('y1', p1.y);
    line.setAttribute('x2', p2.x);
    line.setAttribute('y2', p2.y);
    line.setAttribute('class', 'edge');
    svg.appendChild(line);
  }

  for (const p of pos) {
    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', p.x);
    c.setAttribute('cy', p.y);
    c.setAttribute('r', 18);
    c.setAttribute('class', 'node');
    svg.appendChild(c);

    const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    t.setAttribute('x', p.x);
    t.setAttribute('y', p.y);
    t.setAttribute('class', 'label');
    t.textContent = String(p.idx);
    svg.appendChild(t);
  }

  document.getElementById('legend').textContent =
    'Nodes: ' + coords.length + ' | Edges: ' + edges.length;
}

loadGrid().catch((e) => {
  document.getElementById('legend').textContent = 'Error: ' + e.message;
});
</script>
</body>
</html>
"""
