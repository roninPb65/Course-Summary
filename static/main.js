/* Alberta Career Pathways — main.js */

const inp = document.getElementById('career-input');
inp.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

const STEP_LABELS = [
  'Searching SAIT programs\u2026',
  'Searching NAIT programs\u2026',
  'Building your pathway\u2026',
];

/* ── STATE HELPERS ─────────────────────────────────── */

function show(id) {
  ['empty-state', 'loading-state', 'error-state', 'results-state'].forEach(s =>
    document.getElementById(s).classList.add('hidden')
  );
  document.getElementById(id).classList.remove('hidden');
}

function resetUI() {
  show('empty-state');
  document.getElementById('search-btn').disabled = false;
  inp.value = '';
  inp.focus();
  // hide sub-sections for next run
  ['insight-box', 'sait-section', 'nait-section', 'pathway-section'].forEach(id =>
    document.getElementById(id).classList.add('hidden')
  );
}

function useSuggestion(career) {
  inp.value = career;
  doSearch();
}

/* ── STEP PILLS ────────────────────────────────────── */

function setStep(activeMsg) {
  STEP_LABELS.forEach((label, i) => {
    const el = document.getElementById('step-' + i);
    const activeIndex = STEP_LABELS.indexOf(activeMsg);
    if (i < activeIndex) {
      el.className = 'step-pill step-done';
      el.textContent = '\u2713 ' + label;
    } else if (i === activeIndex) {
      el.className = 'step-pill step-active';
      el.textContent = label;
    } else {
      el.className = 'step-pill step-pending';
      el.textContent = label;
    }
  });
}

/* ── CARD BUILDERS ─────────────────────────────────── */

function buildCourseCard(course, inst) {
  const tag = inst === 'sait'
    ? '<span class="inst-tag tag-sait">SAIT</span>'
    : '<span class="inst-tag tag-nait">NAIT</span>';

  const meta = [
    course.duration   ? `<span class="meta-pill meta-duration">\u23f1 ${course.duration}</span>` : '',
    course.credential ? `<span class="meta-pill meta-credential">\uD83C\uDF93 ${course.credential}</span>` : '',
    course.area       ? `<span class="meta-pill meta-area">${course.area}</span>` : '',
  ].join('');

  const url = course.url || (inst === 'sait'
    ? 'https://www.sait.ca/programs-and-courses'
    : 'https://www.nait.ca/programs');

  return `
    <a class="course-card" href="${url}" target="_blank" rel="noopener noreferrer">
      <div class="card-header"><h4>${course.name}</h4>${tag}</div>
      <p>${course.desc}</p>
      <div class="card-meta">${meta}</div>
      <span class="card-link">View program \u2192</span>
    </a>`;
}

function buildPathway(steps) {
  return steps.map((s, i) => `
    <div class="pathway-step">
      <div class="step-line">
        <div class="step-num">${i + 1}</div>
        ${i < steps.length - 1 ? '<div class="step-connector"></div>' : ''}
      </div>
      <div class="step-content">
        <h4>${s.step}</h4>
        ${s.detail ? `<p>${s.detail}</p>` : ''}
      </div>
    </div>`).join('');
}

/* ── RENDER RESULTS ────────────────────────────────── */

function renderResults(career, data) {
  document.getElementById('results-title').textContent = `Your path to becoming a ${career}`;
  document.getElementById('results-summary').textContent = data.summary || '';

  if (data.insight) {
    document.getElementById('insight-text').textContent = data.insight;
    document.getElementById('insight-box').classList.remove('hidden');
  }

  if (data.sait && data.sait.length) {
    document.getElementById('sait-grid').innerHTML = data.sait.map(c => buildCourseCard(c, 'sait')).join('');
    document.getElementById('sait-section').classList.remove('hidden');
  }

  if (data.nait && data.nait.length) {
    document.getElementById('nait-grid').innerHTML = data.nait.map(c => buildCourseCard(c, 'nait')).join('');
    document.getElementById('nait-section').classList.remove('hidden');
  }

  if (data.pathway && data.pathway.length) {
    document.getElementById('pathway-steps').innerHTML = buildPathway(data.pathway);
    document.getElementById('pathway-section').classList.remove('hidden');
  }

  show('results-state');
  document.getElementById('search-btn').disabled = false;
  document.getElementById('main-content').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ── MAIN SEARCH ───────────────────────────────────── */

async function doSearch() {
  const career = inp.value.trim();
  if (!career) return;

  document.getElementById('search-btn').disabled = true;
  document.getElementById('loading-career').textContent = career;

  // Reset step pills
  STEP_LABELS.forEach((label, i) => {
    const el = document.getElementById('step-' + i);
    el.className = i === 0 ? 'step-pill step-active' : 'step-pill step-pending';
    el.textContent = label;
  });

  show('loading-state');

  try {
    const resp = await fetch('/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ career }),
    });

    if (!resp.ok) {
      throw new Error(`Server error: ${resp.status}`);
    }

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let payload;
        try { payload = JSON.parse(line.slice(6)); } catch { continue; }

        if (payload.type === 'status') {
          setStep(payload.msg);
        } else if (payload.type === 'error') {
          document.getElementById('error-msg').textContent = payload.msg;
          show('error-state');
          document.getElementById('search-btn').disabled = false;
        } else if (payload.type === 'result') {
          renderResults(career, payload.data);
        }
      }
    }
  } catch (err) {
    document.getElementById('error-msg').textContent = err.message || 'Network error. Please try again.';
    show('error-state');
    document.getElementById('search-btn').disabled = false;
  }
}
