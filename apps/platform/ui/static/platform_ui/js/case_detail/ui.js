(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.ui) {
    return;
  }

  const JOB_DETAIL_LOADING =
    '<div class="flex items-center gap-2 text-xs text-slate-300"><svg class="h-3 w-3 animate-spin text-primary-300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle class="opacity-30" cx="12" cy="12" r="10" stroke-width="2"></circle><path d="M22 12a10 10 0 00-10-10" stroke-width="2" stroke-linecap="round"></path></svg><span>Loading…</span></div>';
  const JOB_DETAIL_ERROR = '<div class="text-xs text-rose-300">Unable to load job detail.</div>';

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
    jobsBody.querySelectorAll('[data-job]').forEach((row) => {
      const jobId = row.dataset.job;
      if (!jobId) return;
      if (deps.realtime?.watchJob) {
        deps.realtime.watchJob(jobId);
      } else {
        deps.realtime?.connectSocket(jobId);
        deps.realtime?.ensurePolling(jobId);
      }
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
  }

  function boost(caseIdParam) {
    refreshCaseJobs(caseIdParam || ctx.caseId);
  }

  function getTableController() {
    return tableController;
  }

  caseDetail.ui = {
    setContext,
    setDeps,
    initJobsTable,
    scheduleTranscribeRefresh,
    setActiveCard,
    updateStatusDisplays,
    syncTranscribeSidebar,
    refreshCaseJobs,
    boost,
    getTableController,
  };
})(window);
