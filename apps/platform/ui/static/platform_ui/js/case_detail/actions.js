(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.actions) {
    return;
  }

  const helpers = caseDetail.helpers || {};

  let ctx = null;
  let deps = {};

  function setContext(value) {
    ctx = value;
  }

  function setDeps(value) {
    deps = value || {};
  }

  function updateModelOptions(row) {
    if (!row) return;
    const providerSelect = row.querySelector('[data-llm-provider]');
    const modelSelect = row.querySelector('[data-llm-model]');
    const fallbackSelect = row.querySelector('[data-llm-fallback]');
    if (!providerSelect || !modelSelect) return;
    const provider = providerSelect.value;
    Array.from(modelSelect.options).forEach((option) => {
      const match = option.getAttribute('data-provider');
      if (!match || match === provider) {
        option.hidden = false;
        option.disabled = false;
      } else {
        option.hidden = true;
        option.disabled = true;
        if (option.selected) {
          option.selected = false;
        }
      }
    });
    if (!modelSelect.value) {
      const firstVisible = Array.from(modelSelect.options).find((opt) => !opt.hidden && !opt.disabled);
      if (firstVisible) {
        firstVisible.selected = true;
      }
    }
    if (fallbackSelect) {
      Array.from(fallbackSelect.options).forEach((option) => {
        if (option.value === provider) {
          option.disabled = true;
          option.selected = false;
        } else if (!option.hasAttribute('data-disabled')) {
          option.disabled = false;
        }
      });
    }
    const allowCheckbox = row.querySelector('[data-llm-allow-offline]');
    if (allowCheckbox) {
      const hasLocalFallback = provider === 'local'
        || (fallbackSelect && Array.from(fallbackSelect.options).some((opt) => opt.selected && opt.value === 'local'));
      allowCheckbox.disabled = !hasLocalFallback;
      if (!hasLocalFallback) {
        allowCheckbox.checked = false;
      }
    }
  }

  function collectProviderChain(overrides) {
    const sequence = [];
    Object.values(overrides || {}).forEach((config) => {
      if (!config) return;
      const primary = config.provider;
      const fallbacks = config.fallbacks || [];
      [primary].concat(fallbacks).forEach((name) => {
        if (name && !sequence.includes(name)) {
          sequence.push(name);
        }
      });
    });
    return sequence;
  }

  function setupLLMControls(container) {
    if (!container) return;
    const advanced = container.querySelector('[data-llm-advanced]');
    if (!advanced) return;
    const primarySelect = advanced.querySelector('[data-llm-provider-primary]');
    const fallbackSelect = advanced.querySelector('[data-llm-provider-fallback]');
    const allowOfflineCheckbox = advanced.querySelector('[data-llm-allow-offline]');

    const syncAdvancedControls = () => {
      const primaryValue = primarySelect?.value || null;
      if (fallbackSelect) {
        Array.from(fallbackSelect.options).forEach((option) => {
          if (!option.value) return;
          const permanent = option.hasAttribute('data-disabled');
          if (option.value === primaryValue) {
            option.disabled = true;
            option.selected = false;
          } else if (!permanent) {
            option.disabled = false;
          }
        });
      }
      if (allowOfflineCheckbox) {
        const chain = [];
        if (primaryValue) {
          chain.push(primaryValue);
        }
        if (fallbackSelect) {
          Array.from(fallbackSelect.options).forEach((option) => {
            if (option.selected && option.value && option.value !== primaryValue) {
              chain.push(option.value);
            }
          });
        }
        const hasLocal = chain.includes('local');
        allowOfflineCheckbox.disabled = !hasLocal;
        if (!hasLocal) {
          allowOfflineCheckbox.checked = false;
        }
      }
    };

    if (primarySelect) {
      primarySelect.addEventListener('change', syncAdvancedControls);
    }
    if (fallbackSelect) {
      fallbackSelect.addEventListener('change', syncAdvancedControls);
    }
    syncAdvancedControls();

    const llmButton = advanced.querySelector('[data-llm-open-modal]') || container.querySelector('[data-llm-open-modal]');
    if (llmButton) {
      llmButton.addEventListener('click', (evt) => {
        evt.preventDefault();
        openLLMModal(container);
      });
    }
  }

  async function persistLLMOverrides(target, overrides, chain) {
    if (!ctx?.caseId) {
      return null;
    }
    try {
      const resp = await fetch(`/cases/${ctx.caseId}/llm/settings/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': helpers.getCSRFToken(),
          Accept: 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ target, overrides, provider_chain: chain }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP ${resp.status}`);
      }
      return await resp.json();
    } catch (error) {
      console.warn('Persist LLM overrides failed', error);
      return null;
    }
  }

  function openLLMModal(container) {
    if (!caseDetail.modals || typeof caseDetail.modals.openFromHTML !== 'function') {
      return;
    }
    const template = container.querySelector('[data-llm-modal-template]');
    if (!template) return;
    const modal = caseDetail.modals.openFromHTML(template.innerHTML, { container: ctx?.modalRoot || undefined });
    if (!modal) {
      // Fallback: notify if modal system isn’t available
      if (caseDetail.modals && typeof caseDetail.modals.message === 'function') {
        caseDetail.modals.message({
          heading: 'LLM tuning',
          body: 'Unable to open modal window. Is the modal system loaded?',
          container: ctx?.modalRoot || undefined,
        });
      }
      return;
    }
    // Nudge modal into view in cases where host disables scroll
    try {
      const modalEl = (modal.querySelector && modal.querySelector('[data-modal]')) || modal;
      if (modalEl && modalEl.scrollIntoView) {
        // Give the DOM a tick to attach before scrolling
        setTimeout(() => {
          try {
            modalEl.setAttribute && modalEl.setAttribute('tabindex', '-1');
            modalEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
            modalEl.focus && modalEl.focus({ preventScroll: true });
          } catch (_) {}
        }, 0);
      }
    } catch (_) {}
    const form = modal.querySelector('[data-llm-form]');
    if (!form) return;
    const saveButton = form.querySelector('[data-llm-save]');
    const stageRows = Array.from(form.querySelectorAll('[data-llm-stage]'));
    const target = container.dataset.llmTarget || 'summary';
    let existingOverrides = {};
    if (container.dataset.llmOverrides) {
      try {
        existingOverrides = JSON.parse(container.dataset.llmOverrides);
      } catch (error) {
        existingOverrides = {};
      }
    }

    stageRows.forEach((row) => {
      const stageKey = row.getAttribute('data-stage-key');
      const override = stageKey ? existingOverrides[stageKey] : null;
      const providerSelect = row.querySelector('[data-llm-provider]');
      const fallbackSelect = row.querySelector('[data-llm-fallback]');
      const modelSelect = row.querySelector('[data-llm-model]');
      const allowCheckbox = row.querySelector('[data-llm-allow-offline]');
      if (override && providerSelect) {
        if (override.provider) {
          providerSelect.value = override.provider;
        }
        updateModelOptions(row);
        if (fallbackSelect && Array.isArray(override.fallbacks)) {
          const set = new Set(override.fallbacks.map(String));
          Array.from(fallbackSelect.options).forEach((option) => {
            option.selected = set.has(option.value) && !option.disabled;
          });
        }
        if (modelSelect && override.model) {
          modelSelect.value = override.model;
        }
        if (allowCheckbox && typeof override.allow_offline_fallback === 'boolean') {
          allowCheckbox.checked = override.allow_offline_fallback;
        }
      }
      if (providerSelect) {
        providerSelect.addEventListener('change', () => updateModelOptions(row));
      }
      if (fallbackSelect) {
        fallbackSelect.addEventListener('change', () => updateModelOptions(row));
      }
      updateModelOptions(row);
    });

    form.addEventListener('submit', async (evt) => {
      evt.preventDefault();
      if (saveButton) {
        saveButton.disabled = true;
        saveButton.textContent = 'Saving…';
      }
      const overrides = {};
      stageRows.forEach((row) => {
        const key = row.getAttribute('data-stage-key');
        if (!key) return;
        const providerSelect = row.querySelector('[data-llm-provider]');
        const modelSelect = row.querySelector('[data-llm-model]');
        const fallbackSelect = row.querySelector('[data-llm-fallback]');
        const allowCheckbox = row.querySelector('[data-llm-allow-offline]');
        if (!providerSelect) return;
        const fallbacks = fallbackSelect
          ? Array.from(fallbackSelect.options)
              .filter((opt) => opt.selected && opt.value && opt.value !== providerSelect.value)
              .map((opt) => opt.value)
          : [];
        overrides[key] = {
          provider: providerSelect.value,
          fallbacks,
          model: modelSelect ? modelSelect.value : '',
          allow_offline_fallback: allowCheckbox ? allowCheckbox.checked : false,
        };
      });
      container.dataset.llmOverrides = JSON.stringify(overrides);
      const chain = collectProviderChain(overrides);
      if (chain.length) {
        container.dataset.llmProviderChain = JSON.stringify(chain);
      } else {
        delete container.dataset.llmProviderChain;
      }
      const persisted = await persistLLMOverrides(target, overrides, chain);
      if (persisted && typeof persisted === 'object') {
        if (persisted.overrides && typeof persisted.overrides === 'object') {
          container.dataset.llmOverrides = JSON.stringify(persisted.overrides);
        }
        if (Array.isArray(persisted.provider_chain)) {
          container.dataset.llmProviderChain = JSON.stringify(persisted.provider_chain);
        }
      }
      if (caseDetail.modals && typeof caseDetail.modals.message === 'function') {
        caseDetail.modals.message({
          heading: 'LLM tuning',
          body: persisted ? 'Organization defaults updated.' : 'Settings applied for this job run.',
          container: ctx?.modalRoot || undefined,
        });
      }
      if (saveButton) {
        saveButton.disabled = false;
        saveButton.textContent = 'Save';
      }
      const closeButton = modal.querySelector('[data-modal-close]');
      if (closeButton) {
        closeButton.click();
      }
    });
  }

  function closeActionMenu(menu) {
    if (!menu) return;
    menu.removeAttribute('open');
    const popover = menu.querySelector('[data-popover]');
    if (popover && typeof popover.hide === 'function') {
      popover.hide();
    }
    menu.querySelectorAll('[data-popover]').forEach((trigger) => {
      if (trigger.dataset.popoverTarget) {
        const target = global.document.getElementById(trigger.dataset.popoverTarget);
        if (target && typeof target.hide === 'function') {
          target.hide();
        }
      }
    });
  }

  function handleRowClick(evt) {
    if (!ctx) return;
    const row = evt.target.closest('[data-job-row]');
    if (!row) return;
    if (evt.target.closest('a, button, input, textarea, select, [role="button"], [data-job-action-menu], [data-popover]')) return;
    evt.preventDefault();
    const table = deps.ui?.getTableController();
    table?.toggle(row);
  }

  function handleRowKey(evt) {
    if (!ctx) return;
    if (evt.target.closest('[data-job-row]') && (evt.key === 'Enter' || evt.key === ' ')) {
      if (evt.target.closest('a, button, input, textarea, select, [role="button"], [data-job-action-menu], [data-popover]')) return;
      evt.preventDefault();
      const table = deps.ui?.getTableController();
      table?.toggle(evt.target.closest('[data-job-row]'));
    }
  }

  function removeJobRow(jobId) {
    const row = global.document.querySelector(`[data-job="${jobId}"]`);
    const detail = global.document.querySelector(`[data-job-detail="${jobId}"]`);
    if (row) row.remove();
    if (detail) detail.remove();
  }

  async function handleJobAction(evt) {
    if (!ctx) return;
    const control = evt.target.closest('[data-job-action]');
    if (!control) return;
    evt.preventDefault();
    const jobId = control.getAttribute('data-job-id');
    const kind = control.getAttribute('data-job-action-kind') || 'api';
    const action = control.getAttribute('data-job-action');
    const menu = control.closest('[data-job-action-menu]');
    const closeMenu = () => closeActionMenu(menu);

    if (kind === 'modal') {
      if (action === 'view-log') {
        const caseValue = control.getAttribute('data-case-id') || ctx.jobsState.currentCaseId;
        if (jobId && caseValue) {
          await deps.modals?.openJobLogModal(caseValue, jobId);
        }
      } else if (action === 'view-transcript') {
        if (jobId) {
          await deps.modals?.openTranscriptModal(ctx.caseId, jobId);
        }
      } else if (action === 'view-metadata') {
        const caseValue = control.getAttribute('data-case-id') || ctx.jobsState.currentCaseId;
        if (jobId && caseValue) {
          await deps.modals?.openJobMetadataModal(caseValue, jobId);
        }
      }
      closeMenu();
      return;
    }

    if (kind === 'navigate') {
      const targetJob = control.getAttribute('data-job-target');
      if (targetJob) {
        const expanded = await actions.expandJobRow(targetJob);
        if (!expanded && deps.notify) {
          deps.notify(evt.clientX || global.innerWidth / 2, evt.clientY || global.innerHeight / 2, 'Job not available in this panel');
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
      const confirmed = await deps.modals?.confirm({
        heading: 'Confirm action',
        title: label || 'Please confirm',
        body: confirmMessage,
        confirmLabel: control.getAttribute('data-job-action-confirm-label') || (kind === 'delete' ? 'Delete' : 'Confirm'),
        cancelLabel: control.getAttribute('data-job-action-cancel-label') || 'Cancel',
        destructive: kind === 'delete',
        container: ctx.modalRoot || undefined,
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
      const response = global.prompt(promptMessage, '');
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
      'X-CSRFToken': helpers.getCSRFToken(),
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
        body: method === 'DELETE' ? null : requestBody || null,
      });
      if (!resp.ok) {
        const body = await resp.text();
        console.warn('Job action failed', endpointAction, body);
      } else if (method === 'DELETE') {
        removeJobRow(jobId);
        deps.ui?.scheduleTranscribeRefresh();
      } else {
        const data = await resp.json();
        deps.realtime?.handleJobUpdate(jobId, data, 'action');
        deps.realtime?.ensurePolling(jobId);
      }
    } catch (error) {
      console.warn('Job action error', action, error);
    } finally {
      control.disabled = false;
    }
  }

  async function handleJobNotesSave(evt) {
    if (!ctx) return;
    const button = evt.target.closest('[data-job-notes-save]');
    if (!button) return;
    evt.preventDefault();
    if (button.disabled) return;
    const container = button.closest('[data-job-notes]');
    if (!container) return;
    const jobId = button.getAttribute('data-job-id') || container.getAttribute('data-job-id');
    if (!jobId) return;
    const textarea = container.querySelector('[data-job-notes-input]');
    if (!textarea) return;
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = 'Saving…';

    try {
      const resp = await fetch(`/api/v1/jobs/${jobId}/notes/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': helpers.getCSRFToken(),
          Accept: 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ notes: textarea.value }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP ${resp.status}`);
      }
      const data = await resp.json();
      const notes = data && data.notes ? data.notes : {};
      helpers.updateNotes(container, notes);
      if (typeof deps.ui?.updateNotesIndicator === 'function') {
        const noteCount = typeof notes.count === 'number' ? notes.count : Array.isArray(notes.entries) ? notes.entries.length : 0;
        deps.ui.updateNotesIndicator(jobId, noteCount);
      }
      button.textContent = 'Saved!';
      if (deps.notify) {
        deps.notify(evt.clientX || global.innerWidth / 2, evt.clientY || global.innerHeight / 2, 'Notes updated');
      }
    } catch (error) {
      console.error('Job notes save failed', jobId, error);
      button.textContent = originalLabel || 'Save notes';
      if (deps.notify) {
        deps.notify(evt.clientX || global.innerWidth / 2, evt.clientY || global.innerHeight / 2, 'Unable to save notes');
      }
    } finally {
      setTimeout(() => {
        button.disabled = false;
        button.textContent = originalLabel || 'Save notes';
      }, 2000);
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
            'X-CSRFToken': helpers.getCSRFToken(),
            Accept: 'application/json',
          },
          credentials: 'same-origin',
        });
        if (!resp.ok) continue;
        const data = await resp.json();
        deps.realtime?.handleJobUpdate(id, data, 'verify');
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
    const markTargets = Array.from(
      new Set([
        jobId,
        ...corruptedAttr
          .split(',')
          .map((value) => value.trim())
          .filter(Boolean),
      ]),
    );
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
        tip = global.document.createElement('span');
        tip.dataset.verifyTooltip = '1';
        tip.setAttribute('role', 'status');
        tip.className =
          'pointer-events-none absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap rounded-md border border-white/20 bg-slate-900/95 px-2 py-1 text-[10px] font-semibold text-slate-100 shadow-lg shadow-black/40';
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
          'X-CSRFToken': helpers.getCSRFToken(),
          Accept: 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      if (resp.ok) {
        const data = await resp.json();
        const observed =
          typeof data.observed === 'string' && data.observed.length >= 12
            ? `${data.observed.slice(0, 8)}…${data.observed.slice(-4)}`
            : data.observed || 'n/a';
        const expected =
          typeof data.expected === 'string' && data.expected.length >= 12
            ? `${data.expected.slice(0, 8)}…${data.expected.slice(-4)}`
            : data.expected || 'n/a';
        resultType = data.result || null;
        if (data.result === 'match') {
          btn.textContent = 'Verified';
          ensureTooltip(`Hash verified (${observed})`, 'success');
        } else if (data.result === 'mismatch') {
          btn.textContent = 'Failed';
          ensureTooltip(`Expected ${expected}, got ${observed}`, 'error');
        } else if (data.result === 'computed') {
          btn.textContent = 'Verified';
          ensureTooltip(`Computed ${observed}`, 'info');
        } else {
          btn.textContent = 'Failed';
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
        btn.textContent = 'Failed';
      }
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
        tip = global.document.createElement('span');
        tip.dataset.verifyTooltip = '1';
        tip.setAttribute('role', 'status');
        tip.className =
          'pointer-events-none absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap rounded-md border border-white/20 bg-slate-900/95 px-2 py-1 text-[10px] font-semibold text-slate-100 shadow-lg shadow-black/40';
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
      if (deps.notify) {
        const toastX = evt.clientX || global.innerWidth / 2;
        const toastY = evt.clientY || global.innerHeight / 2;
        deps.notify(toastX, toastY, 'Metadata unavailable for this panel');
      }
      return;
    }
    const panel = global.document.querySelector(
      `[data-audio-panel="${panelKey}"][data-job-id="${displayJob}"]`,
    );
    if (!panel) return;
    const originalText = btn.textContent;
    const toastX = evt.clientX || global.innerWidth / 2;
    const toastY = evt.clientY || global.innerHeight / 2;
    btn.disabled = true;
    btn.textContent = 'Refreshing…';
    try {
      const resp = await fetch(`/api/v1/jobs/${refreshJobId}/refresh-audio/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': helpers.getCSRFToken(),
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
        helpers.updateAudioPanel(panel, data.audio);
        if (deps.notify) {
          deps.notify(toastX, toastY, 'Audio metadata updated');
        }
      }
    } catch (error) {
      console.warn('Audio metadata refresh failed', refreshJobId, error);
      if (deps.notify) {
        deps.notify(toastX, toastY, 'Unable to refresh metadata');
      }
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }

  function setupTranscribeSection(root) {
    if (!root) return;
    const form = root.querySelector('#transcribe-form');
    if (!form) return;
    const fileInput = form.querySelector('#transcribe-audio');
    const submitBtn = form.querySelector('[data-transcribe-submit]');
    const statusPill = root.querySelector('[data-transcribe-status-pill]');
    const progressWrap = root.querySelector('[data-transcribe-progress]');
    const progressBar = root.querySelector('[data-transcribe-progress-bar]');
    const progressLabel = root.querySelector('[data-transcribe-progress-label]');
    const summary = root.querySelector('[data-transcribe-summary]');
    const filenameLabel = form.querySelector('[data-transcribe-filename]');
    const defaultFilenameText = filenameLabel ? filenameLabel.textContent || 'Select audio file to continue' : 'Select audio file to continue';

    function updateSubmitState() {
      if (!submitBtn) return;
      const hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
      submitBtn.disabled = !hasFile;
      if (filenameLabel) {
        if (hasFile) {
          const file = fileInput.files[0];
          filenameLabel.textContent = file ? file.name : defaultFilenameText;
          filenameLabel.classList.remove('text-slate-300');
          filenameLabel.classList.add('text-primary-200');
        } else {
          filenameLabel.textContent = defaultFilenameText;
          filenameLabel.classList.remove('text-primary-200');
          filenameLabel.classList.add('text-slate-300');
        }
      }
    }

    form.addEventListener('change', updateSubmitState);
    if (fileInput) {
      fileInput.addEventListener('input', updateSubmitState);
    }
    updateSubmitState();
    deps.ui?.syncTranscribeSidebar(root);

    global.document.body.addEventListener('htmx:beforeRequest', (evt) => {
      if (evt.target !== form) return;
      const renderStatusLabel = deps.realtime?.renderStatusLabel() || (() => {});
      if (statusPill) {
        renderStatusLabel(statusPill, 'Uploading', 5);
      }
      if (progressWrap && progressBar && progressLabel) {
        progressWrap.classList.remove('hidden');
        progressBar.style.width = '5%';
        progressLabel.textContent = 'Starting upload…';
      }
    });

    global.document.body.addEventListener('htmx:xhr:progress', (evt) => {
      if (evt.target !== form) return;
      const loaded = evt.detail?.loaded ?? 0;
      const total = evt.detail?.total ?? 1;
      const pct = Math.max(0, Math.min(100, Math.round((loaded / total) * 100)));
      const renderStatusLabel = deps.realtime?.renderStatusLabel() || (() => {});
      if (statusPill) {
        renderStatusLabel(statusPill, 'Uploading', pct);
      }
      if (progressWrap && progressBar && progressLabel) {
        progressWrap.classList.remove('hidden');
        progressBar.style.width = `${pct}%`;
        progressLabel.textContent = `${pct}% uploaded`;
      }
    });

    global.document.body.addEventListener('htmx:afterRequest', (evt) => {
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
    if (!root) return;
    const summaryContainer = root.querySelector('[data-summary]');
    if (summaryContainer) {
      setupLLMControls(summaryContainer);
      const select = summaryContainer.querySelector('[data-summary-source]');
      const button = summaryContainer.querySelector('[data-analysis-action="summary"]');

      const updateDisabled = () => {
        if (!button) return;
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
      setupLLMControls(timelineContainer);
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

  async function expandJobRow(jobId) {
    if (!jobId || !ctx) return false;
    const row = ctx.caseView.querySelector(`[data-job="${jobId}"]`);
    if (!row) return false;
    const table = deps.ui?.getTableController();
    if (table && typeof table.expand === 'function') {
      await table.expand(row);
    }
    row.focus({ preventScroll: true });
    const detailRow = ctx.caseView.querySelector(`[data-job-detail="${jobId}"]`);
    global.requestAnimationFrame(() => helpers.ensureElementVisible(detailRow || row, 'nearest'));
    return true;
  }

  async function handleTranscriptAction(evt) {
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
      await deps.modals?.openTranscriptModal(ctx.caseId, jobId);
    } else if (action === 'job') {
      const success = await expandJobRow(jobId);
      if (!success && deps.notify) {
        deps.notify(evt.clientX || global.innerWidth / 2, evt.clientY || global.innerHeight / 2, 'Job not available in this panel');
      }
    } else if (action === 'create-artifact') {
      const endpoint = transcriptAction.getAttribute('data-artifact-endpoint');
      if (!endpoint) return;
      const confirmed = await deps.modals?.confirm({
        heading: 'Create Artifact',
        title: 'Promote transcript?',
        body: 'Add this transcript as a case artifact?',
        confirmLabel: 'Create artifact',
        cancelLabel: 'Cancel',
        container: ctx.modalRoot || undefined,
      });
      if (!confirmed) return;
      transcriptAction.disabled = true;
      const toastX = evt.clientX || global.innerWidth / 2;
      const toastY = evt.clientY || global.innerHeight / 2;
      try {
        const resp = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'X-CSRFToken': helpers.getCSRFToken(),
            Accept: 'application/json',
          },
          credentials: 'same-origin',
        });
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || `HTTP ${resp.status}`);
        }
        if (deps.notify) {
          deps.notify(toastX, toastY, 'Case artifact created');
        }
      } catch (error) {
        console.error('Create artifact failed', error);
        if (deps.notify) {
          deps.notify(toastX, toastY, 'Unable to create artifact');
        }
      } finally {
        transcriptAction.disabled = false;
      }
    }
  }

  async function handleJobLinkClick(evt) {
    const jobLink = evt.target.closest('[data-job-link]');
    if (!jobLink) return;
    evt.preventDefault();
    const targetJobId = jobLink.getAttribute('data-job-link');
    if (!targetJobId) return;
    const linkCaseId = jobLink.getAttribute('data-job-link-case');
    if (!linkCaseId || linkCaseId === ctx.caseId) {
      const success = await expandJobRow(targetJobId);
      if (!success && deps.notify) {
        const toastX = evt.clientX || global.innerWidth / 2;
        const toastY = evt.clientY || global.innerHeight / 2;
        deps.notify(toastX, toastY, 'Job not available in this panel');
      }
      return;
    }
    global.location.href = `/cases/${linkCaseId}/`;
  }

  async function handleJobViewLog(evt) {
    const trigger = evt.target.closest('[data-job-view-log]');
    if (!trigger) return;
    evt.preventDefault();
    const jobId = trigger.getAttribute('data-job-id');
    const caseValue = trigger.getAttribute('data-case-id') || ctx.jobsState.currentCaseId;
    if (jobId && caseValue) {
      await deps.modals?.openJobLogModal(caseValue, jobId);
    }
  }

  async function handleAnalysisAction(evt) {
    const button = evt.target.closest('[data-analysis-action]');
    if (!button) return;
    evt.preventDefault();
    const action = button.getAttribute('data-analysis-action');
    const endpointTemplate = button.getAttribute('data-analysis-endpoint');
    if (!endpointTemplate) return;
    let jobId;
    const payload = {};
    if (action === 'summary') {
      const summaryContainer = button.closest('[data-summary]');
      const select = summaryContainer?.querySelector('[data-summary-source]');
      if (!select || !select.value) {
        button.disabled = true;
        return;
      }
      const selectedOption = select.selectedOptions[0];
      if (selectedOption && selectedOption.disabled) {
        if (deps.notify) {
          deps.notify(evt.clientX, evt.clientY, 'Transcript pending approval.');
        }
        return;
      }
      jobId = select.value;

      const advanced = summaryContainer?.querySelector('[data-llm-advanced]');
      if (advanced) {
        const primarySelect = advanced.querySelector('[data-llm-provider-primary]');
        const fallbackSelect = advanced.querySelector('[data-llm-provider-fallback]');
        const allowOfflineCheckbox = advanced.querySelector('[data-llm-allow-offline]');
        const chain = [];
        if (primarySelect && primarySelect.value) {
          chain.push(primarySelect.value);
        }
        if (fallbackSelect) {
          Array.from(fallbackSelect.options).forEach((option) => {
            if (option.selected && option.value && (!primarySelect || option.value !== primarySelect.value)) {
              chain.push(option.value);
            }
          });
        }
        if (chain.length) {
          payload.provider_chain = chain;
        }
        if (allowOfflineCheckbox && !allowOfflineCheckbox.disabled) {
          payload.allow_offline_fallback = allowOfflineCheckbox.checked;
        }
      }
      const overridesValue = summaryContainer?.dataset.llmOverrides;
      if (overridesValue) {
        try {
          const overrides = JSON.parse(overridesValue);
          if (overrides && typeof overrides === 'object') {
            payload.stage_overrides = overrides;
          }
        } catch (error) {
          console.warn('Invalid LLM overrides payload', error);
        }
      }
      const chainOverride = summaryContainer?.dataset.llmProviderChain;
      if (chainOverride && !payload.provider_chain) {
        try {
          const chain = JSON.parse(chainOverride);
          if (Array.isArray(chain) && chain.length) {
            payload.provider_chain = chain;
          }
        } catch (error) {
          console.warn('Invalid provider chain override', error);
        }
      }
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
        payload.artifact_ids = Array.from(artifactSelect.selectedOptions)
          .map((opt) => opt.value)
          .filter(Boolean);
      }
    }
    if (!jobId) return;

    button.disabled = true;
    const toastX = evt.clientX || global.innerWidth / 2;
    const toastY = evt.clientY || global.innerHeight / 2;
    try {
      const url = endpointTemplate.replace('{job_id}', jobId);
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': helpers.getCSRFToken(),
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: Object.keys(payload).length ? JSON.stringify(payload) : null,
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `HTTP ${resp.status}`);
      }
      if (deps.notify) {
        deps.notify(toastX, toastY, 'Automation queued');
      }
      if (global.htmx && typeof global.htmx.ajax === 'function') {
        global.htmx.ajax('GET', `/cases/${ctx.caseId}/tools/${action}/`, '#tool-workspace');
      }
    } catch (error) {
      console.error('Automation queue failed', action, error);
      if (deps.notify) {
        deps.notify(toastX, toastY, 'Unable to queue automation');
      }
    } finally {
      button.disabled = false;
    }
  }

  caseDetail.actions = {
    setContext,
    setDeps,
    handleRowClick,
    handleRowKey,
    removeJobRow,
    handleJobAction,
    handleJobNotesSave,
    markJobsCorrupted,
    handleVerifyHash,
    handleAudioRefresh,
    setupTranscribeSection,
    setupAnalysisActions,
    expandJobRow,
    handleTranscriptAction,
    handleJobLinkClick,
    handleJobViewLog,
    handleAnalysisAction,
  };
})(window);
