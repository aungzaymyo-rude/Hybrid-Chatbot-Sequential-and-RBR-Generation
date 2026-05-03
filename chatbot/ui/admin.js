const metricsGrid = document.getElementById('metrics-grid');
const intentTable = document.getElementById('intent-table');
const flaggedTable = document.getElementById('flagged-table');
const modelTable = document.getElementById('model-table');
const logsList = document.getElementById('logs-list');
const ratesChart = document.getElementById('rates-chart');
const reviewChart = document.getElementById('review-chart');
const intentChart = document.getElementById('intent-chart');
const modelTrafficChart = document.getElementById('model-traffic-chart');
const modelQualityChart = document.getElementById('model-quality-chart');
const modelRoutingChart = document.getElementById('model-routing-chart');
const ingestionMetrics = document.getElementById('ingestion-metrics');
const datasetChart = document.getElementById('dataset-chart');
const labeledFilesTable = document.getElementById('labeled-files-table');
const versioningMetrics = document.getElementById('versioning-metrics');
const certificateMetrics = document.getElementById('certificate-metrics');
const versionTable = document.getElementById('version-table');
const splitPolicyMetrics = document.getElementById('split-policy-metrics');
const splitChart = document.getElementById('split-chart');
const artifactTable = document.getElementById('artifact-table');
const reportAnalysisPreviewTable = document.getElementById('report-analysis-preview-table');
const refreshDashboardButton = document.getElementById('refresh-dashboard');
const reloadLogsButton = document.getElementById('reload-logs');
const flaggedOnlyInput = document.getElementById('flagged-only');
const reviewStatusSelect = document.getElementById('review-status');
const retrainHelpButton = document.getElementById('run-retrain-help');
const modelFilterSelect = document.getElementById('model-filter');
const applyModelFilterButton = document.getElementById('apply-model-filter');
const traceTextInput = document.getElementById('trace-text');
const traceModelSelect = document.getElementById('trace-model');
const runTraceButton = document.getElementById('run-trace');
const traceInputMetrics = document.getElementById('trace-input-metrics');
const tracePreprocess = document.getElementById('trace-preprocess');
const traceRules = document.getElementById('trace-rules');
const traceClassifier = document.getElementById('trace-classifier');
const traceEntity = document.getElementById('trace-entity');
const traceDirectRetrieval = document.getElementById('trace-direct-retrieval');
const traceEntityRetrieval = document.getElementById('trace-entity-retrieval');
const traceRoute = document.getElementById('trace-route');
const sidebarLinks = Array.from(document.querySelectorAll('.sidebar-link'));
const adminViews = Array.from(document.querySelectorAll('.admin-view'));

const MODEL_LABELS = {
  general: 'General Hematology',
  report: 'Report Assistant',
  unassigned: 'Unassigned',
};

function fmtPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function fmtNumber(value) {
  return Number(value || 0).toLocaleString();
}

function fmtDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function fmtPath(value) {
  return value || '-';
}

function friendlyModelLabel(modelKey) {
  return MODEL_LABELS[modelKey] || modelKey || 'Unknown';
}

function activeModelKey() {
  return modelFilterSelect.value || '';
}

function renderMetrics(summary) {
  const cards = [
    ['Active model filter', summary.active_model_key ? friendlyModelLabel(summary.active_model_key) : 'All models'],
    ['Total chats', fmtNumber(summary.total_chats)],
    ['Unique sessions', fmtNumber(summary.unique_sessions)],
    ['Avg confidence', Number(summary.avg_confidence || 0).toFixed(3)],
    ['Fallback rate', fmtPercent(summary.fallback_rate)],
    ['Guardrail rate', fmtPercent(summary.guardrail_rate)],
    ['Low-confidence rate', fmtPercent(summary.low_confidence_rate)],
    ['Retrieval rate', fmtPercent(summary.retrieval_rate)],
    ['Auto-switch rate', fmtPercent(summary.auto_switch_rate)],
    ['Unreviewed logs', fmtNumber(summary.unreviewed_count)],
  ];

  metricsGrid.innerHTML = cards.map(([label, value]) => `
    <article class="metric-card">
      <span class="metric-label">${label}</span>
      <strong class="metric-value">${value}</strong>
    </article>
  `).join('');
}

function renderMiniMetrics(target, rows) {
  target.innerHTML = rows.map((row) => `
    <article class="mini-metric ${row.tone || ''}">
      <span>${row.label}</span>
      <strong>${row.value}</strong>
      ${row.subLabel ? `<small>${row.subLabel}</small>` : ''}
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
      ${row.subLabel ? `<p class="chart-subtext">${row.subLabel}</p>` : ''}
    </div>
  `).join('');
}

function renderRateChart(summary) {
  renderProgressChart(ratesChart, [
    { label: 'Fallback', valueLabel: fmtPercent(summary.fallback_rate), percent: Number(summary.fallback_rate || 0) * 100, tone: 'warn' },
    { label: 'Guardrail', valueLabel: fmtPercent(summary.guardrail_rate), percent: Number(summary.guardrail_rate || 0) * 100, tone: 'warn' },
    { label: 'Low confidence', valueLabel: fmtPercent(summary.low_confidence_rate), percent: Number(summary.low_confidence_rate || 0) * 100, tone: 'danger' },
    { label: 'Retrieval', valueLabel: fmtPercent(summary.retrieval_rate), percent: Number(summary.retrieval_rate || 0) * 100, tone: 'success' },
    { label: 'Auto-switch', valueLabel: fmtPercent(summary.auto_switch_rate), percent: Number(summary.auto_switch_rate || 0) * 100, tone: 'neutral' },
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

function renderModelTrafficChart(rows) {
  const maxCount = Math.max(1, ...rows.map((row) => Number(row.count || 0)));
  renderProgressChart(modelTrafficChart, rows.map((row) => ({
    label: friendlyModelLabel(row.model_key),
    valueLabel: fmtNumber(row.count),
    percent: (Number(row.count || 0) / maxCount) * 100,
    tone: 'success',
    subLabel: `Avg confidence ${Number(row.avg_confidence || 0).toFixed(3)}`,
  })));
}

function renderModelQualityChart(rows) {
  renderProgressChart(modelQualityChart, rows.map((row) => ({
    label: friendlyModelLabel(row.model_key),
    valueLabel: fmtPercent(row.low_confidence_rate),
    percent: Number(row.low_confidence_rate || 0) * 100,
    tone: Number(row.low_confidence_rate || 0) > 0.15 ? 'danger' : 'warn',
    subLabel: `Fallback ${fmtPercent(row.fallback_rate)} | Guardrail ${fmtPercent(row.guardrail_rate)}`,
  })));
}

function renderModelRoutingChart(rows) {
  renderProgressChart(modelRoutingChart, rows.map((row) => ({
    label: friendlyModelLabel(row.model_key),
    valueLabel: `Switch ${fmtPercent(row.auto_switch_rate)}`,
    percent: Number(row.auto_switch_rate || 0) * 100,
    tone: 'neutral',
    subLabel: `Retrieval ${fmtPercent(row.retrieval_rate)}`,
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

function renderModelTable(rows) {
  modelTable.innerHTML = rows.map((row) => `
    <tr>
      <td>${friendlyModelLabel(row.model_key)}</td>
      <td>${fmtNumber(row.count)}</td>
      <td>${Number(row.avg_confidence || 0).toFixed(3)}</td>
      <td>${fmtPercent(row.fallback_rate)}</td>
      <td>${fmtPercent(row.guardrail_rate)}</td>
      <td>${fmtPercent(row.auto_switch_rate)}</td>
      <td>${fmtPercent(row.retrieval_rate)}</td>
    </tr>
  `).join('');
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
        <span class="pill muted">${friendlyModelLabel(log.model_key)}</span>
        <span class="pill muted">${log.review_status}</span>
      </div>
      <p class="log-question">${log.user_text}</p>
      <p class="log-answer">${log.response}</p>
      <dl class="log-meta">
        <div><dt>Created</dt><dd>${fmtDate(log.created_at)}</dd></div>
        <div><dt>Language</dt><dd>${log.detected_lang}</dd></div>
        <div><dt>Entity</dt><dd>${log.entity_label || '-'}</dd></div>
        <div><dt>Retrieval intent</dt><dd>${log.retrieval_intent || '-'}</dd></div>
        <div><dt>Session</dt><dd>${log.session_id || '-'}</dd></div>
        <div><dt>Requested model</dt><dd>${friendlyModelLabel(log.requested_model_key || log.model_key)}</dd></div>
        <div><dt>Answered model</dt><dd>${friendlyModelLabel(log.model_key)}</dd></div>
        <div><dt>Auto-switched</dt><dd>${log.auto_switched ? 'Yes' : 'No'}</dd></div>
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

function renderReportAnalysisPreview(rows) {
  if (!reportAnalysisPreviewTable) return;
  if (!rows.length) {
    reportAnalysisPreviewTable.innerHTML = '<tr><td colspan="5">No report-analysis retry candidates found.</td></tr>';
    return;
  }
  reportAnalysisPreviewTable.innerHTML = rows.map((row) => `
    <tr>
      <td>${row.user_text}</td>
      <td>${row.intent || '-'}</td>
      <td>${row.recommended_analysis_intent || '-'}</td>
      <td>${row.analysis_label || '-'}</td>
      <td>${Number(row.confidence || 0).toFixed(3)}</td>
    </tr>
  `).join('');
}

function renderIngestion(pipeline) {
  const ingestion = pipeline.ingestion || {};
  const datasets = ingestion.datasets || {};
  const datasetRows = [
    { key: 'master', label: 'Master dataset' },
    { key: 'general', label: 'General dataset' },
    { key: 'report', label: 'Report dataset' },
    { key: 'knowledge_base', label: 'Knowledge base' },
  ];

  renderMiniMetrics(ingestionMetrics, [
    { label: 'Labeled files', value: fmtNumber(ingestion.labeled_file_count), subLabel: 'CSV / JSONL sources' },
    { label: 'Labeled rows', value: fmtNumber(ingestion.total_labeled_rows), subLabel: 'Before merge into train pool' },
    { label: 'Master rows', value: fmtNumber(datasets.master?.row_count), subLabel: 'chatbot/data/train/intent_dataset.jsonl' },
    { label: 'Knowledge rows', value: fmtNumber(datasets.knowledge_base?.row_count), subLabel: 'retrieval knowledge entries' },
  ]);

  const maxCount = Math.max(1, ...datasetRows.map((row) => Number(datasets[row.key]?.row_count || 0)));
  renderProgressChart(datasetChart, datasetRows.map((row) => ({
    label: row.label,
    valueLabel: fmtNumber(datasets[row.key]?.row_count || 0),
    percent: (Number(datasets[row.key]?.row_count || 0) / maxCount) * 100,
    tone: row.key === 'knowledge_base' ? 'neutral' : 'success',
    subLabel: `Updated ${fmtDate(datasets[row.key]?.modified_at)}`,
  })));

  labeledFilesTable.innerHTML = (ingestion.labeled_files || []).slice().reverse().map((row) => `
    <tr>
      <td>${row.name}</td>
      <td>${fmtNumber(row.row_count)}</td>
      <td>${fmtDate(row.modified_at)}<br><span class="path-cell">${row.display_path || '-'}</span></td>
    </tr>
  `).join('');
}

function renderVersioning(pipeline) {
  const versioning = pipeline.versioning || {};
  const certificate = versioning.certificate || {};
  renderMiniMetrics(versioningMetrics, [
    { label: 'Default model', value: friendlyModelLabel(versioning.default_model_key), subLabel: 'config default' },
    { label: 'Fallback threshold', value: Number(versioning.fallback_threshold || 0).toFixed(2), subLabel: 'inference threshold' },
    { label: 'Knowledge path', value: 'Configured', subLabel: versioning.knowledge_display_path || '-' },
    { label: 'Split directory', value: 'Configured', subLabel: versioning.split_display_path || '-' },
  ]);

  renderMiniMetrics(certificateMetrics, [
    { label: 'HTTPS mode', value: certificate.https_enabled ? 'Enabled' : 'Disabled', subLabel: certificate.https_enabled ? `Port ${certificate.https_port}` : 'serving HTTP only', tone: certificate.https_enabled ? 'success' : 'neutral' },
    { label: 'HTTP redirect', value: certificate.http_redirect_enabled ? 'Enabled' : 'Disabled', subLabel: certificate.http_redirect_enabled ? `Port ${certificate.http_redirect_port} → ${certificate.https_port}` : 'no redirect listener', tone: certificate.http_redirect_enabled ? 'success' : 'neutral' },
    { label: 'Certificate', value: certificate.status || 'unknown', subLabel: certificate.certfile_display_path || '-', tone: certificate.warning_level || 'neutral' },
    { label: 'Days remaining', value: certificate.days_remaining != null ? fmtNumber(certificate.days_remaining) : '-', subLabel: certificate.is_self_signed === true ? 'self-signed' : (certificate.is_self_signed === false ? 'CA or external issuer' : (certificate.keyfile_display_path || '-')), tone: certificate.warning_level || 'neutral' },
  ]);

  versionTable.innerHTML = (versioning.components || []).map((row) => `
    <tr>
      <td>${row.component}</td>
      <td>${row.version || '-'}</td>
      <td class="path-cell">${fmtPath(row.display_path || row.path)}</td>
    </tr>
  `).join('');
}

function renderSplits(pipeline) {
  const splits = pipeline.splits || {};
  const policy = splits.policy || {};
  const models = splits.models || [];

  renderMiniMetrics(splitPolicyMetrics, [
    { label: 'Train ratio', value: `${Math.round(Number(policy.train_ratio || 0) * 100)}%`, subLabel: 'fit model weights' },
    { label: 'Validation ratio', value: `${Math.round(Number(policy.validation_ratio || 0) * 100)}%`, subLabel: 'select best checkpoint' },
    { label: 'Test ratio', value: `${Math.round(Number(policy.test_ratio || 0) * 100)}%`, subLabel: 'final held-out evaluation' },
    { label: 'Seed', value: fmtNumber(policy.seed), subLabel: 'reproducible splits' },
  ]);

  renderProgressChart(splitChart, models.map((row) => {
    const counts = row.counts || {};
    const trainRows = Number(counts.train?.rows || 0);
    const validationRows = Number(counts.validation?.rows || 0);
    const testRows = Number(counts.test?.rows || 0);
    const total = Math.max(1, trainRows + validationRows + testRows);
    return {
      label: friendlyModelLabel(row.model_key),
      valueLabel: `${fmtNumber(trainRows)} / ${fmtNumber(validationRows)} / ${fmtNumber(testRows)}`,
      percent: (trainRows / total) * 100,
      tone: 'success',
      subLabel: `train / validation / test | ${row.display_path || '-'} | updated ${fmtDate(row.modified_at)}`,
    };
  }));

  artifactTable.innerHTML = (pipeline.models || []).map((row) => `
    <tr>
      <td>${friendlyModelLabel(row.model_key)}<br><span class="path-cell">${row.architecture || '-'} | ${row.display_path || '-'}</span></td>
      <td>${row.version || '-'}</td>
      <td>${row.best_epoch ?? '-'}</td>
      <td>${row.best_f1 != null ? Number(row.best_f1).toFixed(4) : '-'}</td>
      <td>${fmtNumber(row.train_size)} / ${fmtNumber(row.validation_size)}</td>
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

function buildQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      query.set(key, value);
    }
  });
  return query.toString();
}

function populateModelFilter(modelsPayload) {
  const models = modelsPayload.models || {};
  modelFilterSelect.innerHTML = '<option value="">All deployed models</option>';
  traceModelSelect.innerHTML = '<option value="">Use current default model</option>';
  Object.entries(models).forEach(([key, entry]) => {
    const option = document.createElement('option');
    const version = entry.version ? ` (${entry.version})` : '';
    option.value = key;
    option.textContent = `${friendlyModelLabel(key)}${version}`;
    modelFilterSelect.appendChild(option);
    traceModelSelect.appendChild(option.cloneNode(true));
  });
}

function bindSidebarNavigation() {
  function activateSection(sectionId) {
    sidebarLinks.forEach((button) => {
      button.classList.toggle('active', button.dataset.section === sectionId);
    });
    adminViews.forEach((view) => {
      view.classList.toggle('active', view.id === sectionId);
    });
    if (window.location.hash !== `#${sectionId}`) {
      history.replaceState(null, '', `#${sectionId}`);
    }
  }

  sidebarLinks.forEach((button) => {
    button.addEventListener('click', () => {
      activateSection(button.dataset.section);
    });
  });

  const initialSection = window.location.hash.replace('#', '');
  const knownSection = adminViews.some((view) => view.id === initialSection);
  activateSection(knownSection ? initialSection : 'overview-section');
}

async function loadModels() {
  const response = await fetch('/models');
  const payload = await response.json();
  populateModelFilter(payload);
}

async function loadPipeline() {
  const response = await fetch('/admin/api/pipeline');
  const payload = await response.json();
  renderIngestion(payload);
  renderVersioning(payload);
  renderSplits(payload);
}

function renderTraceDetail(target, rows) {
  target.innerHTML = rows.map((row) => `
    <article class="trace-block">
      <h3>${row.title}</h3>
      <p>${row.body}</p>
    </article>
  `).join('');
}

function renderTokenMap(tokenMap) {
  if (!tokenMap.length) {
    return '<article class="trace-block"><h3>Tokens</h3><p>No tokens generated.</p></article>';
  }
  return `
    <article class="trace-block">
      <h3>Tokens and IDs</h3>
      <div class="trace-inline-list">
        ${tokenMap.map((item) => `<span class="trace-token ${item.known ? '' : 'unknown'}">${item.token} → ${item.id}</span>`).join('')}
      </div>
    </article>
  `;
}

function renderRetrievalChart(target, rows) {
  if (!rows.length) {
    target.innerHTML = '<article class="trace-block"><p>No candidates for this path.</p></article>';
    return;
  }
  const maxScore = Math.max(0.0001, ...rows.map((row) => Number(row.score || 0)));
  renderProgressChart(target, rows.map((row) => ({
    label: row.question,
    valueLabel: Number(row.score || 0).toFixed(3),
    percent: (Number(row.score || 0) / maxScore) * 100,
    tone: Number(row.score || 0) >= 0.18 ? 'success' : 'warn',
    subLabel: row.intent,
  })));
}

function renderTrace(payload) {
  renderMiniMetrics(traceInputMetrics, [
    { label: 'Requested model', value: friendlyModelLabel(payload.input.requested_model_key), subLabel: 'from trace form' },
    { label: 'Effective model', value: friendlyModelLabel(payload.input.effective_model_key), subLabel: payload.input.model_version || 'active runtime' },
    { label: 'Auto-switch', value: payload.input.auto_switched ? 'Yes' : 'No', subLabel: payload.input.advisory_message || 'no model switch' },
    { label: 'Language', value: payload.preprocessing.language || '-', subLabel: 'detected language' },
  ]);

  tracePreprocess.innerHTML = `
    <article class="trace-block">
      <h3>Normalized text</h3>
      <p>${payload.preprocessing.normalized_text || '-'}</p>
    </article>
    ${renderTokenMap(payload.preprocessing.token_map || [])}
  `;

  if (payload.rules.matched && payload.rules.details) {
    renderTraceDetail(traceRules, [
      {
        title: `Rule matched: ${payload.rules.details.intent}`,
        body: `Stage: ${payload.rules.details.stage}. Matched pattern: ${payload.rules.details.matched_pattern}. The sequential classifier was bypassed for this request.`,
      },
    ]);
  } else {
    renderTraceDetail(traceRules, [
      {
        title: 'No hard rule matched',
        body: 'The phrase continued to the sequential BiLSTM classifier because no greeting, small-talk, incomplete-query, unsafe, or language gate rule was triggered.',
      },
    ]);
  }

  const topPredictions = payload.classifier.top_predictions || [];
  if (!topPredictions.length) {
    traceClassifier.innerHTML = '<article class="trace-block"><p>No classifier probabilities because a rule handled the request before the model stage.</p></article>';
  } else {
    renderProgressChart(traceClassifier, topPredictions.map((row) => ({
      label: row.intent,
      valueLabel: Number(row.confidence || 0).toFixed(3),
      percent: Number(row.confidence || 0) * 100,
      tone: row.intent === payload.classifier.final_intent ? 'success' : 'neutral',
      subLabel: `threshold ${Number(payload.classifier.threshold || 0).toFixed(2)}`,
    })));
  }

  const domainAssist = payload.classifier.domain_assist;
  if (domainAssist?.applied) {
    traceClassifier.insertAdjacentHTML('beforeend', `
      <article class="trace-block">
        <h3>Domain assist applied</h3>
        <p>The base classifier fell below threshold for this phrase, so the report-analysis layer promoted the final intent from ${domainAssist.base_intent} to ${domainAssist.assisted_intent}. This keeps numeric report phrases and printed report flags inside the report-analysis path.</p>
      </article>
    `);
  }

  if (payload.entity_detection.matched) {
    renderTraceDetail(traceEntity, [
      {
        title: `Entity: ${payload.entity_detection.label}`,
        body: `Mapped to intent ${payload.entity_detection.intent} using canonical question "${payload.entity_detection.canonical_question}".`,
      },
    ]);
  } else {
    renderTraceDetail(traceEntity, [
      {
        title: 'No entity match',
        body: 'No hematology entity rule matched the phrase, so retrieval could only use the predicted intent path.',
      },
    ]);
  }

  renderRetrievalChart(traceDirectRetrieval, payload.retrieval.direct_candidates || []);
  renderRetrievalChart(traceEntityRetrieval, payload.retrieval.entity_candidates || []);

  renderTraceDetail(traceRoute, [
    {
      title: `Final route: ${payload.route.source}`,
      body: payload.route.explanation,
    },
    {
      title: 'Final response',
      body: payload.route.final_response,
    },
    {
      title: 'Route metadata',
      body: `Intent ${payload.classifier.final_intent} | confidence ${Number(payload.classifier.final_confidence || 0).toFixed(3)} | retrieval intent ${payload.route.retrieval_intent || '-'} | retrieval question ${payload.route.retrieval_question || '-'} | entity ${payload.route.entity_label || '-'}.`,
    },
  ]);
}

async function runTrace() {
  const text = traceTextInput.value.trim();
  if (!text) {
    window.alert('Enter a phrase to trace.');
    return;
  }
  const response = await fetch('/admin/api/trace', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      model_key: traceModelSelect.value || null,
    }),
  });
  const payload = await response.json();
  renderTrace(payload);
}

async function loadSummary() {
  const response = await fetch(`/admin/api/summary?${buildQuery({ model_key: activeModelKey() })}`);
  const payload = await response.json();
  renderMetrics(payload.summary);
  renderRateChart(payload.summary);
  renderReviewChart(payload.summary);
  renderIntentChart(payload.intent_breakdown || []);
  renderIntentTable(payload.intent_breakdown || []);
  renderFlaggedTable(payload.flagged_phrases || []);
  renderModelTable(payload.model_breakdown || []);
  renderModelTrafficChart(payload.model_breakdown || []);
  renderModelQualityChart(payload.model_breakdown || []);
  renderModelRoutingChart(payload.model_breakdown || []);
}

async function loadLogs() {
  const response = await fetch(`/admin/api/logs?${buildQuery({
    limit: '60',
    flagged_only: flaggedOnlyInput.checked ? 'true' : '',
    review_status: reviewStatusSelect.value,
    model_key: activeModelKey(),
  })}`);
  const payload = await response.json();
  renderLogs(payload.logs || []);
}

async function loadReportAnalysisPreview() {
  const response = await fetch('/admin/api/report-analysis-preview');
  const payload = await response.json();
  renderReportAnalysisPreview(payload.rows || []);
}

async function refreshAll() {
  await Promise.all([loadPipeline(), loadSummary(), loadLogs(), loadReportAnalysisPreview()]);
}

refreshDashboardButton.addEventListener('click', refreshAll);
reloadLogsButton.addEventListener('click', loadLogs);
flaggedOnlyInput.addEventListener('change', loadLogs);
reviewStatusSelect.addEventListener('change', loadLogs);
applyModelFilterButton.addEventListener('click', refreshAll);
modelFilterSelect.addEventListener('change', refreshAll);

retrainHelpButton.addEventListener('click', () => {
  window.alert(`Run this from the project root after reviewing queries:

./chatbot/.venv/Scripts/python.exe chatbot/training/retrain_from_reviews.py --config chatbot/config.yaml`);
});
runTraceButton.addEventListener('click', runTrace);

(async function init() {
  bindSidebarNavigation();
  await loadModels();
  await refreshAll();
  traceTextInput.value = 'What is aPTT?';
  await runTrace();
})();
