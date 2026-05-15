/* Alberta Career Pathways — main.js */

const STEP_LABELS = ['Searching universities\u2026', 'Gathering market insights\u2026', 'Building your pathway\u2026'];
const METHOD_LABELS = {
  shadow:  '🔭 Shadowing Lottery',
  unjob:   '🦄 Un-Job Posting',
  audit:   '🧪 Audit Experiment',
  problem: '🌍 Problem-Mapping',
  podcast: '🎙️ Insider Podcast',
  direct:  '🔍 Direct Search',
};

/* ── STATE ─────────────────────────────────────────────── */

function showState(id) {
  ['hub-state', 'form-state', 'loading-state', 'error-state', 'results-state'].forEach(s => {
    const el = document.getElementById(s);
    if (el) el.classList.add('hidden');
  });
  document.getElementById(id).classList.remove('hidden');
}

function resetToHub() {
  showState('hub-state');
  window.scrollTo({ top: document.getElementById('main-content').offsetTop - 20, behavior: 'smooth' });
}

function goBack() {
  showState('hub-state');
}

/* ── METHOD NAVIGATION ──────────────────────────────────── */

function openMethod(method) {
  // Hide all forms
  document.querySelectorAll('.discovery-form').forEach(f => f.classList.add('hidden'));
  // Show selected
  const form = document.getElementById('form-' + method);
  if (form) form.classList.remove('hidden');
  showState('form-state');
  window.scrollTo({ top: document.getElementById('main-content').offsetTop - 20, behavior: 'smooth' });
}

/* ── HELPER: set example text ───────────────────────────── */

function setExample(inputId, value) {
  const el = document.getElementById(inputId);
  if (el) { el.value = value; el.focus(); }
}

/* ── TOGGLE BUTTONS ─────────────────────────────────────── */

function setPref(prefix, value) {
  document.querySelectorAll(`[id^="${prefix}-pref-"]`).forEach(btn => {
    btn.classList.toggle('active', btn.id === `${prefix}-pref-${value}`);
  });
}

function setCredPref(value) {
  ['any', 'cert', 'degree'].forEach(v => {
    document.getElementById(`pod-cred-${v}`)?.classList.toggle('active', v === value);
  });
}

/* ── STEP PILLS ─────────────────────────────────────────── */

function setStep(activeMsg) {
  STEP_LABELS.forEach((label, i) => {
    const el = document.getElementById('step-' + i);
    if (!el) return;
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

/* ── TAB SWITCHING ──────────────────────────────────────── */

function switchTab(tab) {
  ['universities', 'colleges'].forEach(t => {
    document.getElementById('tab-' + t)?.classList.toggle('active', t === tab);
    document.getElementById('tab-content-' + t)?.classList.toggle('hidden', t !== tab);
  });
}

/* ── CARD BUILDERS ──────────────────────────────────────── */

function buildCourseCard(c) {
  const instClass = c.institution_type === 'university' ? 'university' : 'college';
  const meta = [
    c.duration   ? `<span class="meta-pill meta-duration">\u23f1 ${c.duration}</span>` : '',
    c.credential ? `<span class="meta-pill meta-credential">\uD83C\uDF93 ${c.credential}</span>` : '',
  ].filter(Boolean).join('');

  return `
    <a class="course-card" href="${c.url || '#'}" target="_blank" rel="noopener noreferrer">
      <div class="card-top">
        <h4>${c.name}</h4>
        <span class="card-inst ${instClass}">${c.institution || ''}</span>
      </div>
      <p>${c.desc || ''}</p>
      ${meta ? `<div class="card-meta">${meta}</div>` : ''}
      <div class="card-link">View program \u2192</div>
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

/* ── RENDER RESULTS ─────────────────────────────────────── */

function renderResults(data) {
  document.getElementById('method-badge').textContent = METHOD_LABELS[data.method] || '✦ Results';
  document.getElementById('results-title').textContent = `Programs aligned with: ${data.career}`;
  document.getElementById('results-summary').textContent = data.summary || '';

  if (data.insight) {
    document.getElementById('insight-text').textContent = data.insight;
    document.getElementById('insight-box').classList.remove('hidden');
  }

  const univs = data.universities || [];
  const colls = data.colleges    || [];

  document.getElementById('univ-count').textContent = univs.length || '';
  document.getElementById('coll-count').textContent = colls.length || '';

  document.getElementById('tab-content-universities').innerHTML =
    univs.length ? univs.map(buildCourseCard).join('') : '<p style="color:#aaa;padding:20px 0">No university programs found for this search. Try the Colleges tab.</p>';

  document.getElementById('tab-content-colleges').innerHTML =
    colls.length ? colls.map(buildCourseCard).join('') : '<p style="color:#aaa;padding:20px 0">No college programs found for this search. Try the Universities tab.</p>';

  // Default to whichever tab has results
  if (!univs.length && colls.length) switchTab('colleges');
  else switchTab('universities');

  if (data.pathway && data.pathway.length) {
    document.getElementById('pathway-steps').innerHTML = buildPathway(data.pathway);
    document.getElementById('pathway-section').classList.remove('hidden');
  }

  showState('results-state');
  window.scrollTo({ top: document.getElementById('main-content').offsetTop - 20, behavior: 'smooth' });
}

/* ── STREAMING SSE ──────────────────────────────────────── */

async function streamSearch(url, body) {
  // Reset step pills
  STEP_LABELS.forEach((label, i) => {
    const el = document.getElementById('step-' + i);
    if (el) { el.className = i === 0 ? 'step-pill step-active' : 'step-pill step-pending'; el.textContent = label; }
  });
  // Reset sub-sections
  ['insight-box', 'pathway-section'].forEach(id => document.getElementById(id)?.classList.add('hidden'));
  document.getElementById('pathway-section')?.classList.add('hidden');

  showState('loading-state');

  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`Server error: ${resp.status}`);

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        let payload;
        try { payload = JSON.parse(line.slice(6)); } catch { continue; }
        if (payload.type === 'status')  setStep(payload.msg);
        if (payload.type === 'error')   { document.getElementById('error-msg').textContent = payload.msg; showState('error-state'); }
        if (payload.type === 'result')  renderResults(payload.data);
      }
    }
  } catch (err) {
    document.getElementById('error-msg').textContent = err.message || 'Network error.';
    showState('error-state');
  }
}

/* ── SUBMIT HANDLERS ────────────────────────────────────── */

function submitDiscovery(method) {
  const data = { method };

  if (method === 'shadow') {
    data.job1 = document.getElementById('shadow-job1')?.value.trim();
    data.job2 = document.getElementById('shadow-job2')?.value.trim();
    data.job3 = document.getElementById('shadow-job3')?.value.trim();
    data.job4 = document.getElementById('shadow-job4')?.value.trim();
    data.job5 = document.getElementById('shadow-job5')?.value.trim();
    if (!data.job1) { alert('Please enter at least one dream job.'); return; }
  }

  if (method === 'unjob') {
    data.unjob_title = document.getElementById('unjob-title')?.value.trim();
    data.unjob_why   = document.getElementById('unjob-why')?.value.trim();
    if (!data.unjob_title) { alert('Please enter the job title.'); return; }
  }

  if (method === 'audit') {
    data.subject1 = document.getElementById('audit-s1')?.value.trim();
    data.subject2 = document.getElementById('audit-s2')?.value.trim();
    data.subject3 = document.getElementById('audit-s3')?.value.trim();
    if (!data.subject1 || !data.subject2) { alert('Please enter at least two subjects.'); return; }
  }

  if (method === 'problem') {
    data.problem = document.getElementById('problem-input')?.value.trim();
    if (!data.problem) { alert('Please describe the world problem.'); return; }
  }

  if (method === 'podcast') {
    data.industry = document.getElementById('podcast-industry')?.value.trim();
    if (!data.industry) { alert('Please enter an industry.'); return; }
  }

  if (method === 'direct') {
    data.career = document.getElementById('direct-career')?.value.trim();
    if (!data.career) { alert('Please enter a career goal.'); return; }
    streamSearch('/search', data);
    return;
  }

  streamSearch('/discover', data);
}
