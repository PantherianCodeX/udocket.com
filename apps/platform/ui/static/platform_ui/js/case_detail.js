(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail._bootstrapped) {
    return;
  }

  caseDetail._bootstrapped = true;

  function init(options = {}) {
    // TODO(layout-refresh): Investigate more reliable template update tooling to reduce manual patch churn during upcoming refactor.
    const caseView = options.root || document.querySelector('[data-case-view]');
    if (!caseView) {
      return;
    }
    const caseId = options.caseId || caseView.getAttribute('data-case-id');
    const initialToolKey = options.initialToolKey || caseView.getAttribute('data-initial-tool') || '';
    const workspace = options.workspace || caseView.querySelector('#tool-workspace');
    const modalRoot = options.modalRoot || document.getElementById('modal-root');

    // Initialize shared jobs state namespace used across handlers in this view
    const jobsState =
      (caseDetail.state =
        caseDetail.state ||
        global.JobsState || {
          currentCaseId: caseId,
          pollers: {},
          sockets: {},
          lastStatus: {},
          refreshTranscribeScheduled: false,
        });
    global.JobsState = jobsState;

    const jobsTableApi = platformUI.jobsTable;
    if (!jobsTableApi || typeof jobsTableApi.init !== 'function') {
      console.warn('platformUI.jobsTable.init is required for case detail interactions');
      return;
    }

    const statusUtils = platformUI.status || {};
    const jobActions = platformUI.jobActions || {};
    const modalApi = platformUI.modal || {};
    const toastAt = typeof platformUI.toastAt === 'function' ? platformUI.toastAt : null;
    const toast = typeof platformUI.toast === 'function' ? platformUI.toast : null;
    const notify = (x, y, text) => {
      if (toastAt) {
        toastAt(x, y, text);
      } else if (toast) {
        toast(text);
      }
    };

    const confirmWithModal = async (options = {}) => {
      if (typeof modalApi.confirm === 'function') {
        return modalApi.confirm(options);
      }
      if (typeof window.confirm === 'function') {
        const message = options.body || options.title || 'Are you sure?';
        return window.confirm(message);
      }
      return true;
    };

    const openModalHTML = (html, modalOptions = {}) => {
      if (typeof modalApi.openFromHTML === 'function') {
        return modalApi.openFromHTML(html, modalOptions);
      }
      return null;
    };

    const showModalMessage = (options = {}) => {
      if (typeof modalApi.message === 'function') {
        return modalApi.message(options);
      }
      const body = options.body || options.title || options.heading;
      if (body) {
        notify(window.innerWidth / 2, window.innerHeight / 2, body);
      }
      return Promise.resolve();
    };
    
      const JOB_DETAIL_LOADING = '<div class="flex items-center gap-2 text-xs text-slate-300"><svg class="h-3 w-3 animate-spin text-primary-300" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle class="opacity-30" cx="12" cy="12" r="10" stroke-width="2"></circle><path d="M22 12a10 10 0 00-10-10" stroke-width="2" stroke-linecap="round"></path></svg><span>Loading…</span></div>';
      const JOB_DETAIL_ERROR = '<div class="text-xs text-rose-300">Unable to load job detail.</div>';
    
      const jobsTableController = jobsTableApi.init({
        root: caseView,
        activeRowClass: 'bg-white/10',
        detailRowSelector: (jobId) => `[data-job-detail="${jobId}"]`,
        detailContainerSelector: (jobId) => `[data-job-detail-container="${jobId}"]`,
        loadingTemplate: JOB_DETAIL_LOADING,
        errorTemplate: JOB_DETAIL_ERROR,
        loadDetail: async (jobId, container) => {
          const resp = await fetch(`/cases/${caseId}/jobs/${jobId}/detail/`, {
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
    
      jobsState.table = jobsTableController;
    
            const renderStatusLabel = statusUtils.renderStatusLabel || (() => {});
      const normalizeStatus = statusUtils.normalizeStatus || ((value) => (value || '').toString().trim().toUpperCase());
      const TERMINAL_STATUSES = statusUtils.TERMINAL_STATUSES || ['SUCCEEDED', 'FAILED', 'CANCELLED', 'ERROR', 'CORRUPTED'];
      const JOB_ROW_STATUS_CLASSES = ['bg-emerald-500/10', 'bg-rose-500/10', 'bg-amber-500/10', 'bg-primary-500/10', 'bg-white/5'];
    
      function formatDuration(value) {
        const seconds = Number(value);
        if (!Number.isFinite(seconds) || seconds < 0) return null;
        if (seconds >= 600) return `${Math.round(seconds)} s`;
        if (seconds >= 60) return `${seconds.toFixed(1)} s`;
        if (seconds >= 10) return `${seconds.toFixed(1)} s`;
        return `${seconds.toFixed(2)} s`;
      }
    
      function formatFileSize(bytes) {
        const size = Number(bytes);
        if (!Number.isFinite(size) || size < 0) return null;
        const units = ['bytes', 'KB', 'MB', 'GB', 'TB'];
        let value = size;
        let idx = 0;
        while (value >= 1024 && idx < units.length - 1) {
          value /= 1024;
          idx += 1;
        }
        const formatted = idx === 0 ? Math.round(value).toString() : (value >= 10 ? value.toFixed(0) : value.toFixed(1));
        if (idx === 0) {
          return `${formatted} ${Number(formatted) === 1 ? 'byte' : 'bytes'}`;
        }
        return `${formatted} ${units[idx]}`;
      }
    
      function truncateMiddle(input, head = 28, tail = 16) {
        if (typeof input !== 'string') return input;
        if (input.length <= head + tail + 3) return input;
        return `${input.slice(0, head)}…${input.slice(-tail)}`;
      }
    
      function updateAudioPanel(panel, payload) {
        if (!panel || !payload) return;
        const sizeBytes = payload.size_bytes_local ?? payload.size_bytes_remote ?? payload.audio_size_bytes ?? null;
        const hashValue = payload.sha256 || payload.remote_sha256 || payload.audio_sha256 || null;
        const values = {
          original_name: payload.original_name || payload.audio_file || null,
          duration: formatDuration(payload.duration_s ?? payload.audio_duration_s),
          channels: payload.channels != null ? String(payload.channels) : (payload.audio_channels != null ? String(payload.audio_channels) : null),
          sample_rate: payload.sample_rate_hz != null ? `${payload.sample_rate_hz} Hz` : (payload.audio_sample_rate_hz != null ? `${payload.audio_sample_rate_hz} Hz` : null),
          bitrate: payload.bitrate_kbps != null ? `${payload.bitrate_kbps} kbps` : (payload.audio_bitrate_kbps != null ? `${payload.audio_bitrate_kbps} kbps` : null),
          codec: payload.codec || payload.audio_codec || null,
          layout: payload.channel_layout || payload.audio_channel_layout || null,
          mime: payload.mime || payload.audio_mime || null,
          path: payload.path || payload.audio_path || null,
          size: sizeBytes != null ? formatFileSize(sizeBytes) : null,
          hash: hashValue,
        };
        Object.entries(values).forEach(([key, rawValue]) => {
          const field = panel.querySelector(`[data-audio-field="${key}"]`);
          if (!field) return;
          if (key === 'path') {
            if (rawValue) {
              field.textContent = truncateMiddle(String(rawValue));
              field.setAttribute('data-copy-text', String(rawValue));
              field.setAttribute('title', String(rawValue));
              field.classList.add('clip-inline', 'font-mono', 'text-[11px]', 'text-primary-100');
              field.classList.remove('text-slate-500');
            } else {
              field.textContent = '—';
              field.removeAttribute('data-copy-text');
              field.removeAttribute('title');
              field.classList.remove('clip-inline', 'font-mono', 'text-[11px]', 'text-primary-100');
            }
          } else if (key === 'hash') {
            if (rawValue) {
              const hashText = String(rawValue);
              const display = hashText.length >= 12 ? `${hashText.slice(0, 8)}…${hashText.slice(-4)}` : hashText;
              field.textContent = display;
              field.setAttribute('data-copy-text', hashText);
              field.setAttribute('title', hashText);
              field.classList.add('font-mono', 'text-[11px]', 'text-primary-100');
              field.classList.remove('text-slate-500');
            } else {
              field.textContent = 'Not recorded';
              field.removeAttribute('data-copy-text');
              field.removeAttribute('title');
              field.classList.remove('font-mono', 'text-[11px]', 'text-primary-100');
              field.classList.add('text-slate-500');
            }
          } else if (key === 'size') {
            field.textContent = rawValue || '—';
          } else {
            field.textContent = rawValue || '—';
          }
        });
      }
    
    
      function scheduleTranscribeRefresh() {
        if (!jobsState.currentCaseId) return;
        if (jobsState.refreshTranscribeScheduled) return;
        jobsState.refreshTranscribeScheduled = true;
        setTimeout(() => {
          jobsState.refreshTranscribeScheduled = false;
          const url = `/cases/${jobsState.currentCaseId}/tools/transcribe/`;
          if (typeof window.htmx !== 'undefined' && window.htmx.ajax) {
            window.htmx.ajax('GET', url, '#tool-workspace');
            return;
          }
          fetch(url, { headers: { 'HX-Request': 'true' }, credentials: 'same-origin' })
            .then((resp) => (resp.ok ? resp.text() : null))
            .then((html) => {
              if (!html) return;
              const workspaceEl = document.getElementById('tool-workspace');
              if (workspaceEl) {
                workspaceEl.innerHTML = html;
                if (typeof boostJobs === 'function') {
                  boostJobs();
                }
              }
            })
            .catch(() => {});
        }, 150);
      }
    
      function ensureElementVisible(el, align = 'nearest') {
        if (!el || !el.getBoundingClientRect) return;
        const rect = el.getBoundingClientRect();
        const viewHeight = window.innerHeight || document.documentElement.clientHeight;
        const padding = Math.min(120, Math.max(48, viewHeight * 0.15));
        const topLimit = padding;
        const bottomLimit = viewHeight - padding;
        const fullyVisible = rect.top >= topLimit && rect.bottom <= bottomLimit;
        if (fullyVisible) {
          return;
        }
        const overTop = rect.top - topLimit;
        const overBottom = rect.bottom - bottomLimit;
        let delta = 0;
        if (overTop < 0) {
          delta = overTop;
        } else if (overBottom > 0) {
          delta = overBottom;
        }
        if (delta && typeof window.scrollBy === 'function') {
          window.scrollBy({ top: delta, behavior: 'smooth' });
        } else {
          el.scrollIntoView({ behavior: 'smooth', block: align, inline: 'nearest' });
        }
      }
    
      function updateStatusDisplays(jobId, status, progress) {
        const statusCell = document.getElementById(`job-status-${jobId}`);
        if (statusCell) {
          renderStatusLabel(statusCell, status, progress);
        }
        const jobRow = document.querySelector(`[data-job="${jobId}"]`);
        if (jobRow) {
          jobRow.classList.remove(...JOB_ROW_STATUS_CLASSES);
        }
        if (jobActions && typeof jobActions.updateForRow === 'function') {
          jobActions.updateForRow(jobId, status);
        }
        const detailContainer = document.querySelector(`[data-job-detail="${jobId}"]`);
        if (!detailContainer) return;
        const pill = detailContainer.querySelector('[data-job-status-pill]');
        if (pill) {
          renderStatusLabel(pill, status, progress);
        }
      }
    
      function setActiveCard(key) {
        document.querySelectorAll('[data-tool-card]').forEach((card) => {
          const match = card.getAttribute('data-tool-card') === key;
          card.classList.toggle('border-primary-400', match);
          card.classList.toggle('bg-slate-900/70', match);
          card.setAttribute('aria-pressed', match ? 'true' : 'false');
        });
        caseView.setAttribute('data-active-tool', key || '');
        if (key) {
          history.replaceState({}, '', `?tool=${encodeURIComponent(key)}`);
        } else {
          history.replaceState({}, '', location.pathname);
        }
      }
    
      document.body.addEventListener('htmx:beforeRequest', (evt) => {
        const button = evt.target.closest('[data-tool-card]');
        if (!button) return;
        const key = button.getAttribute('data-tool-card');
        setActiveCard(key);
        button.classList.add('ring-1', 'ring-primary-400/60');
      });
    
      document.body.addEventListener('htmx:afterSwap', (evt) => {
        const button = evt.target.closest('[data-tool-card]');
        if (button) {
          button.classList.remove('ring-1', 'ring-primary-400/60');
          boostJobs();
          return;
        }
        if (evt.target === workspace) {
          if (jobsState.table && typeof jobsState.table.collapseAll === 'function') {
            jobsState.table.collapseAll();
          }
          boostJobs();
        }
      });
    
      document.body.addEventListener('htmx:error', (evt) => {
        const button = evt.target.closest('[data-tool-card]');
        if (button) {
          button.classList.remove('ring-1', 'ring-primary-400/60');
        }
      });
    
      document.body.addEventListener('htmx:afterOnLoad', (evt) => {
        const headerValue = evt.detail?.xhr?.getResponseHeader('HX-Trigger');
        if (!headerValue) return;
        try {
          const payload = JSON.parse(headerValue);
          const refreshed = payload['case-view-refreshed'];
          if (refreshed) {
            if (refreshed.header_html) {
              const headerContainer = document.querySelector('[data-case-header-container]');
              if (headerContainer) headerContainer.innerHTML = refreshed.header_html;
            }
            if (refreshed.cards_html) {
              const cardsContainer = document.querySelector('[data-case-developer-cards]');
              if (cardsContainer) cardsContainer.innerHTML = refreshed.cards_html;
            }
            if (refreshed.active_tool) {
              setActiveCard(refreshed.active_tool);
            }
            boostJobs();
          }
        } catch (_) {}
      });
    
      function ensurePolling(jobId) {
        if (jobsState.pollers[jobId]) return;
        const statusEl = document.getElementById(`job-status-${jobId}`);
        const normalized = statusEl && statusEl.dataset ? statusEl.dataset.status : '';
        if (TERMINAL_STATUSES.includes(normalizeStatus(normalized))) {
          return;
        }
        jobsState.pollers[jobId] = setInterval(() => pollJob(jobId), 3000);
      }
    
      async function pollJob(jobId) {
        try {
          const resp = await fetch(`/api/v1/jobs/${jobId}/status/`);
          if (!resp.ok) return;
          const data = await resp.json();
          handleJobUpdate(jobId, data, 'poll');
          const normalized = normalizeStatus(data.status);
          if (TERMINAL_STATUSES.includes(normalized) && jobsState.pollers[jobId]) {
            clearInterval(jobsState.pollers[jobId]);
            delete jobsState.pollers[jobId];
          }
        } catch (error) {
          console.warn('Job poll failed', jobId, error);
        }
      }
    
      function handleJobUpdate(jobId, payload, source) {
        const status = normalizeStatus(payload.status || payload.event || '');
        const progressValue = payload.upload_progress ?? payload.progress_percent ?? (typeof payload.progress === 'number' ? payload.progress * (payload.progress <= 1 ? 100 : 1) : null);
        updateStatusDisplays(jobId, status, progressValue);
        jobsState.lastStatus[jobId] = status;
        if (payload && (payload.converted_audio_job_id || (payload.event && String(payload.event).toLowerCase() === 'job.created' && (payload.job_kind === 'audio_conversion' || payload.agent_type === 'Audio Conversion')))) {
          scheduleTranscribeRefresh();
        }
        if (status && TERMINAL_STATUSES.includes(status) && jobsState.pollers[jobId]) {
          clearInterval(jobsState.pollers[jobId]);
          delete jobsState.pollers[jobId];
        }
      }
    
      function connectSocket(jobId) {
        if (jobsState.sockets[jobId]) return;
        const url = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + `/ws/jobs/${jobId}/`;
        const ws = new WebSocket(url);
        jobsState.sockets[jobId] = ws;
        ws.onopen = () => {
          if (jobsState.pollers[jobId]) {
            clearInterval(jobsState.pollers[jobId]);
            delete jobsState.pollers[jobId];
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
          delete jobsState.sockets[jobId];
          ensurePolling(jobId);
        };
      }
    
      function handleRowClick(evt) {
        const row = evt.target.closest('[data-job-row]');
        if (!row) return;
        if (evt.target.closest('a, button, input, textarea, select, [role="button"], [data-job-action-menu], [data-popover]')) return;
        evt.preventDefault();
        jobsTableController.toggle(row);
      }
    
      function handleRowKey(evt) {
        if (evt.target.closest('[data-job-row]') && (evt.key === 'Enter' || evt.key === ' ')) {
          if (evt.target.closest('a, button, input, textarea, select, [role="button"], [data-job-action-menu], [data-popover]')) return;
          evt.preventDefault();
          jobsTableController.toggle(evt.target.closest('[data-job-row]'));
        }
      }
    
      function removeJobRow(jobId) {
        const row = document.querySelector(`[data-job="${jobId}"]`);
        const detail = document.querySelector(`[data-job-detail="${jobId}"]`);
        if (row) row.remove();
        if (detail) detail.remove();
      }
    
      async function handleJobAction(evt) {
        const control = evt.target.closest('[data-job-action]');
        if (!control) return;
        evt.preventDefault();
        const jobId = control.getAttribute('data-job-id');
        const kind = control.getAttribute('data-job-action-kind') || 'api';
        const action = control.getAttribute('data-job-action');
        const menu = control.closest('[data-job-action-menu]');
        const closeMenu = () => {
          if (menu) {
            menu.removeAttribute('open');
            resetPopoverMenu(menu);
          }
        };
    
        if (kind === 'modal') {
          if (action === 'view-log') {
            const caseValue = control.getAttribute('data-case-id') || jobsState.currentCaseId;
            if (jobId && caseValue) {
              await openJobLogModal(caseValue, jobId);
            }
          } else if (action === 'view-transcript') {
            if (jobId) await openTranscriptModal(jobId);
          } else if (action === 'view-metadata') {
            const caseValue = control.getAttribute('data-case-id') || jobsState.currentCaseId;
            if (jobId && caseValue) {
              await openJobMetadataModal(caseValue, jobId);
            }
          }
          closeMenu();
          return;
        }
    
        if (kind === 'navigate') {
          const targetJob = control.getAttribute('data-job-target');
          if (targetJob) {
            const expanded = await expandJobRow(targetJob);
            if (!expanded && notify) {
              notify(evt.clientX || window.innerWidth / 2, evt.clientY || window.innerHeight / 2, 'Job not available in this panel');
            }
          }
          closeMenu();
          return;
        }
    
        if (!jobId || !action) {
          closeMenu();
          return;
        }
    
        const confirmMessage = control.getAttribute('data-job-action-confirm');
        if (confirmMessage) {
          const label = (control.textContent || control.getAttribute('aria-label') || '').trim();
          const confirmed = await confirmWithModal({
            heading: 'Confirm action',
            title: label || 'Please confirm',
            body: confirmMessage,
            confirmLabel: control.getAttribute('data-job-action-confirm-label') || (kind === 'delete' ? 'Delete' : 'Confirm'),
            cancelLabel: control.getAttribute('data-job-action-cancel-label') || 'Cancel',
            destructive: kind === 'delete',
            container: modalRoot || undefined,
          });
          if (!confirmed) {
            closeMenu();
            return;
          }
        }
    
        let requestBody;
        let endpointAction = action;
        const promptMessage = control.getAttribute('data-job-action-prompt');
        if (promptMessage) {
          const response = window.prompt(promptMessage, '');
          if (response === null) {
            closeMenu();
            return;
          }
          requestBody = JSON.stringify({ comment: response });
        }
        const optionalQuery = control.getAttribute('data-job-action-query');
        if (optionalQuery) {
          endpointAction = `${endpointAction}?${optionalQuery}`;
        }
    
        const method = control.getAttribute('data-job-action-method') || (kind === 'delete' ? 'DELETE' : 'POST');
        const headers = {
          'X-CSRFToken': getCSRFToken(),
          Accept: 'application/json',
        };
        if (method !== 'DELETE') {
          headers['Content-Type'] = 'application/json';
        }
    
        closeMenu();
    
        control.disabled = true;
        try {
          const url = method === 'DELETE' ? `/api/v1/jobs/${jobId}/` : `/api/v1/jobs/${jobId}/${endpointAction}/`;
          const resp = await fetch(url, {
            method,
            headers,
            credentials: 'same-origin',
            body: method === 'DELETE' ? null : (requestBody || null),
          });
          if (!resp.ok) {
            const body = await resp.text();
            console.warn('Job action failed', endpointAction, body);
          } else if (method === 'DELETE') {
            removeJobRow(jobId);
            scheduleTranscribeRefresh();
          } else {
            const data = await resp.json();
            handleJobUpdate(jobId, data, 'action');
            ensurePolling(jobId);
          }
        } catch (error) {
          console.warn('Job action error', action, error);
        } finally {
          control.disabled = false;
        }
      }
    
      async function markJobsCorrupted(jobIds) {
        if (!Array.isArray(jobIds) || !jobIds.length) return;
        for (const id of jobIds) {
          try {
            const resp = await fetch(`/api/v1/jobs/${id}/mark-corrupted/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
                Accept: 'application/json',
              },
              credentials: 'same-origin',
            });
            if (!resp.ok) continue;
            const data = await resp.json();
            handleJobUpdate(id, data, 'verify');
          } catch (error) {
            console.warn('Mark corrupted failed', id, error);
          }
        }
      }
      async function handleVerifyHash(evt) {
        const btn = evt.target.closest('[data-verify-hash]');
        if (!btn) return;
        evt.preventDefault();
        if (btn.disabled) return;
        const jobId = btn.getAttribute('data-job-id');
        const target = btn.getAttribute('data-target') || 'audio';
        const scopeAttr = btn.getAttribute('data-scope');
        if (!jobId) return;
        const payload = { target };
        if (scopeAttr) {
          payload.scope = scopeAttr;
        }
        const corruptedAttr = btn.getAttribute('data-mark-corrupted') || '';
        const markTargets = Array.from(new Set([jobId, ...corruptedAttr.split(',').map((value) => value.trim()).filter(Boolean)]));
        const originalText = btn.textContent;
        const tooltipContainer = btn.querySelector('[data-verify-tooltip]');
        if (tooltipContainer) {
          tooltipContainer.remove();
        }
        btn.disabled = true;
        btn.classList.add('cursor-progress');
        btn.textContent = 'Verifying…';
        let finalised = false;
        let resultType = null;
        let tooltip = null;
        const ensureTooltip = (text, tone) => {
          let tip = btn.querySelector('[data-verify-tooltip]');
          if (!tip) {
            tip = document.createElement('span');
            tip.dataset.verifyTooltip = '1';
            tip.setAttribute('role', 'status');
            tip.className = 'pointer-events-none absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap rounded-md border border-white/20 bg-slate-900/95 px-2 py-1 text-[10px] font-semibold text-slate-100 shadow-lg shadow-black/40';
            btn.appendChild(tip);
          }
          tip.textContent = text;
          tip.dataset.tone = tone || '';
          tooltip = tip;
        };
        try {
          const resp = await fetch(`/api/v1/jobs/${jobId}/verify-hash/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCSRFToken(),
              Accept: 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify(payload),
          });
          let label = 'Failed';
          if (resp.ok) {
            const data = await resp.json();
            const observed = typeof data.observed === 'string' && data.observed.length >= 12
              ? `${data.observed.slice(0, 8)}…${data.observed.slice(-4)}`
              : (data.observed || 'n/a');
            const expected = typeof data.expected === 'string' && data.expected.length >= 12
              ? `${data.expected.slice(0, 8)}…${data.expected.slice(-4)}`
              : (data.expected || 'n/a');
            resultType = data.result || null;
            if (data.result === 'match') {
              label = 'Verified';
              ensureTooltip(`Hash verified (${observed})`, 'success');
            } else if (data.result === 'mismatch') {
              label = 'Failed';
              ensureTooltip(`Expected ${expected}, got ${observed}`, 'error');
            } else if (data.result === 'computed') {
              label = 'Verified';
              ensureTooltip(`Computed ${observed}`, 'info');
            } else {
              label = 'Failed';
              ensureTooltip('Verification failed', 'error');
            }
          } else {
            resultType = 'error';
            try {
              const err = await resp.json();
              const detail = err && err.detail ? String(err.detail) : 'Verification failed';
              ensureTooltip(detail, 'error');
            } catch (_) {
              ensureTooltip('Verification request failed', 'error');
            }
          }
          btn.textContent = resultType === 'match' || resultType === 'computed' ? 'Verified' : 'Failed';
          btn.classList.remove('cursor-progress');
          btn.classList.add('cursor-default', 'opacity-70');
          btn.style.cursor = 'default';
          btn.setAttribute('aria-disabled', 'true');
          finalised = true;
        } catch (error) {
          resultType = 'error';
          btn.textContent = 'Failed';
          btn.classList.remove('cursor-progress');
          let tip = btn.querySelector('[data-verify-tooltip]');
          if (!tip) {
            tip = document.createElement('span');
            tip.dataset.verifyTooltip = '1';
            tip.setAttribute('role', 'status');
            tip.className = 'pointer-events-none absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap rounded-md border border-white/20 bg-slate-900/95 px-2 py-1 text-[10px] font-semibold text-slate-100 shadow-lg shadow-black/40';
            btn.appendChild(tip);
          }
          tip.textContent = 'Verification failed';
          btn.classList.add('cursor-default', 'opacity-70');
          btn.style.cursor = 'default';
          btn.setAttribute('aria-disabled', 'true');
          finalised = true;
        } finally {
          if (!finalised) {
            btn.textContent = originalText;
            btn.disabled = false;
            btn.classList.remove('cursor-progress', 'cursor-default', 'opacity-70');
            btn.removeAttribute('aria-disabled');
            btn.style.cursor = '';
          } else {
            btn.classList.remove('cursor-progress');
            btn.classList.add('cursor-default');
            btn.style.cursor = 'default';
          }
        }
        if (resultType === 'mismatch') {
          await markJobsCorrupted(markTargets);
        }
      }
      async function handleAudioRefresh(evt) {
        const btn = evt.target.closest('[data-audio-refresh]');
        if (!btn) return;
        evt.preventDefault();
        if (btn.disabled) return;
        const refreshJobId = btn.getAttribute('data-refresh-job');
        const panelKey = btn.getAttribute('data-panel');
        const displayJob = btn.getAttribute('data-display-job') || refreshJobId;
        if (!panelKey || !displayJob) return;
        if (!refreshJobId) {
          if (notify) {
            const toastX = evt.clientX || window.innerWidth / 2;
            const toastY = evt.clientY || window.innerHeight / 2;
            notify(toastX, toastY, 'Metadata unavailable for this panel');
          }
          return;
        }
        const panel = document.querySelector(`[data-audio-panel="${panelKey}"][data-job-id="${displayJob}"]`);
        if (!panel) return;
        const originalText = btn.textContent;
        const toastX = evt.clientX || window.innerWidth / 2;
        const toastY = evt.clientY || window.innerHeight / 2;
        btn.disabled = true;
        btn.textContent = 'Refreshing…';
        try {
          const resp = await fetch(`/api/v1/jobs/${refreshJobId}/refresh-audio/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCSRFToken(),
              Accept: 'application/json',
            },
            credentials: 'same-origin',
          });
          if (!resp.ok) {
            const detail = await resp.text();
            throw new Error(detail || `HTTP ${resp.status}`);
          }
          const data = await resp.json();
          if (data && data.audio) {
            updateAudioPanel(panel, data.audio);
            if (notify) {
              notify(toastX, toastY, 'Audio metadata updated');
            }
          }
        } catch (error) {
          console.warn('Audio metadata refresh failed', refreshJobId, error);
          if (notify) {
            notify(toastX, toastY, 'Unable to refresh metadata');
          }
        } finally {
          btn.disabled = false;
          btn.textContent = originalText;
        }
      }
    
    
    
      async function openJobLogModal(caseValue, jobId) {
        if (!caseValue || !jobId) return;
        const container = modalRoot || undefined;
        const showErrorModal = (title, detail) => {
          const content = typeof detail === 'string' ? detail : (detail && detail.message) || '';
          const safe = (content || '').toString().slice(0, 2000) || 'No details available.';
          showModalMessage({
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
          const modal = openModalHTML(text, { container });
          if (!modal) {
            console.error('Job log modal missing [data-modal] wrapper');
            showErrorModal('Log content unavailable', text);
          }
        } catch (error) {
          console.error('Job log modal failed', jobId, error);
          showErrorModal('Unable to load job log', error && error.message ? error.message : String(error));
        }
      }
    
    
      async function openJobMetadataModal(caseValue, jobId) {
        if (!caseValue || !jobId) return;
        const container = modalRoot || undefined;
        const showErrorModal = (title, detail) => {
          const content = typeof detail === 'string' ? detail : (detail && detail.message) || '';
          const safe = (content || '').toString().slice(0, 2000) || 'No metadata available.';
          showModalMessage({
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
          const modal = openModalHTML(text, { container });
          if (!modal) {
            console.error('Job metadata modal missing [data-modal] wrapper');
            showErrorModal('Metadata unavailable', text);
          }
        } catch (error) {
          console.error('Job metadata modal failed', jobId, error);
          showErrorModal('Unable to load metadata', error && error.message ? error.message : String(error));
        }
      }
    
    
      function getCSRFToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) return decodeURIComponent(match[1]);
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') || '' : '';
      }
    
      function syncTranscribeSidebar(root) {
        const container = root && root.closest ? root.closest('[data-transcribe]') || root : root;
        if (!container) return;
        const formPanel = container.querySelector('[data-transcribe-form-panel]');
        const sidebar = container.querySelector('[data-transcript-sidebar]');
        if (!formPanel || !sidebar) return;
    
        if (transcribeSidebarBinding) {
          window.removeEventListener('resize', transcribeSidebarBinding.onResize);
          if (transcribeSidebarBinding.mediaQuery && transcribeSidebarBinding.onMediaChange) {
            const previousQuery = transcribeSidebarBinding.mediaQuery;
            if (previousQuery.removeEventListener) {
              previousQuery.removeEventListener('change', transcribeSidebarBinding.onMediaChange);
            } else if (previousQuery.removeListener) {
              previousQuery.removeListener(transcribeSidebarBinding.onMediaChange);
            }
          }
          if (transcribeSidebarBinding.observer) {
            transcribeSidebarBinding.observer.disconnect();
          }
          if (transcribeSidebarBinding.sidebar && transcribeSidebarBinding.sidebar !== sidebar) {
            transcribeSidebarBinding.sidebar.style.maxHeight = '';
          }
          transcribeSidebarBinding = null;
        }
    
        const mediaQuery = window.matchMedia('(min-width: 1024px)');
        const apply = () => {
          if (!document.body.contains(formPanel) || !document.body.contains(sidebar)) {
            if (transcribeSidebarBinding) {
              window.removeEventListener('resize', transcribeSidebarBinding.onResize);
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
        window.addEventListener('resize', onResize, { passive: true });
        let observer = null;
        if (window.ResizeObserver) {
          observer = new ResizeObserver(() => apply());
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
    
      function setupTranscribeSection(root) {
        const form = root.querySelector('#transcribe-form');
        if (!form) return;
        const fileInput = form.querySelector('#transcribe-audio');
        const submitBtn = form.querySelector('[data-transcribe-submit]');
        const statusPill = root.querySelector('[data-transcribe-status-pill]');
        const progressWrap = root.querySelector('[data-transcribe-progress]');
        const progressBar = root.querySelector('[data-transcribe-progress-bar]');
        const progressLabel = root.querySelector('[data-transcribe-progress-label]');
        const summary = root.querySelector('[data-transcribe-summary]');
    
        function updateSubmitState() {
          if (!submitBtn) return;
          const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
          submitBtn.disabled = !hasFile;
        }
    
        form.addEventListener('change', updateSubmitState);
        updateSubmitState();
        syncTranscribeSidebar(root);
    
        document.body.addEventListener('htmx:beforeRequest', (evt) => {
          if (evt.target !== form) return;
          if (statusPill) {
            renderStatusLabel(statusPill, 'Uploading', 5);
          }
          if (progressWrap && progressBar && progressLabel) {
            progressWrap.classList.remove('hidden');
            progressBar.style.width = '5%';
            progressLabel.textContent = 'Starting upload…';
          }
        });
    
        document.body.addEventListener('htmx:xhr:progress', (evt) => {
          if (evt.target !== form) return;
          const loaded = evt.detail?.loaded ?? 0;
          const total = evt.detail?.total ?? 1;
          const pct = Math.max(0, Math.min(100, Math.round((loaded / total) * 100)));
          if (statusPill) {
            renderStatusLabel(statusPill, 'Uploading', pct);
          }
          if (progressWrap && progressBar && progressLabel) {
            progressWrap.classList.remove('hidden');
            progressBar.style.width = `${pct}%`;
            progressLabel.textContent = `${pct}% uploaded`;
          }
        });
    
        document.body.addEventListener('htmx:afterRequest', (evt) => {
          if (evt.target !== form) return;
          form.reset();
          updateSubmitState();
          if (progressWrap && progressBar && progressLabel) {
            progressWrap.classList.add('hidden');
            progressBar.style.width = '0%';
            progressLabel.textContent = '';
          }
          if (summary) {
            summary.textContent = 'Job queued. Monitoring status…';
          }
        });
      }
    
      function setupAnalysisActions(root) {
        const summaryContainer = root.querySelector('[data-summary]');
        if (summaryContainer) {
          const select = summaryContainer.querySelector('[data-summary-source]');
          const button = summaryContainer.querySelector('[data-analysis-action="summary"]');
          const updateDisabled = () => {
            if (!button) return;
            const option = select ? select.querySelector('option[value][disabled]:not([value=""])') : null;
            if (select && select.selectedOptions.length) {
              const selected = select.selectedOptions[0];
              button.disabled = selected.hasAttribute('disabled');
            } else {
              button.disabled = true;
            }
          };
          if (select) {
            select.addEventListener('change', updateDisabled);
            updateDisabled();
          }
        }
    
        const timelineContainer = root.querySelector('[data-timeline]');
        if (timelineContainer) {
          const transcriptSelect = timelineContainer.querySelector('[data-timeline-transcript]');
          const button = timelineContainer.querySelector('[data-analysis-action="timeline"]');
          const updateDisabled = () => {
            if (!button) return;
            if (!transcriptSelect || !transcriptSelect.value || transcriptSelect.selectedOptions[0]?.disabled) {
              button.disabled = true;
            } else {
              button.disabled = false;
            }
          };
          if (transcriptSelect) {
            transcriptSelect.addEventListener('change', updateDisabled);
            updateDisabled();
          }
        }
      }
    
      async function openTranscriptModal(jobId) {
        if (!jobId) return;
        try {
          const resp = await fetch(`/cases/${caseId}/jobs/${jobId}/transcript/`, {
            headers: { 'HX-Request': 'true' },
            credentials: 'same-origin',
          });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const html = await resp.text();
          const modal = openModalHTML(html, {
            container: modalRoot || undefined,
          });
          if (!modal) {
            showModalMessage({
              heading: 'Transcript Preview',
              title: 'Unable to load transcript',
              body: 'No transcript content available.',
              container: modalRoot || undefined,
            });
          }
        } catch (error) {
          console.error('Transcript preview failed', jobId, error);
          if (notify) {
            notify(window.innerWidth / 2, window.innerHeight / 2, 'Unable to load transcript');
          }
        }
      }
    
      async function expandJobRow(jobId) {
        if (!jobId) return false;
        const row = caseView.querySelector(`[data-job="${jobId}"]`);
        if (!row) return false;
        await jobsTableController.expand(row);
        row.focus({ preventScroll: true });
        const detailRow = caseView.querySelector(`[data-job-detail="${jobId}"]`);
        requestAnimationFrame(() => ensureElementVisible(detailRow || row, 'nearest'));
        return true;
      }
    
      document.body.addEventListener('click', async (evt) => {
        const transcriptAction = evt.target.closest('[data-transcript-action]');
        if (!transcriptAction) return;
        evt.preventDefault();
        const action = transcriptAction.getAttribute('data-transcript-action');
        const jobId = transcriptAction.getAttribute('data-job-id');
        const parentDetails = transcriptAction.closest('details');
        if (parentDetails) {
          parentDetails.removeAttribute('open');
        }
        if (action === 'view') {
          await openTranscriptModal(jobId);
        } else if (action === 'job') {
          const success = await expandJobRow(jobId);
          if (!success && notify) {
            notify(evt.clientX || window.innerWidth / 2, evt.clientY || window.innerHeight / 2, 'Job not available in this panel');
          }
        } else if (action === 'create-artifact') {
          const endpoint = transcriptAction.getAttribute('data-artifact-endpoint');
          if (!endpoint) return;
          const confirmed = await confirmWithModal({
            heading: 'Create Artifact',
            title: 'Promote transcript?',
            body: 'Add this transcript as a case artifact?',
            confirmLabel: 'Create artifact',
            cancelLabel: 'Cancel',
            container: modalRoot || undefined,
          });
          if (!confirmed) return;
          transcriptAction.disabled = true;
          const toastX = evt.clientX || window.innerWidth / 2;
          const toastY = evt.clientY || window.innerHeight / 2;
          try {
            const resp = await fetch(endpoint, {
              method: 'POST',
              headers: {
                'X-CSRFToken': getCSRFToken(),
                'Accept': 'application/json',
              },
              credentials: 'same-origin',
            });
            if (!resp.ok) {
              const text = await resp.text();
              throw new Error(text || `HTTP ${resp.status}`);
            }
            if (notify) {
              notify(toastX, toastY, 'Case artifact created');
            }
          } catch (error) {
            console.error('Create artifact failed', error);
            if (notify) {
              notify(toastX, toastY, 'Unable to create artifact');
            }
          } finally {
            transcriptAction.disabled = false;
          }
        }
      });
    
      document.body.addEventListener('click', async (evt) => {
        const jobLink = evt.target.closest('[data-job-link]');
        if (!jobLink) return;
        evt.preventDefault();
        const targetJobId = jobLink.getAttribute('data-job-link');
        if (!targetJobId) return;
        const linkCaseId = jobLink.getAttribute('data-job-link-case');
        if (!linkCaseId || linkCaseId === caseId) {
          const success = await expandJobRow(targetJobId);
          if (!success && notify) {
            const toastX = evt.clientX || window.innerWidth / 2;
            const toastY = evt.clientY || window.innerHeight / 2;
            notify(toastX, toastY, 'Job not available in this panel');
          }
          return;
        }
        window.location.href = `/cases/${linkCaseId}/`;
      });
    
      document.body.addEventListener('click', (evt) => {
        const card = evt.target.closest('[data-job-row]');
        if (card && evt.target.closest('button, a, input, textarea, select, [data-job-action-menu], [data-action-menu]') == null) {
          evt.preventDefault();
          jobsTableController.toggle(card);
        }
      });
    
      document.body.addEventListener('keydown', handleRowKey);
      document.body.addEventListener('click', handleRowClick);
      document.body.addEventListener('click', handleJobAction);
      document.body.addEventListener('click', handleVerifyHash);
      document.body.addEventListener('click', handleAudioRefresh);
      document.body.addEventListener('click', async (evt) => {
        const trigger = evt.target.closest('[data-job-view-log]');
        if (!trigger) return;
        evt.preventDefault();
        const jobId = trigger.getAttribute('data-job-id');
        const caseValue = trigger.getAttribute('data-case-id') || jobsState.currentCaseId;
        if (jobId && caseValue) {
          await openJobLogModal(caseValue, jobId);
        }
      });
    
      document.body.addEventListener('click', async (evt) => {
        const button = evt.target.closest('[data-analysis-action]');
        if (!button) return;
        evt.preventDefault();
        const action = button.getAttribute('data-analysis-action');
        const endpointTemplate = button.getAttribute('data-analysis-endpoint');
        if (!endpointTemplate) return;
        let jobId;
        let payload = {};
        if (action === 'summary') {
          const select = button.closest('[data-summary]')?.querySelector('[data-summary-source]');
          if (!select || !select.value) {
            button.disabled = true;
            return;
          }
          const selectedOption = select.selectedOptions[0];
          if (selectedOption && selectedOption.disabled) {
            if (notify) {
              notify(evt.clientX, evt.clientY, 'Transcript pending approval.');
            }
            return;
          }
          jobId = select.value;
        } else if (action === 'timeline') {
          const container = button.closest('[data-timeline]');
          const transcriptSelect = container?.querySelector('[data-timeline-transcript]');
          if (!transcriptSelect || !transcriptSelect.value || transcriptSelect.selectedOptions[0]?.disabled) {
            return;
          }
          jobId = transcriptSelect.value;
          const summarySelect = container.querySelector('[data-timeline-summary]');
          const artifactSelect = container.querySelector('[data-timeline-artifacts]');
          if (summarySelect && summarySelect.value) {
            payload.summary_artifact_id = summarySelect.value;
          }
          if (artifactSelect && artifactSelect.selectedOptions.length) {
            payload.artifact_ids = Array.from(artifactSelect.selectedOptions).map((opt) => opt.value).filter(Boolean);
          }
        }
        if (!jobId) return;
    
        button.disabled = true;
        const toastX = evt.clientX || window.innerWidth / 2;
        const toastY = evt.clientY || window.innerHeight / 2;
        try {
          const url = endpointTemplate.replace('{job_id}', jobId);
          const resp = await fetch(url, {
            method: 'POST',
            headers: {
              'X-CSRFToken': getCSRFToken(),
              'Accept': 'application/json',
              'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: Object.keys(payload).length ? JSON.stringify(payload) : null,
          });
          if (!resp.ok) {
            const text = await resp.text();
            throw new Error(text || `HTTP ${resp.status}`);
          }
          if (notify) {
            notify(toastX, toastY, 'Automation queued');
          }
          htmx.ajax('GET', `/cases/${caseId}/tools/${action}/`, '#tool-workspace');
        } catch (error) {
          console.error('Automation queue failed', action, error);
          if (notify) {
            notify(toastX, toastY, 'Unable to queue automation');
          }
        } finally {
          button.disabled = false;
        }
      });
    
      const refreshCaseJobs = function (caseIdParam) {
        if (caseIdParam) {
          jobsState.currentCaseId = caseIdParam;
        }
        const root = document.querySelector('#tool-workspace');
        if (!root) return;
        setupTranscribeSection(root.querySelector('[data-transcribe]') || root);
        setupAnalysisActions(root);
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
        if (caseAttr && caseAttr !== jobsState.currentCaseId) {
          jobsState.currentCaseId = caseAttr;
        }
        jobsBody.querySelectorAll('[data-job]').forEach((row) => {
          const jobId = row.dataset.job;
          if (!jobId) return;
          connectSocket(jobId);
          ensurePolling(jobId);
          const statusEl = document.getElementById(`job-status-${jobId}`);
          if (statusEl) {
            const statusValue = statusEl.dataset && statusEl.dataset.status ? statusEl.dataset.status : statusEl.textContent;
            const progressValue = statusEl.dataset && statusEl.dataset.progress ? parseFloat(statusEl.dataset.progress) : undefined;
            renderStatusLabel(statusEl, statusValue, progressValue);
            if (jobActions && typeof jobActions.updateForRow === 'function') {
              jobActions.updateForRow(jobId, statusValue);
            }
          }
        });
      };

      caseDetail.refresh = refreshCaseJobs;

      function boostJobs() {
        refreshCaseJobs(caseId);
      }

      caseDetail.boost = boostJobs;

      setActiveCard(initialToolKey);
      boostJobs();
  }

  caseDetail.init = init;
  init();
})(window);
