(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.realtime) {
    return;
  }
  const helpers = caseDetail.helpers || {};

  const DEFAULT_TERMINAL = ['SUCCEEDED', 'FAILED', 'CANCELLED', 'ERROR', 'CORRUPTED'];
  const FALLBACK_INTERVAL_MS = 5000;
  const CONNECT_TIMEOUT_MS = 5000;
  const WS_READY = {
    CONNECTING: 0,
    OPEN: 1,
    CLOSING: 2,
    CLOSED: 3,
  };

  let ctx = null;
  let deps = {};

  function setContext(value) {
    ctx = value;
  }

  function setDeps(value) {
    deps = value || {};
  }

  function supportsWebSocket() {
    return typeof global.WebSocket === 'function';
  }

  function ensureStateCollections() {
    if (!ctx) return;
    if (!(ctx.jobsState.fallbackJobs instanceof Set)) {
      ctx.jobsState.fallbackJobs = new Set();
    }
    ctx.jobsState.connectTimeouts = ctx.jobsState.connectTimeouts || {};
    ctx.jobsState.fallbackTimer = ctx.jobsState.fallbackTimer || null;
    ctx.jobsState.fallbackInFlight = ctx.jobsState.fallbackInFlight || false;
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

  function getFallbackJobs() {
    if (!ctx) return new Set();
    ensureStateCollections();
    return ctx.jobsState.fallbackJobs;
  }

  function startFallbackTimer() {
    if (!ctx) return;
    ensureStateCollections();
    if (ctx.jobsState.fallbackTimer) return;
    ctx.jobsState.fallbackTimer = global.setInterval(runFallbackPoll, FALLBACK_INTERVAL_MS);
  }

  function stopFallbackTimer() {
    if (!ctx) return;
    if (ctx.jobsState.fallbackTimer && getFallbackJobs().size === 0) {
      global.clearInterval(ctx.jobsState.fallbackTimer);
      ctx.jobsState.fallbackTimer = null;
    }
  }

  async function runFallbackPoll(explicitIds) {
    if (!ctx) return;
    ensureStateCollections();
    if (ctx.jobsState.fallbackInFlight) {
      return;
    }
    const fallbackJobs = getFallbackJobs();
    const ids = explicitIds ? Array.from(new Set(explicitIds)) : Array.from(fallbackJobs);
    if (!ids.length) {
      stopFallbackTimer();
      return;
    }

    const params = new URLSearchParams();
    params.set('ids', ids.join(','));
    if (ctx.jobsState.currentCaseId) {
      params.set('case_id', ctx.jobsState.currentCaseId);
    }

    ctx.jobsState.fallbackInFlight = true;
    try {
      const resp = await fetch(`/api/v1/jobs/status/bulk/?${params.toString()}`, {
        credentials: 'same-origin',
      });
      if (!resp.ok) {
        if (resp.status === 404) {
          ids.forEach((jobId) => clearFallback(jobId));
        }
        return;
      }
      const records = await resp.json();
      const seen = new Set();
      if (Array.isArray(records)) {
        records.forEach((item) => {
          const jobId = String(item.id || '').trim();
          if (!jobId) return;
          seen.add(jobId);
          handleJobUpdate(jobId, item, 'bulk');
          const normalized = normalizeStatus(item.status);
          if (normalized && terminalStatuses().includes(normalized)) {
            clearFallback(jobId);
          }
        });
      }
      ids.forEach((jobId) => {
        if (!seen.has(jobId)) {
          clearFallback(jobId);
        }
      });
    } catch (error) {
      console.warn('Job bulk poll failed', ids, error);
    } finally {
      ctx.jobsState.fallbackInFlight = false;
      if (!getFallbackJobs().size) {
        stopFallbackTimer();
      }
    }
  }

  function markForFallback(jobId, immediate) {
    if (!ctx || !jobId) return;
    ensureStateCollections();
    const fallbackJobs = getFallbackJobs();
    if (!fallbackJobs.has(jobId)) {
      fallbackJobs.add(jobId);
    }
    startFallbackTimer();
    if (immediate) {
      runFallbackPoll([jobId]);
    }
  }

  function clearFallback(jobId) {
    if (!ctx || !jobId) return;
    const fallbackJobs = getFallbackJobs();
    if (fallbackJobs.delete(jobId)) {
      stopFallbackTimer();
    }
  }

  function scheduleConnectTimeout(jobId) {
    if (!ctx) return;
    ensureStateCollections();
    const timers = ctx.jobsState.connectTimeouts;
    if (timers[jobId]) return;
    timers[jobId] = global.setTimeout(() => {
      delete timers[jobId];
      const socket = ctx.jobsState.sockets && ctx.jobsState.sockets[jobId];
      if (!socket || socket.readyState !== WS_READY.OPEN) {
        markForFallback(jobId, true);
      }
    }, CONNECT_TIMEOUT_MS);
  }

  function clearConnectTimeout(jobId) {
    if (!ctx) return;
    ensureStateCollections();
    const timers = ctx.jobsState.connectTimeouts;
    if (timers && timers[jobId]) {
      global.clearTimeout(timers[jobId]);
      delete timers[jobId];
    }
  }

  function ensurePolling(jobId) {
    if (!ctx || !jobId) return;
    if (!supportsWebSocket()) {
      markForFallback(jobId, true);
      return;
    }
    const socket = ctx.jobsState.sockets && ctx.jobsState.sockets[jobId];
    if (!socket || socket.readyState === WS_READY.CLOSED) {
      connectSocket(jobId);
      markForFallback(jobId);
      return;
    }
    if (socket.readyState === WS_READY.CLOSING) {
      markForFallback(jobId);
      return;
    }
    if (socket.readyState === WS_READY.CONNECTING) {
      scheduleConnectTimeout(jobId);
    } else if (socket.readyState === WS_READY.OPEN) {
      clearFallback(jobId);
    }
  }

  async function pollJob(jobId) {
    await runFallbackPoll(jobId ? [jobId] : undefined);
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

    if (payload.notes) {
      const notesContainer = global.document.querySelector(
        `[data-job-notes][data-job-id="${jobId}"]`,
      );
      if (notesContainer && typeof helpers.updateNotes === 'function') {
        helpers.updateNotes(notesContainer, payload.notes, { preserveInput: true });
      }
      if (typeof deps.ui?.updateNotesIndicator === 'function') {
        const noteCount =
          typeof payload.notes.count === 'number'
            ? payload.notes.count
            : Array.isArray(payload.notes.entries)
              ? payload.notes.entries.length
              : 0;
        deps.ui.updateNotesIndicator(jobId, noteCount);
      }
    }

    const jobKind = (payload.job_kind || payload.agent_type || '').toString().toLowerCase();
    if (
      payload.converted_audio_job_id ||
      (payload.event && String(payload.event).toLowerCase() === 'job.created' && jobKind.includes('audio_conversion'))
    ) {
      deps.scheduleTranscribeRefresh?.();
    }

    if (status && terminalStatuses().includes(status)) {
      clearFallback(jobId);
      const socket = ctx.jobsState.sockets && ctx.jobsState.sockets[jobId];
      if (socket && socket.readyState <= WS_READY.OPEN) {
        try {
          socket.close(1000, 'job-terminal');
        } catch (_) {}
      }
    }
  }

  function connectSocket(jobId) {
    if (!ctx || !jobId) return;
    if (!supportsWebSocket()) {
      markForFallback(jobId, false);
      return;
    }
    const existing = ctx.jobsState.sockets && ctx.jobsState.sockets[jobId];
    if (existing && (existing.readyState === WS_READY.OPEN || existing.readyState === WS_READY.CONNECTING)) {
      return;
    }
    if (existing) {
      try {
        existing.close();
      } catch (_) {}
    }
    const schema = global.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const url = `${schema}${global.location.host}/ws/jobs/${jobId}/`;
    let ws;
    try {
      ws = new global.WebSocket(url);
    } catch (error) {
      console.warn('Job websocket init failed', jobId, error);
      markForFallback(jobId, true);
      return;
    }
    ctx.jobsState.sockets[jobId] = ws;
    scheduleConnectTimeout(jobId);

    ws.onopen = () => {
      clearConnectTimeout(jobId);
      clearFallback(jobId);
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
      markForFallback(jobId, true);
    };
    ws.onclose = () => {
      delete ctx.jobsState.sockets[jobId];
      clearConnectTimeout(jobId);
      markForFallback(jobId);
    };
  }

  function watchJob(jobId) {
    if (!ctx || !jobId) return;
    if (supportsWebSocket()) {
      connectSocket(jobId);
    } else {
      markForFallback(jobId, true);
    }
    ensurePolling(jobId);
  }

  caseDetail.realtime = {
    setContext,
    setDeps,
    watchJob,
    ensurePolling,
    pollJob,
    handleJobUpdate,
    connectSocket,
    renderStatusLabel: renderStatusLabelFactory,
    normalizeStatus,
  };
})(window);
