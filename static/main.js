/* Alberta Career Pathways — main.js */

const STEP_LABELS = [
  'Searching universities\u2026',
  'Searching colleges & polytechnics\u2026',
  'Gathering market insights\u2026',
  'Building your pathway\u2026',
];
const METHOD_LABELS = {
  shadow:  '🔭 Shadowing Lottery',
  unjob:   '🦄 Un-Job Posting',
  audit:   '🧪 Audit Experiment',
  problem: '🌍 Problem-Mapping',
  podcast: '🎙️ Insider Podcast',
  direct:  '🔍 Direct Search',
};

// Holds the governance data from the last search — used by the modal
let _lastGovernance = null;

/* ── STATE ─────────────────────────────────────────────── */
function showState(id) {
  ['hub-state','form-state','loading-state','error-state','results-state'].forEach(s => {
    document.getElementById(s)?.classList.add('hidden');
  });
  document.getElementById(id)?.classList.remove('hidden');
}
function resetToHub() {
  showState('hub-state');
  ['insight-box','pathway-section','governance-card','transparency-bar'].forEach(id =>
    document.getElementById(id)?.classList.add('hidden')
  );
  _lastGovernance = null;
  window.scrollTo({ top: document.getElementById('main-content').offsetTop - 20, behavior: 'smooth' });
}
function goBack() { showState('hub-state'); }

/* ── METHOD NAVIGATION ──────────────────────────────────── */
function openMethod(method) {
  document.querySelectorAll('.discovery-form').forEach(f => f.classList.add('hidden'));
  document.getElementById('form-' + method)?.classList.remove('hidden');
  showState('form-state');
  window.scrollTo({ top: document.getElementById('main-content').offsetTop - 20, behavior: 'smooth' });
}
function setExample(inputId, value) {
  const el = document.getElementById(inputId);
  if (el) { el.value = value; el.focus(); }
}
function setPref(prefix, value) {
  document.querySelectorAll(`[id^="${prefix}-pref-"]`).forEach(btn =>
    btn.classList.toggle('active', btn.id === `${prefix}-pref-${value}`)
  );
}
function setCredPref(value) {
  ['any','cert','degree'].forEach(v =>
    document.getElementById(`pod-cred-${v}`)?.classList.toggle('active', v === value)
  );
}

/* ── STEP PILLS ─────────────────────────────────────────── */
function setStep(activeMsg) {
  STEP_LABELS.forEach((label, i) => {
    const el = document.getElementById('step-' + i);
    if (!el) return;
    const idx = STEP_LABELS.indexOf(activeMsg);
    if (i < idx)      { el.className = 'step-pill step-done';    el.textContent = '\u2713 ' + label; }
    else if (i === idx){ el.className = 'step-pill step-active';  el.textContent = label; }
    else               { el.className = 'step-pill step-pending'; el.textContent = label; }
  });
}

/* ── TAB SWITCHING ──────────────────────────────────────── */
function switchTab(tab) {
  ['universities','colleges'].forEach(t => {
    document.getElementById('tab-' + t)?.classList.toggle('active', t === tab);
    document.getElementById('tab-content-' + t)?.classList.toggle('hidden', t !== tab);
  });
}

/* ── PER-CARD REASONING ─────────────────────────────────── */
function toggleWhy(id) {
  const el = document.getElementById('why-' + id);
  if (!el) return;
  el.classList.toggle('open');
  const btn = document.getElementById('why-btn-' + id);
  if (btn) btn.textContent = el.classList.contains('open') ? '🔍 Hide reasoning ↑' : '🔍 Why this? ↓';
}

/* ── TRANSPARENCY BAR ───────────────────────────────────── */
function toggleTransparency() {
  const trail = document.getElementById('audit-trail');
  const btn   = document.querySelector('.trans-expand-btn');
  if (!trail) return;
  const isOpen = !trail.classList.contains('hidden');
  trail.classList.toggle('hidden', isOpen);
  if (btn) btn.textContent = isOpen ? 'View full audit trail ↓' : 'Hide audit trail ↑';
}

/* ── AUDIT TRAIL RENDERER ───────────────────────────────── */
const STEP_NAMES = {
  session_start:           'Session Start',
  career_interpretation:   'Career Interpretation',
  targeted_search:         'Targeted Search',
  targeted_search_error:   'Search Error',
  broad_fallback_search:   'Broad Fallback Search',
  broad_fallback_error:    'Fallback Error',
  filtering:               'Result Filtering',
  market_insight_search:   'Labour Market Search',
  market_insight_error:    'Market Search Error',
  session_complete:        'Session Complete',
};

function renderAuditTrail(audit) {
  const container = document.getElementById('audit-trail');
  if (!container || !audit) return;

  const html = audit.map((step, i) => {
    const label = STEP_NAMES[step.step] || step.step;
    let meta = '';
    if (step.query)         meta += `Query: "${step.query}" `;
    if (step.domains_count) meta += `| Domains searched: ${step.domains_count} `;
    if (step.raw_results !== undefined) meta += `| Raw results: ${step.raw_results} `;
    if (step.final_count  !== undefined) meta += `| After filtering: ${step.final_count} `;
    if (step.duration_ms)  meta += `| Time: ${step.duration_ms}ms `;
    if (step.input)        meta += `Input: "${step.input}" `;
    if (step.output && Array.isArray(step.output)) meta += `→ Terms: [${step.output.join(', ')}]`;
    if (step.error)        meta += `⚠ Error: ${step.error}`;

    return `
      <div class="audit-step">
        <div class="audit-step-num">${i + 1}</div>
        <div class="audit-step-body">
          <div class="audit-label">${label}</div>
          ${step.reason ? `<div class="audit-reason">${step.reason}</div>` : ''}
          ${meta       ? `<div class="audit-detail">${meta.trim()}</div>` : ''}
        </div>
      </div>`;
  }).join('');

  container.innerHTML = html;
}

/* ── GOVERNANCE MODAL ───────────────────────────────────── */
function openGovModal() {
  document.getElementById('gov-modal')?.classList.remove('hidden');
  if (_lastGovernance) renderGovModal(_lastGovernance);
  document.body.style.overflow = 'hidden';
}
function closeGovModal() {
  document.getElementById('gov-modal')?.classList.add('hidden');
  document.body.style.overflow = '';
}
function closeGovModalOutside(e) {
  if (e.target.id === 'gov-modal') closeGovModal();
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeGovModal(); });

function renderGovModal(gov) {
  const body = document.getElementById('gov-modal-body');
  if (!body || !gov) return;

  body.innerHTML = `
    <div class="modal-section">
      <h3>System Information</h3>
      <dl class="modal-kv">
        <dt>System</dt>      <dd>${gov.system_version || '-'}</dd>
        <dt>Model type</dt>  <dd>${gov.model_type || '-'}</dd>
        <dt>Data source</dt> <dd>${gov.data_source || '-'}</dd>
        <dt>Searched at</dt> <dd>${gov.search_timestamp || '-'}</dd>
        <dt>Career input</dt><dd>${gov.career_input || '-'}</dd>
        <dt>Terms used</dt>  <dd>${(gov.terms_used || []).join(', ')}</dd>
        <dt>Institutions</dt><dd>${gov.institutions_searched || '-'} searched</dd>
        <dt>Results found</dt><dd>${gov.results_found || 0} programs</dd>
        <dt>Audit steps</dt> <dd>${gov.audit_steps || 0} logged</dd>
      </dl>
    </div>

    <div class="modal-section">
      <h3>⚠ Limitations</h3>
      <ul>${(gov.limitations || []).map(l => `<li>${l}</li>`).join('')}</ul>
    </div>

    <div class="modal-section">
      <h3>⚖ Bias Disclosures</h3>
      <ul>${(gov.bias_disclosures || []).map(b => `<li>${b}</li>`).join('')}</ul>
    </div>

    <div class="modal-section">
      <h3>👤 Human Oversight</h3>
      <p>${gov.human_oversight || ''}</p>
    </div>

    <div class="modal-section">
      <h3>🔒 Data Privacy</h3>
      <p>${gov.data_privacy || ''}</p>
    </div>

    <div class="modal-section">
      <h3>💬 Feedback</h3>
      <p>${gov.feedback_prompt || ''}</p>
    </div>

    <div class="modal-section">
      <h3>📋 Full Decision Audit Trail</h3>
      ${(gov.full_audit || []).map((step, i) => {
        const label = STEP_NAMES[step.step] || step.step;
        let meta = [];
        if (step.query)           meta.push(`query: "${step.query}"`);
        if (step.domains_count)   meta.push(`domains: ${step.domains_count}`);
        if (step.raw_results !== undefined) meta.push(`raw results: ${step.raw_results}`);
        if (step.final_count  !== undefined) meta.push(`after filter: ${step.final_count}`);
        if (step.duration_ms)     meta.push(`${step.duration_ms}ms`);
        if (step.input)           meta.push(`input: "${step.input}"`);
        if (step.output && Array.isArray(step.output)) meta.push(`terms: [${step.output.join(', ')}]`);
        if (step.error)           meta.push(`⚠ ${step.error}`);
        return `
          <div class="modal-audit-step">
            <div class="step-name">${i+1}. ${label}</div>
            ${step.reason ? `<div class="step-reason">${step.reason}</div>` : ''}
            ${meta.length  ? `<div class="step-meta">${meta.join(' | ')}</div>` : ''}
          </div>`;
      }).join('')}
    </div>`;
}

/* ── CARD BUILDERS ──────────────────────────────────────── */
let _cardIndex = 0;
function buildCourseCard(c) {
  const id         = _cardIndex++;
  const instClass  = c.institution_type === 'university' ? 'university' : 'college';
  const meta = [
    c.duration   ? `<span class="meta-pill meta-duration">⏱ ${c.duration}</span>` : '',
    c.credential ? `<span class="meta-pill meta-credential">🎓 ${c.credential}</span>` : '',
  ].filter(Boolean).join('');

  const reasons = (c.reasons || []).map(r => `<li>${r}</li>`).join('');

  return `
    <div class="course-card">
      <div class="card-top">
        <h4>${c.name}</h4>
        <span class="card-inst ${instClass}">${c.institution || ''}</span>
      </div>
      <p>${c.desc || ''}</p>
      ${meta ? `<div class="card-meta">${meta}</div>` : ''}
      <a href="${c.url || '#'}" target="_blank" rel="noopener noreferrer" class="card-link">View program →</a>
      <button class="why-toggle" id="why-btn-${id}" onclick="toggleWhy(${id})">🔍 Why this? ↓</button>
      <div class="why-section" id="why-${id}">
        <ul>${reasons || '<li>Source: ' + (c.institution || 'Alberta institution') + '</li>'}</ul>
      </div>
    </div>`;
}

function buildPathway(steps) {
  return steps.map((s, i) => `
    <div class="pathway-step">
      <div class="step-line">
        <div class="step-num">${i+1}</div>
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
  _cardIndex = 0;
  _lastGovernance = data.governance || null;

  document.getElementById('method-badge').textContent = METHOD_LABELS[data.method] || '✦ Results';
  document.getElementById('results-title').textContent = `Programs aligned with: ${data.career}`;
  document.getElementById('results-summary').textContent = data.summary || '';

  // ── Transparency bar ──
  const gov = data.governance;
  if (gov) {
    const bar = document.getElementById('transparency-bar');
    const txt = document.getElementById('trans-summary-text');
    if (txt) txt.textContent = ` Searched ${gov.institutions_searched} institutions using ${(gov.terms_used||[]).length} academic terms. Found ${gov.results_found} programs. ${gov.audit_steps} decision steps logged.`;
    bar?.classList.remove('hidden');
    renderAuditTrail(gov.full_audit);
  }

  // ── Insight ──
  if (data.insight) {
    document.getElementById('insight-text').textContent = data.insight;
    document.getElementById('insight-box')?.classList.remove('hidden');
  }

  // ── Course grids ──
  const univs = data.universities || [];
  const colls = data.colleges    || [];
  document.getElementById('univ-count').textContent = univs.length || '';
  document.getElementById('coll-count').textContent = colls.length || '';
  document.getElementById('tab-content-universities').innerHTML =
    univs.length ? univs.map(buildCourseCard).join('') : '<p style="color:#aaa;padding:20px 0">No university programs found. Try the Colleges tab.</p>';
  document.getElementById('tab-content-colleges').innerHTML =
    colls.length ? colls.map(buildCourseCard).join('') : '<p style="color:#aaa;padding:20px 0">No college programs found. Try the Universities tab.</p>';
  if (!univs.length && colls.length) switchTab('colleges');
  else switchTab('universities');

  // ── Pathway ──
  if (data.pathway?.length) {
    document.getElementById('pathway-steps').innerHTML = buildPathway(data.pathway);
    document.getElementById('pathway-section')?.classList.remove('hidden');
  }

  // ── Governance card ──
  if (gov) {
    const lims = (gov.limitations || []).slice(0, 3);
    document.getElementById('gov-limitations').innerHTML = lims.map(l => `<span class="gov-limit-pill">${l}</span>`).join('');
    document.getElementById('governance-card')?.classList.remove('hidden');
  }

  showState('results-state');
  window.scrollTo({ top: document.getElementById('main-content').offsetTop - 20, behavior: 'smooth' });
}

/* ── STREAMING ──────────────────────────────────────────── */
async function streamSearch(url, body) {
  STEP_LABELS.forEach((label, i) => {
    const el = document.getElementById('step-' + i);
    if (el) { el.className = i === 0 ? 'step-pill step-active' : 'step-pill step-pending'; el.textContent = label; }
  });
  ['insight-box','pathway-section','governance-card','transparency-bar'].forEach(id =>
    document.getElementById(id)?.classList.add('hidden')
  );
  document.getElementById('audit-trail')?.classList.add('hidden');
  showState('loading-state');

  try {
    const resp = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    if (!resp.ok) throw new Error(`Server error: ${resp.status}`);
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
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
        if (payload.type === 'status') setStep(payload.msg);
        if (payload.type === 'error')  { document.getElementById('error-msg').textContent = payload.msg; showState('error-state'); }
        if (payload.type === 'result') renderResults(payload.data);
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
    document.getElementById('loading-career').textContent = data.career;
    streamSearch('/search', data);
    return;
  }
  const labelMap = { shadow: data.job1, unjob: data.unjob_title, audit: data.subject1, problem: data.problem, podcast: data.industry };
  document.getElementById('loading-career').textContent = labelMap[method] || method;
  streamSearch('/discover', data);
}
