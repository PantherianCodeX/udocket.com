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

  let ctx = null;
  let deps = {};
  let tableController = null;
  let transcribeSidebarBinding = null;

  function setContext(value) {
    ctx = value;
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

  function scheduleTranscribeRefresh() {
    if (!ctx || !ctx.jobsState.currentCaseId) return;
    if (ctx.jobsState.refreshTranscribeScheduled) return;
    ctx.jobsState.refreshTranscribeScheduled = true;
    setTimeout(() => {
      ctx.jobsState.refreshTranscribeScheduled = false;
      const url = `/cases/${ctx.jobsState.currentCaseId}/tools/transcribe/`;
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
              deps.onTranscribeRefresh();
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
    updateStatusDisplays,
    updateNotesIndicator,
    syncTranscribeSidebar,
    refreshCaseJobs,
    boost,
    getTableController,
    updateReviewDisplays,
  };
})(window);
