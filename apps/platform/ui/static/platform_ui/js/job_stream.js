(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  if (platformUI.jobStream) return;
  const JSONU = platformUI.json;

  const WS_PATH = '/ws/jobs/stream/';
  const MAX_BACKOFF = 30000;
  const BASE_BACKOFF = 1000;

  let socket = null;
  let reconnectTimer = null;
  let attempts = 0;
  const jobSources = new Map();
  const caseSources = new Map();
  const updateListeners = new Set();
  const statusListeners = new Set();

  function notifyStatus(status) {
    statusListeners.forEach((listener) => {
      try {
        listener(status);
      } catch (_) {}
    });
  }

  function notifyUpdate(payload) {
    updateListeners.forEach((listener) => {
      try {
        listener(payload);
      } catch (_) {}
    });
  }

  function currentUrl() {
    const protocol = global.location.protocol === 'https:' ? 'wss://' : 'ws://';
    return `${protocol}${global.location.host}${WS_PATH}`;
  }

  function mergedJobs() {
    const merged = new Set();
    jobSources.forEach((ids) => {
      ids.forEach((id) => merged.add(id));
    });
    return Array.from(merged);
  }

  function mergedCases() {
    const merged = new Set();
    caseSources.forEach((ids) => {
      ids.forEach((id) => merged.add(id));
    });
    return Array.from(merged);
  }

  function sendReplace() {
    if (!socket || socket.readyState !== global.WebSocket.OPEN) return;
    const jobs = mergedJobs();
    const cases = mergedCases();
    const payload = { action: 'replace' };
    if (jobs.length) payload.jobs = jobs;
    if (cases.length) payload.cases = cases;
    try {
      socket.send(JSONU.stringifyStable(payload));
    } catch (_) {}
  }

  function scheduleReconnect() {
    if (reconnectTimer) return;
    const delay = Math.min(MAX_BACKOFF, BASE_BACKOFF * Math.pow(2, attempts));
    reconnectTimer = global.setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, delay);
  }

  function onMessage(event) {
    try {
      const data = JSONU.parse(event.data, null);
      if (!data) return;
      if (data.type && data.type.startsWith('job.')) {
        notifyUpdate(data);
      } else if (data.type === 'job.update') {
        notifyUpdate(data);
      }
    } catch (error) {
      console.warn('jobStream message parse error', error);
    }
  }

  function connect() {
    if (socket && (socket.readyState === global.WebSocket.OPEN || socket.readyState === global.WebSocket.CONNECTING)) {
      return;
    }
    try {
      socket = new global.WebSocket(currentUrl());
    } catch (error) {
      console.warn('jobStream connect error', error);
      socket = null;
      attempts += 1;
      notifyStatus('disconnected');
      scheduleReconnect();
      return;
    }

    socket.onopen = () => {
      attempts = 0;
      notifyStatus('connected');
      sendReplace();
    };

    socket.onmessage = onMessage;

    socket.onerror = (event) => {
      console.warn('jobStream error', event);
      notifyStatus('error');
    };

    socket.onclose = () => {
      socket = null;
      notifyStatus('disconnected');
      attempts += 1;
      scheduleReconnect();
    };
  }

  function setJobsForSource(sourceKey, jobIds) {
    const key = sourceKey || 'default';
    const next = new Set();
    (jobIds || []).forEach((jobId) => {
      if (!jobId) return;
      next.add(String(jobId));
    });
    jobSources.set(key, next);
    sendReplace();
  }

  function setCasesForSource(sourceKey, caseIds) {
    const key = sourceKey || 'default';
    const next = new Set();
    (caseIds || []).forEach((caseId) => {
      if (!caseId) return;
      next.add(String(caseId));
    });
    caseSources.set(key, next);
    sendReplace();
  }

  function removeJobSource(sourceKey) {
    const key = sourceKey || 'default';
    if (jobSources.delete(key)) {
      sendReplace();
    }
  }

  function removeCaseSource(sourceKey) {
    const key = sourceKey || 'default';
    if (caseSources.delete(key)) {
      sendReplace();
    }
  }

  function addJobs(jobIds) {
    const current = new Set(jobSources.get('default') || []);
    let changed = false;
    (jobIds || []).forEach((jobId) => {
      const str = String(jobId);
      if (!str) return;
      if (!current.has(str)) {
        current.add(str);
        changed = true;
      }
    });
    if (changed) {
      jobSources.set('default', current);
      sendReplace();
    }
  }

  function removeJobs(jobIds) {
    const current = new Set(jobSources.get('default') || []);
    let changed = false;
    (jobIds || []).forEach((jobId) => {
      const str = String(jobId);
      if (current.delete(str)) changed = true;
    });
    if (changed) {
      jobSources.set('default', current);
      sendReplace();
    }
  }

  function replaceJobs(jobIds) {
    setJobsForSource('default', jobIds);
  }

  function replaceCases(caseIds) {
    setCasesForSource('default', caseIds);
  }

  function onUpdate(callback) {
    if (typeof callback === 'function') {
      updateListeners.add(callback);
    }
    return () => updateListeners.delete(callback);
  }

  function onStatus(callback) {
    if (typeof callback === 'function') {
      statusListeners.add(callback);
    }
    return () => statusListeners.delete(callback);
  }

  function init(options = {}) {
    if (Array.isArray(options.jobs)) replaceJobs(options.jobs);
    if (Array.isArray(options.cases)) replaceCases(options.cases);
    if (typeof options.onUpdate === 'function') onUpdate(options.onUpdate);
    if (typeof options.onStatus === 'function') onStatus(options.onStatus);
    connect();
    return {
      replaceJobs,
      addJobs,
      removeJobs,
      replaceCases,
      onUpdate,
      onStatus,
    };
  }

  platformUI.jobStream = {
    init,
    replaceJobs,
    addJobs,
    removeJobs,
    replaceCases,
    setJobsForSource,
    setCasesForSource,
    removeJobSource,
    removeCaseSource,
    onUpdate,
    onStatus,
  };

  connect();
})(window);
