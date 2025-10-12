(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.modals) {
    return;
  }

  let ctx = null;
  let notify = null;

  function setContext(value) {
    ctx = value;
  }

  function setNotify(fn) {
    notify = typeof fn === 'function' ? fn : null;
  }

  function confirm(options = {}) {
    if (!ctx) return global.Promise.resolve(true);
    if (typeof ctx.modalApi.confirm === 'function') {
      return ctx.modalApi.confirm(options);
    }
    if (typeof global.confirm === 'function') {
      const message = options.body || options.title || 'Are you sure?';
      return global.Promise.resolve(global.confirm(message));
    }
    return global.Promise.resolve(true);
  }

  function openFromHTML(html, modalOptions = {}) {
    if (!ctx) return null;
    if (typeof ctx.modalApi.openFromHTML === 'function') {
      return ctx.modalApi.openFromHTML(html, modalOptions);
    }
    return null;
  }

  function bindLogLevelToggles(modal) {
    if (!modal) return;
    const entriesContainer = modal.querySelector('[data-log-entries]');
    const toggleButtons = Array.from(modal.querySelectorAll('[data-log-level-toggle]'));
    if (!entriesContainer || !toggleButtons.length) return;
    const resetButton = modal.querySelector('[data-log-level-reset]');
    const activeClasses = ['border-white/30', 'bg-white/20', 'text-white'];
    const inactiveClasses = ['border-white/20', 'bg-white/5', 'text-slate-300', 'opacity-60'];

    function setButtonState(button, isActive) {
      button.dataset.logLevelActive = isActive ? '1' : '0';
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      activeClasses.forEach((cls) => button.classList.toggle(cls, isActive));
      inactiveClasses.forEach((cls) => button.classList.toggle(cls, !isActive));
    }

    toggleButtons.forEach((button) => {
      setButtonState(button, button.dataset.logLevelActive !== '0');
    });

    function applyFilter() {
      const activeLevels = new Set(
        toggleButtons
          .filter((button) => button.dataset.logLevelActive !== '0')
          .map((button) => (button.getAttribute('data-log-level-toggle') || '').toUpperCase())
          .filter((value) => value),
      );
      const entries = entriesContainer.querySelectorAll('[data-log-entry]');
      entries.forEach((entry) => {
        const entryLevel = (entry.getAttribute('data-log-level') || '').toUpperCase();
        const shouldShow = activeLevels.size === 0 ? false : activeLevels.has(entryLevel);
        entry.classList.toggle('hidden', !shouldShow);
        if (shouldShow) {
          entry.removeAttribute('hidden');
        } else {
          entry.setAttribute('hidden', 'hidden');
        }
      });
    }

    toggleButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const nextState = button.dataset.logLevelActive === '0';
        setButtonState(button, nextState);
        applyFilter();
      });
    });

    if (resetButton) {
      resetButton.addEventListener('click', () => {
        toggleButtons.forEach((button) => setButtonState(button, true));
        applyFilter();
      });
    }

    applyFilter();
  }

  function message(options = {}) {
    if (!ctx) return global.Promise.resolve();
    if (typeof ctx.modalApi.message === 'function') {
      return ctx.modalApi.message(options);
    }
    const body = options.body || options.title || options.heading;
    if (notify && body) {
      notify(global.innerWidth / 2, global.innerHeight / 2, body);
    }
    return global.Promise.resolve();
  }

  async function openJobLogModal(caseValue, jobId) {
    if (!ctx || !caseValue || !jobId) return;
    const container = ctx.modalRoot || undefined;
    const showErrorModal = (title, detail) => {
      const content = typeof detail === 'string' ? detail : detail && detail.message ? detail.message : '';
      const safe = (content || '').toString().slice(0, 2000) || 'No details available.';
      message({
        heading: 'Job Logs',
        title: title || 'Unable to load job log',
        body: safe,
        container,
      });
    };
    try {
      const resp = await fetch(`/cases/${caseValue}/jobs/${jobId}/logs/modal/`, {
        headers: { 'HX-Request': 'true' },
        credentials: 'same-origin',
      });
      const text = await resp.text();
      if (!resp.ok) {
        console.error('Job log modal HTTP error', resp.status, text.slice(0, 500));
        showErrorModal(`HTTP ${resp.status}`, text);
        return;
      }
      const modal = openFromHTML(text, { container });
      if (!modal) {
        console.error('Job log modal missing [data-modal] wrapper');
        showErrorModal('Log content unavailable', text);
        return;
      }
      bindLogLevelToggles(modal);
    } catch (error) {
      console.error('Job log modal failed', jobId, error);
      showErrorModal('Unable to load job log', error && error.message ? error.message : String(error));
    }
  }

  async function openJobMetadataModal(caseValue, jobId) {
    if (!ctx || !caseValue || !jobId) return;
    const container = ctx.modalRoot || undefined;
    const showErrorModal = (title, detail) => {
      const content = typeof detail === 'string' ? detail : detail && detail.message ? detail.message : '';
      const safe = (content || '').toString().slice(0, 2000) || 'No metadata available.';
      message({
        heading: 'Job Metadata',
        title: title || 'Unable to load metadata',
        body: safe,
        container,
      });
    };
    try {
      const resp = await fetch(`/cases/${caseValue}/jobs/${jobId}/metadata/modal/`, {
        headers: { 'HX-Request': 'true' },
        credentials: 'same-origin',
      });
      const text = await resp.text();
      if (!resp.ok) {
        console.error('Job metadata modal HTTP error', resp.status, text.slice(0, 500));
        showErrorModal(`HTTP ${resp.status}`, text);
        return;
      }
      const modal = openFromHTML(text, { container });
      if (!modal) {
        console.error('Job metadata modal missing [data-modal] wrapper');
        showErrorModal('Metadata unavailable', text);
      }
    } catch (error) {
      console.error('Job metadata modal failed', jobId, error);
      showErrorModal('Unable to load metadata', error && error.message ? error.message : String(error));
    }
  }

  function close(modal) {
    if (!ctx || !modal) return;
    if (ctx.modalApi && typeof ctx.modalApi.close === 'function') {
      ctx.modalApi.close(modal);
    } else if (modal.parentNode) {
      modal.parentNode.removeChild(modal);
    }
  }

  async function openTranscriptModal(caseId, jobId) {
    if (!ctx || !caseId || !jobId) return;
    try {
      const resp = await fetch(`/cases/${caseId}/jobs/${jobId}/transcript/`, {
        headers: { 'HX-Request': 'true' },
        credentials: 'same-origin',
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const html = await resp.text();
      const modal = openFromHTML(html, { container: ctx.modalRoot || undefined });
      if (!modal) {
        message({
          heading: 'Transcript Preview',
          title: 'Unable to load transcript',
          body: 'No transcript content available.',
          container: ctx.modalRoot || undefined,
        });
      }
    } catch (error) {
      console.error('Transcript preview failed', jobId, error);
      if (notify) {
        notify(global.innerWidth / 2, global.innerHeight / 2, 'Unable to load transcript');
      }
    }
  }

  caseDetail.modals = {
    setContext,
    setNotify,
    confirm,
    openFromHTML,
    message,
    openJobLogModal,
    openJobMetadataModal,
    openTranscriptModal,
    close,
  };
})(window);
