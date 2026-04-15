const metricsGrid = document.getElementById('metrics-grid');
const intentTable = document.getElementById('intent-table');
const flaggedTable = document.getElementById('flagged-table');
const logsList = document.getElementById('logs-list');
const ratesChart = document.getElementById('rates-chart');
const reviewChart = document.getElementById('review-chart');
const intentChart = document.getElementById('intent-chart');
const refreshDashboardButton = document.getElementById('refresh-dashboard');
const reloadLogsButton = document.getElementById('reload-logs');
const flaggedOnlyInput = document.getElementById('flagged-only');
const reviewStatusSelect = document.getElementById('review-status');
const retrainHelpButton = document.getElementById('run-retrain-help');

function fmtPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function fmtNumber(value) {
  return Number(value || 0).toLocaleString();
}

function renderMetrics(summary) {
  const cards = [
    ['Total chats', fmtNumber(summary.total_chats)],
    ['Unique sessions', fmtNumber(summary.unique_sessions)],
    ['Avg confidence', Number(summary.avg_confidence || 0).toFixed(3)],
    ['Fallback rate', fmtPercent(summary.fallback_rate)],
    ['Guardrail rate', fmtPercent(summary.guardrail_rate)],
    ['Low-confidence rate', fmtPercent(summary.low_confidence_rate)],
    ['Retrieval rate', fmtPercent(summary.retrieval_rate)],
    ['Unreviewed logs', fmtNumber(summary.unreviewed_count)],
  ];

  metricsGrid.innerHTML = cards.map(([label, value]) => `
    <article class="metric-card">
      <span class="metric-label">${label}</span>
      <strong class="metric-value">${value}</strong>
    </article>
  `).join('');
}

function renderProgressChart(target, rows) {
  target.innerHTML = rows.map((row) => `
    <div class="chart-row">
      <div class="chart-labels">
        <span>${row.label}</span>
        <strong>${row.valueLabel}</strong>
      </div>
      <div class="chart-bar-track">
        <div class="chart-bar-fill ${row.tone || ''}" style="width: ${Math.max(2, Math.min(100, row.percent))}%"></div>
      </div>
    </div>
  `).join('');
}

function renderRateChart(summary) {
  renderProgressChart(ratesChart, [
    { label: 'Fallback', valueLabel: fmtPercent(summary.fallback_rate), percent: Number(summary.fallback_rate || 0) * 100, tone: 'warn' },
    { label: 'Guardrail', valueLabel: fmtPercent(summary.guardrail_rate), percent: Number(summary.guardrail_rate || 0) * 100, tone: 'warn' },
    { label: 'Low confidence', valueLabel: fmtPercent(summary.low_confidence_rate), percent: Number(summary.low_confidence_rate || 0) * 100, tone: 'danger' },
    { label: 'Retrieval', valueLabel: fmtPercent(summary.retrieval_rate), percent: Number(summary.retrieval_rate || 0) * 100, tone: 'success' },
  ]);
}

function renderReviewChart(summary) {
  const total = Number(summary.total_chats || 0) || 1;
  renderProgressChart(reviewChart, [
    { label: 'Accepted', valueLabel: fmtNumber(summary.accepted_count), percent: (Number(summary.accepted_count || 0) / total) * 100, tone: 'success' },
    { label: 'Unreviewed', valueLabel: fmtNumber(summary.unreviewed_count), percent: (Number(summary.unreviewed_count || 0) / total) * 100, tone: 'neutral' },
    { label: 'Rejected', valueLabel: fmtNumber(summary.rejected_count), percent: (Number(summary.rejected_count || 0) / total) * 100, tone: 'danger' },
  ]);
}

function renderIntentChart(rows) {
  const maxCount = Math.max(1, ...rows.slice(0, 8).map((row) => Number(row.count || 0)));
  renderProgressChart(intentChart, rows.slice(0, 8).map((row) => ({
    label: row.intent,
    valueLabel: `${fmtNumber(row.count)} | ${Number(row.avg_confidence || 0).toFixed(3)}`,
    percent: (Number(row.count || 0) / maxCount) * 100,
    tone: 'success',
  })));
}

function renderIntentTable(rows) {
  intentTable.innerHTML = rows.map((row) => `
    <tr>
      <td>${row.intent}</td>
      <td>${fmtNumber(row.count)}</td>
      <td>${Number(row.avg_confidence || 0).toFixed(3)}</td>
    </tr>
  `).join('');
}

function renderFlaggedTable(rows) {
  flaggedTable.innerHTML = rows.map((row) => `
    <tr>
      <td>${row.user_text}</td>
      <td>${fmtNumber(row.hits)}</td>
      <td>${row.latest_intent}</td>
      <td>${Number(row.avg_confidence || 0).toFixed(3)}</td>
    </tr>
  `).join('');
}

async function updateReview(logId, reviewStatus, correctedIntent, adminNotes) {
  await fetch(`/admin/api/logs/${logId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      review_status: reviewStatus,
      corrected_intent: correctedIntent || '',
      admin_notes: adminNotes || '',
    }),
  });
}

function renderLogs(logs) {
  logsList.innerHTML = '';

  if (!logs.length) {
    logsList.innerHTML = '<p class="empty-state">No logs match the current filters.</p>';
    return;
  }

  logs.forEach((log) => {
    const article = document.createElement('article');
    article.className = 'log-card';
    article.innerHTML = `
      <div class="log-topline">
        <span class="pill">${log.intent}</span>
        <span class="pill muted">confidence ${Number(log.confidence || 0).toFixed(3)}</span>
        <span class="pill muted">${log.response_source}</span>
        <span class="pill muted">${log.review_status}</span>
      </div>
      <p class="log-question">${log.user_text}</p>
      <p class="log-answer">${log.response}</p>
      <dl class="log-meta">
        <div><dt>Created</dt><dd>${new Date(log.created_at).toLocaleString()}</dd></div>
        <div><dt>Language</dt><dd>${log.detected_lang}</dd></div>
        <div><dt>Entity</dt><dd>${log.entity_label || '-'}</dd></div>
        <div><dt>Retrieval intent</dt><dd>${log.retrieval_intent || '-'}</dd></div>
        <div><dt>Session</dt><dd>${log.session_id || '-'}</dd></div>
      </dl>
      <div class="review-controls">
        <select class="review-select">
          <option value="unreviewed" ${log.review_status === 'unreviewed' ? 'selected' : ''}>unreviewed</option>
          <option value="accepted" ${log.review_status === 'accepted' ? 'selected' : ''}>accepted</option>
          <option value="rejected" ${log.review_status === 'rejected' ? 'selected' : ''}>rejected</option>
        </select>
        <input class="intent-input" type="text" value="${log.corrected_intent || ''}" placeholder="Corrected intent">
        <input class="notes-input" type="text" value="${log.admin_notes || ''}" placeholder="Admin notes">
        <button class="secondary-button save-review" type="button">Save review</button>
      </div>
    `;

    article.querySelector('.save-review').addEventListener('click', async () => {
      const reviewStatus = article.querySelector('.review-select').value;
      const correctedIntent = article.querySelector('.intent-input').value;
      const adminNotes = article.querySelector('.notes-input').value;
      await updateReview(log.id, reviewStatus, correctedIntent, adminNotes);
      await loadLogs();
      await loadSummary();
    });

    logsList.appendChild(article);
  });
}

async function loadSummary() {
  const response = await fetch('/admin/api/summary');
  const payload = await response.json();
  renderMetrics(payload.summary);
  renderRateChart(payload.summary);
  renderReviewChart(payload.summary);
  renderIntentChart(payload.intent_breakdown || []);
  renderIntentTable(payload.intent_breakdown || []);
  renderFlaggedTable(payload.flagged_phrases || []);
}

async function loadLogs() {
  const params = new URLSearchParams();
  params.set('limit', '60');
  if (flaggedOnlyInput.checked) {
    params.set('flagged_only', 'true');
  }
  if (reviewStatusSelect.value) {
    params.set('review_status', reviewStatusSelect.value);
  }
  const response = await fetch(`/admin/api/logs?${params.toString()}`);
  const payload = await response.json();
  renderLogs(payload.logs || []);
}

async function refreshAll() {
  await Promise.all([loadSummary(), loadLogs()]);
}

refreshDashboardButton.addEventListener('click', refreshAll);
reloadLogsButton.addEventListener('click', loadLogs);
flaggedOnlyInput.addEventListener('change', loadLogs);
reviewStatusSelect.addEventListener('change', loadLogs);

refreshAll();

retrainHelpButton.addEventListener('click', () => {
  window.alert(`Run this from the project root after reviewing queries:

./chatbot/.venv/Scripts/python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml`);
});
