(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  if (platformUI.jobsTable) return;

  const INTERACTIVE_SELECTOR = 'a, button, input, textarea, select, [role="button"], [data-job-action-menu], [data-popover]';

  function defaultDetailSelector(jobId) {
    return `[data-job-detail="${jobId}"]`;
  }

  function defaultContainerSelector(jobId) {
    return `[data-job-detail-container="${jobId}"]`;
  }

  function applyActiveState(row, expanded, activeClass) {
    if (!row) return;
    row.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    if (activeClass) {
      row.classList.toggle(activeClass, expanded);
    }
    const chevron = row.querySelector('[data-job-chevron]');
    if (chevron) {
      chevron.classList.toggle('rotate-90', expanded);
    }
  }

  function hideDetail(detailRow) {
    if (!detailRow) return;
    detailRow.classList.add('hidden');
    detailRow.style.display = 'none';
  }

  function showDetail(detailRow) {
    if (!detailRow) return;
    detailRow.classList.remove('hidden');
    detailRow.style.display = 'table-row';
  }

  function resolveLoadDetail(options) {
    const loader = options.loadDetail;
    if (typeof loader === 'function') {
      return loader;
    }
    return async () => {};
  }

  function getDetailRow(jobId, options) {
    const selector = (options.detailRowSelector || defaultDetailSelector)(jobId);
    return options.root.querySelector(selector);
  }

  function getDetailContainer(jobId, options) {
    const selector = (options.detailContainerSelector || defaultContainerSelector)(jobId);
    return options.root.querySelector(selector);
  }

  function collapseAll(state) {
    state.expandedRows.forEach((row) => {
      const jobId = row.dataset.job;
      const detailRow = getDetailRow(jobId, state.options);
      hideDetail(detailRow);
      applyActiveState(row, false, state.options.activeRowClass);
      if (typeof state.options.onCollapse === 'function') {
        state.options.onCollapse(row, detailRow);
      }
    });
    state.expandedRows.clear();
  }

  async function expandRow(row, state) {
    const jobId = row.dataset.job;
    if (!jobId) return;
    const detailRow = getDetailRow(jobId, state.options);
    const container = getDetailContainer(jobId, state.options);
    if (!detailRow || !container) return;

    if (typeof state.options.onBeforeExpand === 'function') {
      state.options.onBeforeExpand(row, detailRow);
    }

    if (!container.dataset.loaded) {
      if (!container.dataset.loading) {
        container.dataset.loading = '1';
        container.innerHTML = state.options.loadingTemplate || '<div class="flex items-center gap-2 text-xs text-slate-300"><svg class="h-3 w-3 animate-spin text-primary-300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle class="opacity-30" cx="12" cy="12" r="10" stroke-width="2"></circle><path d="M22 12a10 10 0 00-10-10" stroke-width="2" stroke-linecap="round"></path></svg><span>Loading…</span></div>';
      }
      try {
        await state.loadDetail(jobId, container, row);
        container.dataset.loaded = '1';
      } catch (error) {
        console.warn('Job detail load failed', jobId, error);
        container.innerHTML = state.options.errorTemplate || '<div class="text-xs text-rose-300">Unable to load job detail.</div>';
      } finally {
        delete container.dataset.loading;
      }
    }

    collapseAll(state);
    state.expandedRows.add(row);
    showDetail(detailRow);
    applyActiveState(row, true, state.options.activeRowClass);
    if (typeof state.options.onAfterExpand === 'function') {
      state.options.onAfterExpand(row, detailRow, container);
    }
  }

  function collapseRow(row, state) {
    const jobId = row.dataset.job;
    if (!jobId) return;
    const detailRow = getDetailRow(jobId, state.options);
    hideDetail(detailRow);
    applyActiveState(row, false, state.options.activeRowClass);
    state.expandedRows.delete(row);
    if (typeof state.options.onCollapse === 'function') {
      state.options.onCollapse(row, detailRow);
    }
  }

  async function toggleRow(row, state) {
    if (!row || !row.dataset.job) return;
    const isExpanded = row.getAttribute('aria-expanded') === 'true';
    if (isExpanded) {
      collapseRow(row, state);
    } else {
      await expandRow(row, state);
    }
  }

  function handleClick(evt, state) {
    const row = evt.target.closest(state.options.rowSelector || '[data-job-row]');
    if (!row) return;
    if (evt.target.closest(INTERACTIVE_SELECTOR)) return;
    evt.preventDefault();
    toggleRow(row, state);
  }

  function handleKeydown(evt, state) {
    const row = evt.target.closest(state.options.rowSelector || '[data-job-row]');
    if (!row) return;
    if (evt.key !== 'Enter' && evt.key !== ' ') return;
    if (evt.target.closest(INTERACTIVE_SELECTOR)) return;
    evt.preventDefault();
    toggleRow(row, state);
  }

  function hydrateExisting(state) {
    const rows = state.options.root.querySelectorAll(state.options.rowSelector || '[data-job-row]');
    rows.forEach((row) => {
      if (row.getAttribute('aria-expanded') === 'true') {
        expandRow(row, state);
      } else {
        const jobId = row.dataset.job;
        const detailRow = getDetailRow(jobId, state.options);
        hideDetail(detailRow);
        applyActiveState(row, false, state.options.activeRowClass);
      }
    });
  }

  function init(options = {}) {
    const state = {
      options: Object.assign({
        root: document,
        rowSelector: '[data-job-row]'
      }, options),
      expandedRows: new Set(),
      loadDetail: resolveLoadDetail(options),
    };
    if (!state.options.root) {
      state.options.root = document;
    }

    hydrateExisting(state);

    const clickHandler = (evt) => handleClick(evt, state);
    const keyHandler = (evt) => handleKeydown(evt, state);

    state.options.root.addEventListener('click', clickHandler);
    state.options.root.addEventListener('keydown', keyHandler);

    return {
      toggle: (row) => toggleRow(row, state),
      expand: (row) => expandRow(row, state),
      collapse: (row) => collapseRow(row, state),
      collapseAll: () => collapseAll(state),
      destroy: () => {
        state.options.root.removeEventListener('click', clickHandler);
        state.options.root.removeEventListener('keydown', keyHandler);
        collapseAll(state);
      },
    };
  }

  platformUI.jobsTable = {
    init,
  };
})(window);
