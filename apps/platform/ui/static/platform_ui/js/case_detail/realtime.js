(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.realtime) {
    return;
  }

  const helpers = caseDetail.helpers || {};
  const jobStream = platformUI.jobStream || null;
  let streamKey = null;

  const DEFAULT_TERMINAL = ['SUCCEEDED', 'FAILED', 'CANCELLED', 'ERROR', 'CORRUPTED'];
  const FALLBACK_INTERVAL_MS = 5000;

  let ctx = null;
  let deps = {};
  let streamStatus = 'idle';

  function setContext(value) {
    ctx = value;
    const state = ensureStateCollections();
    const previousKey = streamKey;
    streamKey = ctx && ctx.caseId ? `case-${ctx.caseId}` : 'case-detail';
    if (jobStream && previousKey && typeof jobStream.removeJobSource === 'function') {
      jobStream.removeJobSource(previousKey);
      if (typeof jobStream.removeCaseSource === 'function') {
        jobStream.removeCaseSource(previousKey);
      }
    }
    if (state) {
      state.currentCaseId = ctx && ctx.caseId ? String(ctx.caseId) : state.currentCaseId;
      state.streamJobs = new Set();
    }
    if (jobStream && ctx && ctx.caseId && typeof jobStream.setCasesForSource === 'function') {
      jobStream.setCasesForSource(streamKey, [String(ctx.caseId)]);
    }
  }

  function setDeps(value) {
    deps = value || {};
  }

  function syncJobs(jobIds) {
    const state = ensureStateCollections();
    if (!state) return;
    state.streamJobs = new Set((jobIds || []).map((id) => String(id)));
    if (jobStream && typeof jobStream.setJobsForSource === 'function' && streamKey) {
      jobStream.setJobsForSource(streamKey, Array.from(state.streamJobs));
    }
  }

  function ensureStateCollections() {
    if (!ctx) return;
    const state = (ctx.jobsState = ctx.jobsState || {});
    if (!(state.fallbackJobs instanceof Set)) {
      state.fallbackJobs = new Set();
    }
    if (!(state.streamJobs instanceof Set)) {
      state.streamJobs = new Set();
    }
    if (!state.hasOwnProperty('fallbackTimer')) {
      state.fallbackTimer = null;
    }
    if (!state.hasOwnProperty('fallbackInFlight')) {
      state.fallbackInFlight = false;
    }
    return state;
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
    const state = ensureStateCollections();
    return state ? state.fallbackJobs : new Set();
  }

  function startFallbackTimer() {
    const state = ensureStateCollections();
    if (!state) return;
    if (state.fallbackTimer) return;
    state.fallbackTimer = global.setInterval(runFallbackPoll, FALLBACK_INTERVAL_MS);
  }

  function stopFallbackTimer() {
    const state = ensureStateCollections();
    if (!state) return;
    if (state.fallbackTimer && state.fallbackJobs.size === 0) {
      global.clearInterval(state.fallbackTimer);
      state.fallbackTimer = null;
    }
  }

  async function runFallbackPoll(explicitIds) {
    const state = ensureStateCollections();
    if (!ctx || !state) return;
    if (state.fallbackInFlight) {
      return;
    }
    const fallbackJobs = state.fallbackJobs;
    const ids = explicitIds ? Array.from(new Set(explicitIds)) : Array.from(fallbackJobs);
    if (!ids.length) {
      stopFallbackTimer();
      return;
    }

    const params = new URLSearchParams();
    params.set('ids', ids.join(','));
    if (state.currentCaseId) {
      params.set('case_id', state.currentCaseId);
    }

    state.fallbackInFlight = true;
    try {
      const resp = await fetch(`/api/v1/jobs/status/bulk/?${params.toString()}`, { credentials: 'same-origin' });
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
      state.fallbackInFlight = false;
      if (!state.fallbackJobs.size) {
        stopFallbackTimer();
      }
    }
  }

  function markForFallback(jobId, immediate) {
    if (!jobId) return;
    const state = ensureStateCollections();
    if (!state) return;
    if (!state.fallbackJobs.has(jobId)) {
      state.fallbackJobs.add(jobId);
    }
    startFallbackTimer();
    if (immediate) {
      runFallbackPoll([jobId]);
    }
  }

  function clearFallback(jobId) {
    if (!jobId) return;
    const state = ensureStateCollections();
    if (!state) return;
    if (state.fallbackJobs.delete(jobId)) {
      stopFallbackTimer();
    }
  }

  async function pollJob(jobId) {
    await runFallbackPoll(jobId ? [jobId] : undefined);
  }

  function handleJobUpdate(jobId, payload, source) {
    if (!ctx) return;
    const eventName =
      payload && typeof payload.event === 'string'
        ? payload.event.toString().trim().toLowerCase()
        : '';
    if (eventName === 'analyze.progress') {
      deps.ui?.updateAnalyzeProgress?.(jobId, payload);
    }
    const status = normalizeStatus(payload.status || payload.event || '');
    const progressValue =
      payload.upload_progress ??
      payload.progress_percent ??
      (typeof payload.progress === 'number' ? payload.progress * (payload.progress <= 1 ? 100 : 1) : null);

    deps.ui?.updateStatusDisplays(jobId, status, progressValue);
    ctx.jobsState.lastStatus[jobId] = status;

    if (payload && Object.prototype.hasOwnProperty.call(payload, 'review_status')) {
      deps.ui?.updateReviewDisplays?.(jobId, payload);
    }

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

    deps.ui?.handleAnalyzeJobStatus?.(jobId, status);

    if (status && terminalStatuses().includes(status)) {
      clearFallback(jobId);
    }
  }

  function ensurePolling(jobId) {
    if (!jobId) return;
    if (!jobStream || streamStatus !== 'connected') {
      markForFallback(jobId, true);
    }
  }

  function watchJob(jobId) {
    if (!jobId) return;
    const state = ensureStateCollections();
    if (state && state.streamJobs instanceof Set) {
      state.streamJobs.add(String(jobId));
      if (jobStream && typeof jobStream.setJobsForSource === 'function' && streamKey) {
        jobStream.setJobsForSource(streamKey, Array.from(state.streamJobs));
      }
    }
    if (!jobStream) {
      markForFallback(jobId, true);
    }
    ensurePolling(jobId);
  }

  if (jobStream) {
    jobStream.onUpdate((payload) => {
      const jobId = String(payload.job_id || payload.id || '').trim();
      if (!jobId) return;
      handleJobUpdate(jobId, payload, 'ws');
      if (streamStatus === 'connected') {
        const normalized = normalizeStatus(payload.status || payload.event || '');
        if (normalized && terminalStatuses().includes(normalized)) {
          clearFallback(jobId);
        }
      }
    });

    jobStream.onStatus((status) => {
      streamStatus = status;
      const state = ensureStateCollections();
      if (status === 'connected') {
        const fallbackJobs = Array.from(getFallbackJobs());
        fallbackJobs.forEach((jobId) => clearFallback(jobId));
        stopFallbackTimer();
      } else {
        if (state && state.streamJobs instanceof Set) {
          state.streamJobs.forEach((jobId) => markForFallback(jobId, false));
        }
        if (getFallbackJobs().size) {
          startFallbackTimer();
        }
      }
    });
  }

  caseDetail.realtime = {
    setContext,
    setDeps,
    syncJobs,
    watchJob,
    ensurePolling,
    pollJob,
    handleJobUpdate,
  };
})(window);
