(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.ui) {
    return;
  }

  const JOB_DETAIL_LOADING =
    '<div class="flex items-center gap-2 text-xs text-slate-300"><svg class="h-3 w-3 animate-spin text-primary-300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle class="opacity-30" cx="12" cy="12" r="10" stroke-width="2"></circle><path d="M22 12a10 10 0 00-10-10" stroke-width="2" stroke-linecap="round"></path></svg><span>Loading…</span></div>';
  const JOB_DETAIL_ERROR = '<div class="text-xs text-rose-300">Unable to load job detail.</div>';
  const REVIEW_BADGE_CLASSES = {
    APPROVED:
      'inline-flex items-center rounded-full border border-emerald-400/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-200',
    REJECTED:
      'inline-flex items-center rounded-full border border-rose-400/40 bg-rose-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-rose-200',
    PENDING:
      'inline-flex items-center rounded-full border border-white/20 bg-white/5 px-2 py-0.5 text-[10px] font-semibold uppercase text-slate-300',
  };

  const BASE_ANALYZE_STAGE_ORDER = [
    'pipeline',
    'input_discovery',
    'parse_transcript',
    'context_builder',
    'extract_outline',
    'build_timeline_seeds',
    'build_entity_hints',
    'draft_markdown',
    'qa_and_finalize',
  ];
  const ANALYZE_STAGE_LABELS = {
    pipeline: 'Pipeline',
    input_discovery: 'Input discovery',
    parse_transcript: 'Parse transcript',
    context_builder: 'Context builder',
    extract_outline: 'Outline',
    build_timeline_seeds: 'Timeline seeds',
    build_entity_hints: 'Entity hints',
    draft_markdown: 'Draft summary',
    qa_and_finalize: 'QA and finalize',
  };
  const ANALYZE_STATUS_PRESENTATION = {
    pending: { label: 'Pending', className: 'text-slate-400' },
    ready: { label: 'Ready', className: 'text-amber-300' },
    running: { label: 'Running', className: 'text-primary-300' },
    complete: { label: 'Complete', className: 'text-emerald-300' },
    failed: { label: 'Failed', className: 'text-rose-300' },
  };

  let ctx = null;
  let deps = {};
  let tableController = null;
  let transcribeSidebarBinding = null;
  let analyzeStageOrder = BASE_ANALYZE_STAGE_ORDER.slice();
  let analyzeProgressJobId = null;
  let analyzePipelineStatus = 'Idle';
  const analyzeStageState = new Map();

  function setContext(value) {
    ctx = value;
    renderAnalyzeProgress();
  }

  function setDeps(value) {
    deps = value || {};
  }

  function initJobsTable() {
    if (!ctx || !ctx.caseView) return null;
    const jobsTableApi = ctx.jobsTableApi;
    if (!jobsTableApi || typeof jobsTableApi.init !== 'function') {
      console.warn('platformUI.jobsTable.init is required for case detail interactions');
      return null;
    }

    tableController = jobsTableApi.init({
      root: ctx.caseView,
      activeRowClass: 'bg-white/10',
      detailRowSelector: (jobId) => `[data-job-detail="${jobId}"]`,
      detailContainerSelector: (jobId) => `[data-job-detail-container="${jobId}"]`,
      loadingTemplate: JOB_DETAIL_LOADING,
      errorTemplate: JOB_DETAIL_ERROR,
      loadDetail: async (jobId, container) => {
        const resp = await fetch(`/cases/${ctx.caseId}/jobs/${jobId}/detail/`, {
          headers: { 'HX-Request': 'true' },
          credentials: 'same-origin',
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const html = await resp.text();
        container.innerHTML = html;
      },
      onAfterExpand: (row) => {
        if (!row) return;
        const chevron = row.querySelector('[data-job-chevron]');
        if (chevron) chevron.classList.add('rotate-90');
      },
      onCollapse: (row) => {
        if (!row) return;
        const chevron = row.querySelector('[data-job-chevron]');
        if (chevron) chevron.classList.remove('rotate-90');
      },
    });

    ctx.jobsState.table = tableController;
    return tableController;
  }

  function scheduleTranscribeRefresh(preferredTool) {
    if (!ctx || !ctx.jobsState.currentCaseId) return;
    const activeAttr = ctx.caseView ? ctx.caseView.getAttribute('data-active-tool') : '';
    const initialTool = ctx.initialToolKey || '';
    const chosen = (preferredTool || activeAttr || initialTool || 'transcribe').toString().trim();
    const targetTool = chosen || 'transcribe';
    ctx.jobsState.pendingToolRefresh = targetTool;
    if (ctx.jobsState.refreshTranscribeScheduled) return;
    ctx.jobsState.refreshTranscribeScheduled = true;
    setTimeout(() => {
      ctx.jobsState.refreshTranscribeScheduled = false;
      const nextCaseId = ctx.jobsState.currentCaseId;
      if (!nextCaseId) return;
      const nextTool = ctx.jobsState.pendingToolRefresh || targetTool;
      ctx.jobsState.pendingToolRefresh = null;
      const normalizedTool = (nextTool || '').trim() || 'transcribe';
      const url = `/cases/${nextCaseId}/tools/${encodeURIComponent(normalizedTool)}/`;
      if (global.htmx && typeof global.htmx.ajax === 'function') {
        global.htmx.ajax('GET', url, '#tool-workspace');
        return;
      }
      fetch(url, { headers: { 'HX-Request': 'true' }, credentials: 'same-origin' })
        .then((resp) => (resp.ok ? resp.text() : null))
        .then((html) => {
          if (!html) return;
          const workspaceEl = ctx.workspace || global.document.getElementById('tool-workspace');
          if (workspaceEl) {
            workspaceEl.innerHTML = html;
            if (deps.onTranscribeRefresh) {
              deps.onTranscribeRefresh(normalizedTool);
            }
          }
        })
        .catch(() => {});
    }, 150);
  }

  function setActiveCard(key) {
    if (!ctx) return;
    global.document.querySelectorAll('[data-tool-card]').forEach((card) => {
      const match = card.getAttribute('data-tool-card') === key;
      card.classList.toggle('border-primary-400', match);
      card.classList.toggle('bg-slate-900/70', match);
      card.setAttribute('aria-pressed', match ? 'true' : 'false');
    });
    ctx.caseView.setAttribute('data-active-tool', key || '');
    if (key) {
      global.history.replaceState({}, '', `?tool=${encodeURIComponent(key)}`);
    } else {
      global.history.replaceState({}, '', global.location.pathname);
    }
  }

  function updateStatusDisplays(jobId, status, progress) {
    if (!ctx) return;
    const renderStatusLabel = ctx.statusUtils.renderStatusLabel || (() => {});
    const statusCell = global.document.getElementById(`job-status-${jobId}`);
    if (statusCell) {
      renderStatusLabel(statusCell, status, progress);
    }
    const jobRow = global.document.querySelector(`[data-job="${jobId}"]`);
    if (jobRow) {
      jobRow.classList.remove(
        'bg-emerald-500/10',
        'bg-rose-500/10',
        'bg-amber-500/10',
        'bg-primary-500/10',
        'bg-white/5',
      );
    }
    if (ctx.jobActions && typeof ctx.jobActions.updateForRow === 'function') {
      ctx.jobActions.updateForRow(jobId, status);
    }
    const detailContainer = global.document.querySelector(`[data-job-detail="${jobId}"]`);
    if (!detailContainer) return;
    const pill = detailContainer.querySelector('[data-job-status-pill]');
    if (pill) {
      renderStatusLabel(pill, status, progress);
    }
  }

  function normalizeStageKey(value) {
    return (value || '').toString().trim().toLowerCase();
  }

  function statusForEvent(eventName) {
    const normalized = normalizeStageKey(eventName);
    if (!normalized) return null;
    if (normalized === 'configured') return 'ready';
    if (normalized === 'start') return 'running';
    if (normalized === 'complete') return 'complete';
    if (normalized === 'failure' || normalized === 'failed' || normalized === 'error') return 'failed';
    return null;
  }

  function ensureAnalyzeProgressElements() {
    if (!ctx || !ctx.caseView) return null;
    const panel = ctx.caseView.querySelector('[data-analyze-progress-panel]');
    if (!panel) return null;
    const list = panel.querySelector('[data-analyze-progress-list]');
    const statusEl = panel.querySelector('[data-analyze-progress-status]');
    if (!list || !statusEl) return null;
    return { panel, list, statusEl };
  }

  function resetAnalyzeStageState() {
    analyzeStageState.clear();
    analyzeStageOrder = BASE_ANALYZE_STAGE_ORDER.slice();
    const timestamp = Date.now();
    analyzeStageOrder.forEach((stageKey) => {
      analyzeStageState.set(stageKey, { status: 'pending', message: '', updatedAt: timestamp });
    });
    analyzePipelineStatus = 'Queued';
  }

  function stageLabel(stageKey) {
    if (Object.prototype.hasOwnProperty.call(ANALYZE_STAGE_LABELS, stageKey)) {
      return ANALYZE_STAGE_LABELS[stageKey];
    }
    return stageKey.replace(/[_-]/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function renderAnalyzeProgress() {
    const elements = ensureAnalyzeProgressElements();
    if (!elements) return;
    const { panel, list, statusEl } = elements;
    if (!analyzeProgressJobId) {
      panel.classList.add('hidden');
      list.innerHTML = '';
      statusEl.textContent = 'Idle';
      return;
    }
    panel.classList.remove('hidden');
    statusEl.textContent = analyzePipelineStatus;
    const fragment = global.document.createDocumentFragment();
    analyzeStageOrder.forEach((stageKey) => {
      const state = analyzeStageState.get(stageKey);
      if (!state) return;
      const item = global.document.createElement('li');
      item.className = 'rounded-lg border border-white/10 bg-slate-900/60 px-3 py-2';
      const header = global.document.createElement('div');
      header.className = 'flex items-center justify-between text-[11px] uppercase tracking-wide';
      const labelEl = global.document.createElement('span');
      labelEl.className = 'text-slate-300';
      labelEl.textContent = stageLabel(stageKey);
      header.appendChild(labelEl);
      const presentation = ANALYZE_STATUS_PRESENTATION[state.status] || ANALYZE_STATUS_PRESENTATION.pending;
      const statusBadge = global.document.createElement('span');
      statusBadge.className = `font-semibold ${presentation.className}`;
      statusBadge.textContent = presentation.label;
      header.appendChild(statusBadge);
      item.appendChild(header);
      if (state.message) {
        const messageEl = global.document.createElement('p');
        messageEl.className = 'mt-1 text-[11px] text-slate-400';
        messageEl.textContent = state.message;
        item.appendChild(messageEl);
      }
      fragment.appendChild(item);
    });
    list.innerHTML = '';
    list.appendChild(fragment);
  }

  function setAnalyzeActiveJob(jobId) {
    if (!jobId) return;
    analyzeProgressJobId = String(jobId);
    resetAnalyzeStageState();
    renderAnalyzeProgress();
  }

  function updateAnalyzeProgress(jobId, payload) {
    if (!analyzeProgressJobId || String(jobId) !== analyzeProgressJobId) return;
    const stageKeyRaw = normalizeStageKey(payload && payload.stage);
    if (!stageKeyRaw) return;
    if (!analyzeStageState.has(stageKeyRaw)) {
      analyzeStageState.set(stageKeyRaw, { status: 'pending', message: '', updatedAt: Date.now() });
      if (!analyzeStageOrder.includes(stageKeyRaw)) {
        analyzeStageOrder.push(stageKeyRaw);
      }
    }
    const state = analyzeStageState.get(stageKeyRaw);
    if (!state) return;
    const nextStatus = statusForEvent(payload && payload.stage_event);
    if (nextStatus) {
      const previousStatus = state.status;
      state.status = nextStatus;
      state.updatedAt = Date.now();
    }
    const detailPayload = payload && typeof payload.details === 'object' && payload.details !== null ? payload.details : {};
    let message = '';
    if (detailPayload) {
      if (typeof detailPayload.error === 'string' && detailPayload.error.trim()) {
        message = detailPayload.error.trim();
      } else if (typeof detailPayload.reason === 'string' && detailPayload.reason.trim()) {
        message = detailPayload.reason.trim();
      } else if (typeof detailPayload.message === 'string' && detailPayload.message.trim()) {
        message = detailPayload.message.trim();
      }
    }
    if (message) {
      state.message = message;
    }
    if (stageKeyRaw === 'pipeline' && nextStatus) {
      if (nextStatus === 'complete') {
        analyzePipelineStatus = 'Complete';
      } else if (nextStatus === 'failed') {
        analyzePipelineStatus = 'Failed';
        const pipelineMessage =
          message || 'Analyze pipeline failed. Review the job log for more details.';
        if (deps.notify) {
          deps.notify({
            type: 'error',
            message: `Analyze pipeline failed: ${pipelineMessage}`,
          });
        }
      } else if (nextStatus === 'running') {
        analyzePipelineStatus = 'Running';
      } else if (nextStatus === 'ready') {
        analyzePipelineStatus = 'Ready';
      } else {
        analyzePipelineStatus = 'Pending';
      }
    } else if (nextStatus === 'failed') {
      analyzePipelineStatus = 'Failed';
    }
    if (nextStatus === 'failed' && previousStatus !== 'failed' && stageKeyRaw !== 'pipeline') {
      const label = stageLabel(stageKeyRaw);
      const detailMessage =
        message || `The ${label.toLowerCase()} stage encountered an error. Review the job log for details.`;
      if (deps.notify) {
        deps.notify({
          type: 'error',
          message: `${label} failed: ${detailMessage}`,
        });
      }
    }
    renderAnalyzeProgress();
  }

  function handleAnalyzeJobStatus(jobId, status) {
    if (!analyzeProgressJobId || String(jobId) !== analyzeProgressJobId) return;
    const normalized = (status || '').toString().trim().toUpperCase();
    if (!normalized) return;
    const pipelineState = analyzeStageState.get('pipeline');
    if (normalized === 'SUCCEEDED') {
      analyzePipelineStatus = 'Complete';
      if (pipelineState) {
        pipelineState.status = 'complete';
      }
    } else if (normalized === 'FAILED' || normalized === 'ERROR' || normalized === 'CANCELLED') {
      analyzePipelineStatus = 'Failed';
      if (pipelineState) {
        pipelineState.status = 'failed';
      }
    }
    renderAnalyzeProgress();
  }

  function normalizeReviewStatus(value) {
    const status = (value || '').toString().toUpperCase();
    if (status === 'APPROVED' || status === 'REJECTED') {
      return status;
    }
    return 'PENDING';
  }

  function formatReviewTimestamp(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return '';
    }
    try {
      return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
    } catch (_) {
      return date.toISOString().replace('T', ' ').split('.')[0];
    }
  }

  function updateReviewDisplays(jobId, payload) {
    if (!ctx || !jobId) return;
    const normalized = normalizeReviewStatus(payload && payload.review_status);
    const label = normalized === 'APPROVED' ? 'Approved' : normalized === 'REJECTED' ? 'Rejected' : 'Pending';
    const comment = payload && typeof payload.review_comment === 'string' ? payload.review_comment.trim() : '';
    const reviewer = payload && typeof payload.reviewed_by === 'string' ? payload.reviewed_by.trim() : '';
    const reviewedAt = formatReviewTimestamp(payload && payload.reviewed_at);

    const row = global.document.querySelector(`[data-job="${jobId}"]`);
    if (row) {
      row.dataset.reviewStatus = normalized;
      row.setAttribute('data-review-status', normalized);
      row.dataset.tableValueReviewStatus = normalized;
      row.dataset.tableValueReview = normalized;
    }

    const badge = global.document.getElementById(`job-review-badge-${jobId}`);
    if (badge) {
      badge.className = REVIEW_BADGE_CLASSES[normalized] || REVIEW_BADGE_CLASSES.PENDING;
      badge.textContent = label;
    }

    const approveDisabled = normalized === 'APPROVED';
    const rejectDisabled = normalized === 'REJECTED';
    global.document.querySelectorAll(`[data-job-approve="${jobId}"]`).forEach((button) => {
      if (button && button.dataset.reviewLoading === '1') return;
      button.disabled = approveDisabled;
    });
    global.document.querySelectorAll(`[data-job-reject="${jobId}"]`).forEach((button) => {
      if (button && button.dataset.reviewLoading === '1') return;
      button.disabled = rejectDisabled;
    });

    const summaries = global.document.querySelectorAll(
      `[data-job-detail-container="${jobId}"] [data-review-summary]`,
    );
    summaries.forEach((summary) => {
      const statusEl = summary.querySelector('[data-review-status-text]');
      if (statusEl) {
        statusEl.textContent = label;
      }
      const commentEl = summary.querySelector('[data-review-comment]');
      if (commentEl) {
        commentEl.textContent = comment || 'No review notes yet.';
      }
      const metaEl = summary.querySelector('[data-review-meta]');
      if (metaEl) {
        if (reviewer || reviewedAt) {
          metaEl.textContent = '';
          if (reviewer) {
            metaEl.appendChild(global.document.createTextNode('Reviewed by '));
            const name = global.document.createElement('span');
            name.className = 'font-semibold text-slate-100';
            name.textContent = reviewer;
            metaEl.appendChild(name);
          }
          if (reviewedAt) {
            if (metaEl.childNodes.length) {
              metaEl.appendChild(global.document.createTextNode(' · '));
            }
            const timeText = global.document.createElement('span');
            timeText.textContent = reviewedAt;
            metaEl.appendChild(timeText);
          }
        } else {
          metaEl.textContent = 'Awaiting reviewer decision.';
        }
      }
    });
  }

  function resetSidebarBinding() {
    if (!transcribeSidebarBinding) return;
    global.removeEventListener('resize', transcribeSidebarBinding.onResize);
    if (transcribeSidebarBinding.mediaQuery && transcribeSidebarBinding.onMediaChange) {
      const registeredQuery = transcribeSidebarBinding.mediaQuery;
      if (registeredQuery.removeEventListener) {
        registeredQuery.removeEventListener('change', transcribeSidebarBinding.onMediaChange);
      } else if (registeredQuery.removeListener) {
        registeredQuery.removeListener(transcribeSidebarBinding.onMediaChange);
      }
    }
    if (transcribeSidebarBinding.observer) {
      transcribeSidebarBinding.observer.disconnect();
    }
    if (transcribeSidebarBinding.sidebar) {
      transcribeSidebarBinding.sidebar.style.maxHeight = '';
    }
    transcribeSidebarBinding = null;
  }

  function syncTranscribeSidebar(root) {
    if (!ctx) return;
    const container = root && root.closest ? root.closest('[data-transcribe]') || root : root;
    if (!container) return;
    const formPanel = container.querySelector('[data-transcribe-form-panel]');
    const sidebar = container.querySelector('[data-transcript-sidebar]');
    if (!formPanel || !sidebar) return;

    resetSidebarBinding();

    const mediaQuery = global.matchMedia('(min-width: 1024px)');
    const apply = () => {
      if (!global.document.body.contains(formPanel) || !global.document.body.contains(sidebar)) {
        resetSidebarBinding();
        return;
      }
      if (mediaQuery.matches) {
        const height = formPanel.getBoundingClientRect().height;
        sidebar.style.maxHeight = `${Math.max(320, Math.round(height))}px`;
      } else {
        sidebar.style.maxHeight = '';
      }
    };

    const onResize = () => apply();
    global.addEventListener('resize', onResize, { passive: true });
    let observer = null;
    if (global.ResizeObserver) {
      observer = new global.ResizeObserver(() => apply());
      observer.observe(formPanel);
    }
    const onMediaChange = () => apply();
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', onMediaChange);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(onMediaChange);
    }
    apply();
    transcribeSidebarBinding = {
      onResize,
      observer,
      mediaQuery,
      onMediaChange,
      sidebar,
    };
  }

  function refreshCaseJobs(caseIdParam) {
    if (!ctx) return;
    if (caseIdParam) {
      ctx.jobsState.currentCaseId = caseIdParam;
    }
    const root = global.document.querySelector('#tool-workspace');
    if (!root) return;

    const transcribeSection = root.querySelector('[data-transcribe]') || root;
    deps.actions?.setupTranscribeSection(transcribeSection);
    deps.actions?.setupAnalysisActions(root);

    const jobsBody = root.querySelector('#jobs-body');
    if (!jobsBody) return;
    jobsBody.querySelectorAll('[data-job-detail]').forEach((detail) => {
      const jobId = detail.getAttribute('data-job-detail');
      const row = jobId ? jobsBody.querySelector(`[data-job="${jobId}"]`) : null;
      if (row && row.getAttribute('aria-expanded') === 'true') {
        detail.classList.remove('hidden');
        detail.style.display = 'table-row';
      } else {
        detail.classList.add('hidden');
        detail.style.display = 'none';
      }
    });
    const caseAttr = jobsBody.dataset.caseId;
    if (caseAttr && caseAttr !== ctx.jobsState.currentCaseId) {
      ctx.jobsState.currentCaseId = caseAttr;
    }
    const visibleJobIds = [];
    jobsBody.querySelectorAll('[data-job]').forEach((row) => {
      const jobId = row.dataset.job;
      if (!jobId) return;
      visibleJobIds.push(jobId);
      if (deps.realtime?.watchJob) {
        deps.realtime.watchJob(jobId);
      }
      deps.realtime?.ensurePolling?.(jobId);
      const statusEl = global.document.getElementById(`job-status-${jobId}`);
      if (statusEl) {
        const statusValue = statusEl.dataset && statusEl.dataset.status ? statusEl.dataset.status : statusEl.textContent;
        const progressValue = statusEl.dataset && statusEl.dataset.progress ? parseFloat(statusEl.dataset.progress) : undefined;
        const renderStatusLabel = ctx.statusUtils.renderStatusLabel || (() => {});
        renderStatusLabel(statusEl, statusValue, progressValue);
        if (ctx.jobActions && typeof ctx.jobActions.updateForRow === 'function') {
          ctx.jobActions.updateForRow(jobId, statusValue);
        }
      }
    });
    renderAnalyzeProgress();
    deps.realtime?.syncJobs?.(visibleJobIds);
  }

  function boost(caseIdParam) {
    refreshCaseJobs(caseIdParam || ctx.caseId);
  }

  function getTableController() {
    return tableController;
  }

  function updateNotesIndicator(jobId, count) {
    if (!ctx) return;
    const row = global.document.querySelector(`[data-job="${jobId}"]`);
    if (!row) return;
    const cell = row.querySelector('[data-job-notes-cell]');
    if (!cell) return;
    const value = Number(count) || 0;
    if (value <= 0) {
      cell.innerHTML = '<span class="text-slate-500" data-job-notes-indicator data-count="0">—</span>';
      return;
    }
    const srText = `${value} team note${value === 1 ? '' : 's'}`;
    const countMarkup = value > 1 ? `<span data-job-notes-count>${value}</span>` : '';
    cell.innerHTML = `
      <span class="inline-flex items-center gap-1 rounded-full border border-primary-400/40 bg-primary-500/10 px-2 py-0.5 text-[11px] font-semibold text-primary-100" data-job-notes-indicator data-count="${value}" title="Team notes available">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path d="M4.5 2A2.5 2.5 0 002 4.5v8A2.5 2.5 0 004.5 15H7v2.382a.5.5 0 00.816.387L11.25 15H15.5A2.5 2.5 0 0018 12.5v-8A2.5 2.5 0 0015.5 2h-11z" />
        </svg>
        ${countMarkup}
        <span class="sr-only">${srText}</span>
      </span>
    `;
  }

  caseDetail.ui = {
    setContext,
    setDeps,
    initJobsTable,
    scheduleTranscribeRefresh,
    setActiveCard,
    setAnalyzeActiveJob,
    updateAnalyzeProgress,
    handleAnalyzeJobStatus,
    updateStatusDisplays,
    updateNotesIndicator,
    syncTranscribeSidebar,
    refreshCaseJobs,
    boost,
    getTableController,
    updateReviewDisplays,
  };
})(window);
