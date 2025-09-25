(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.realtime) {
    return;
  }

  const DEFAULT_TERMINAL = ['SUCCEEDED', 'FAILED', 'CANCELLED', 'ERROR', 'CORRUPTED'];

  let ctx = null;
  let deps = {};

  function setContext(value) {
    ctx = value;
  }

  function setDeps(value) {
    deps = value || {};
  }

  function renderStatusLabelFactory() {
    if (!ctx) return () => {};
    return ctx.statusUtils.renderStatusLabel || (() => {});
  }

  function normalizeStatus(value) {
    if (!ctx) return (value || '').toString().trim().toUpperCase();
    const normalizer = ctx.statusUtils.normalizeStatus;
    if (typeof normalizer === 'function') {
      return normalizer(value);
    }
    return (value || '').toString().trim().toUpperCase();
  }

  function terminalStatuses() {
    if (!ctx) return DEFAULT_TERMINAL;
    return Array.isArray(ctx.statusUtils.TERMINAL_STATUSES)
      ? ctx.statusUtils.TERMINAL_STATUSES
      : DEFAULT_TERMINAL;
  }

  function ensurePolling(jobId) {
    if (!ctx || !jobId) return;
    if (ctx.jobsState.pollers[jobId]) return;
    const statusEl = global.document.getElementById(`job-status-${jobId}`);
    const current = statusEl && statusEl.dataset ? statusEl.dataset.status : '';
    if (terminalStatuses().includes(normalizeStatus(current))) {
      return;
    }
    ctx.jobsState.pollers[jobId] = global.setInterval(() => pollJob(jobId), 3000);
  }

  async function pollJob(jobId) {
    try {
      const resp = await fetch(`/api/v1/jobs/${jobId}/status/`);
      if (!resp.ok) return;
      const data = await resp.json();
      handleJobUpdate(jobId, data, 'poll');
      const normalized = normalizeStatus(data.status);
      if (terminalStatuses().includes(normalized) && ctx.jobsState.pollers[jobId]) {
        clearInterval(ctx.jobsState.pollers[jobId]);
        delete ctx.jobsState.pollers[jobId];
      }
    } catch (error) {
      console.warn('Job poll failed', jobId, error);
    }
  }

  function handleJobUpdate(jobId, payload, source) {
    if (!ctx) return;
    const status = normalizeStatus(payload.status || payload.event || '');
    const progressValue =
      payload.upload_progress ??
      payload.progress_percent ??
      (typeof payload.progress === 'number' ? payload.progress * (payload.progress <= 1 ? 100 : 1) : null);

    deps.ui?.updateStatusDisplays(jobId, status, progressValue);
    ctx.jobsState.lastStatus[jobId] = status;

    const jobKind = (payload.job_kind || payload.agent_type || '').toString().toLowerCase();
    if (
      payload.converted_audio_job_id ||
      (payload.event && String(payload.event).toLowerCase() === 'job.created' && jobKind.includes('audio_conversion'))
    ) {
      deps.scheduleTranscribeRefresh?.();
    }

    if (status && terminalStatuses().includes(status) && ctx.jobsState.pollers[jobId]) {
      clearInterval(ctx.jobsState.pollers[jobId]);
      delete ctx.jobsState.pollers[jobId];
    }
  }

  function connectSocket(jobId) {
    if (!ctx || !jobId) return;
    if (ctx.jobsState.sockets[jobId]) return;
    const url = (global.location.protocol === 'https:' ? 'wss://' : 'ws://') + global.location.host + `/ws/jobs/${jobId}/`;
    const ws = new global.WebSocket(url);
    ctx.jobsState.sockets[jobId] = ws;
    ws.onopen = () => {
      if (ctx.jobsState.pollers[jobId]) {
        clearInterval(ctx.jobsState.pollers[jobId]);
        delete ctx.jobsState.pollers[jobId];
      }
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        handleJobUpdate(jobId, data, 'ws');
      } catch (error) {
        console.warn('Job websocket parse error', jobId, error);
      }
    };
    ws.onerror = (err) => {
      console.warn('Job websocket error', jobId, err);
    };
    ws.onclose = () => {
      delete ctx.jobsState.sockets[jobId];
      ensurePolling(jobId);
    };
  }

  caseDetail.realtime = {
    setContext,
    setDeps,
    ensurePolling,
    pollJob,
    handleJobUpdate,
    connectSocket,
    renderStatusLabel: renderStatusLabelFactory,
    normalizeStatus,
  };
})(window);
