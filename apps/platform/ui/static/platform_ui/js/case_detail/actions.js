(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.actions) {
    return;
  }

  if (typeof platformUI.llmDebug === 'undefined') {
    let storedDebug = false;
    try {
      storedDebug = global.localStorage && global.localStorage.getItem('platformUI.llmDebug') === '1';
    } catch (_) {
      storedDebug = false;
    }
    platformUI.llmDebug = storedDebug;
    platformUI.enableLLMDebug = () => {
      try { global.localStorage && global.localStorage.setItem('platformUI.llmDebug', '1'); } catch (_) {}
      platformUI.llmDebug = true;
      console.info('[LLM] Debug logging enabled');
    };
    platformUI.disableLLMDebug = () => {
      try { global.localStorage && global.localStorage.removeItem('platformUI.llmDebug'); } catch (_) {}
      platformUI.llmDebug = false;
      console.info('[LLM] Debug logging disabled');
    };
  }

  const decodeUnicode = (value) => {
    if (typeof value !== 'string' || !/\u[0-9a-fA-F]{4}/.test(value)) {
      return value;
    }
    try {
      return value.replace(/\u([0-9a-fA-F]{4})/g, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
    } catch (_) {
      return value;
    }
  };

  const getEmbeddedJSON = (container, key) => {
    if (!container) return null;
    try {
      const script = container.querySelector(`[data-llm-json="${key}"]`);
      if (!script) return null;
      const text = script.textContent || '';
      if (!text.trim()) return null;
      const parsed = JSON.parse(text);
      if (platformUI.llmDebug) {
        console.debug('[LLM] Parsed embedded JSON', key, parsed);
      }
      return parsed;
    } catch (error) {
      if (platformUI.llmDebug) {
        console.warn('[LLM] Failed to parse embedded JSON', key, error);
      }
      return null;
    }
  };

  const helpers = caseDetail.helpers || {};
  helpers.decodeUnicode = decodeUnicode;
  helpers.getEmbeddedJSON = getEmbeddedJSON;
  caseDetail.helpers = helpers;

  let ctx = null;
  let deps = {};
  let analyzePendingSelection = null;

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
  }


  function setupLLMControls(container) {
    if (!container) return;

    const readEmbeddedJSON = (key) => {
      const el = container.querySelector(`[data-llm-json="${key}"]`);
      if (!el) return null;
      try {
        return JSON.parse(el.textContent || '');
      } catch (error) {
        if (platformUI.llmDebug) {
          console.warn('[LLM] Failed to parse embedded JSON', key, error);
        }
        return null;
      }
    };

    const rawConfigs = readEmbeddedJSON('configurations') || [];
    const activeFromJSON = readEmbeddedJSON('active-configuration');
    const stageDefinitions = readEmbeddedJSON('stage-configs') || [];
    const stageLabelMap = {};
    stageDefinitions.forEach((stage) => {
      if (stage && stage.key) {
        stageLabelMap[stage.key] = stage.label || stage.key;
      }
    });

    const configurations = rawConfigs.map((cfg, index) => ({
      ...cfg,
      _index: index,
      _key: cfg && cfg.id ? `id:${cfg.id}` : `idx:${index}`,
    }));

    if (!configurations.length && activeFromJSON) {
      configurations.push({
        ...activeFromJSON,
        _index: 0,
        _key: activeFromJSON.id ? `id:${activeFromJSON.id}` : 'idx:0',
      });
    }

    if (container.querySelector('[data-llm-config-select]')) {
      const options = container.querySelectorAll('[data-llm-config-select] option');
      options.forEach((option) => {
        const idx = Number(option.dataset.configIndex);
        if (Number.isInteger(idx) && configurations[idx]) {
          configurations[idx]._key = option.value;
        }
      });
    }

    let activeConfig = null;
    if (activeFromJSON && activeFromJSON.id) {
      activeConfig = configurations.find((cfg) => cfg.id && cfg.id === activeFromJSON.id) || null;
    }
    if (!activeConfig) {
      activeConfig = configurations[0] || null;
    }

    const configSelect = container.querySelector('[data-llm-config-select]');
    const nameDisplay = container.querySelector('[data-llm-config-name-display]');
    const descriptionDisplay = container.querySelector('[data-llm-config-description-display]');
    const providerDisplay = container.querySelector('[data-llm-config-provider-chain-display]');
    const stageListEl = container.querySelector('[data-llm-stage-list]');
    const stageEmptyEl = container.querySelector('[data-llm-stage-empty]');
    const editLink = container.querySelector('[data-llm-link="edit"]');
    const settingsBase = container.dataset.llmSettingsBase || '';
    const returnUrl = container.dataset.llmReturnUrl || '';

    const encode = (value) => encodeURIComponent(value || '');

    const updateEditLink = (config) => {
      if (!editLink || !settingsBase) return;
      if (config && config.id) {
        const nextParam = returnUrl ? `&next=${encode(returnUrl)}` : '';
        editLink.href = `${settingsBase}?config=${encode(config.id)}${nextParam}`;
        editLink.classList.remove('pointer-events-none', 'opacity-50');
      } else {
        const nextParam = returnUrl ? `?next=${encode(returnUrl)}` : '';
        editLink.href = `${settingsBase}${nextParam}`;
        editLink.classList.add('pointer-events-none', 'opacity-50');
      }
    };

    const setDatasetJSON = (prop, value) => {
      const hasValue =
        value &&
        ((Array.isArray(value) && value.length > 0) ||
          (typeof value === 'object' && Object.keys(value).length > 0));
      if (hasValue) {
        container.dataset[prop] = JSON.stringify(value);
      } else {
        delete container.dataset[prop];
      }
    };

    const renderStageOverrides = (stageMap) => {
      if (!stageListEl) return;
      stageListEl.innerHTML = '';
      const entries = Object.entries(stageMap || {}).filter(([, override]) => override && typeof override === 'object');
      if (!entries.length) {
        stageListEl.classList.add('hidden');
        if (stageEmptyEl) stageEmptyEl.classList.remove('hidden');
        return;
      }
      stageListEl.classList.remove('hidden');
      if (stageEmptyEl) stageEmptyEl.classList.add('hidden');
      entries.forEach(([stageKey, override]) => {
        const row = global.document.createElement('div');
        row.className = 'rounded border border-white/10 bg-slate-900/60 p-3';

        const title = global.document.createElement('p');
        title.className = 'text-sm font-semibold text-white';
        title.textContent = stageLabelMap[stageKey] || stageKey;
        row.appendChild(title);

        const details = global.document.createElement('dl');
        details.className = 'mt-1 space-y-1 text-xs text-slate-400';

        const provider = override.provider || (Array.isArray(override.providers) ? override.providers[0] : null);
        if (provider) {
          const wrapper = global.document.createElement('div');
          wrapper.innerHTML = '<dt class="inline font-semibold text-slate-300">Provider:</dt> <dd class="inline"></dd>';
          wrapper.querySelector('dd').textContent = provider;
          details.appendChild(wrapper);
        }

        if (override.model) {
          const wrapper = global.document.createElement('div');
          wrapper.innerHTML = '<dt class="inline font-semibold text-slate-300">Model:</dt> <dd class="inline"></dd>';
          wrapper.querySelector('dd').textContent = override.model;
          details.appendChild(wrapper);
        }

        if (override.max_tokens) {
          const wrapper = global.document.createElement('div');
          wrapper.innerHTML = '<dt class="inline font-semibold text-slate-300">Max tokens:</dt> <dd class="inline"></dd>';
          wrapper.querySelector('dd').textContent = override.max_tokens;
          details.appendChild(wrapper);
        }

        if (override.options && typeof override.options === 'object') {
          const optionWrapper = global.document.createElement('div');
          const dt = global.document.createElement('dt');
          dt.className = 'font-semibold text-slate-300';
          dt.textContent = 'Options:';
          const dd = global.document.createElement('dd');
          const list = global.document.createElement('ul');
          list.className = 'ml-4 list-disc space-y-0.5';
          Object.entries(override.options).forEach(([key, value]) => {
            const item = global.document.createElement('li');
            item.innerHTML = `<span class="font-semibold text-slate-300">${key.replace(/_/g, ' ')}:</span> ${value}`;
            list.appendChild(item);
          });
          dd.appendChild(list);
          optionWrapper.appendChild(dt);
          optionWrapper.appendChild(dd);
          details.appendChild(optionWrapper);
        }

        row.appendChild(details);
        stageListEl.appendChild(row);
      });
    };

    const renderConfigDetails = (config) => {
      if (!config) return;
      if (nameDisplay) nameDisplay.textContent = config.name || '(Untitled configuration)';
      if (descriptionDisplay) {
        descriptionDisplay.textContent = config.description || 'No notes added.';
      }
      const providerChain = Array.isArray(config.provider_chain) ? config.provider_chain.filter(Boolean) : [];
      if (providerDisplay) {
        if (providerChain.length) {
          providerDisplay.textContent = `Providers: ${providerChain.join(', ')}`;
        } else {
          providerDisplay.textContent = 'Providers will be selected automatically.';
        }
      }
      renderStageOverrides(config.stage_map || {});
      setDatasetJSON('llmStageMap', config.stage_map || {});
      setDatasetJSON('llmProviderChain', providerChain);
      if (config.id) {
        container.dataset.llmConfigId = config.id;
      } else {
        delete container.dataset.llmConfigId;
      }
    };

    const applyActiveConfiguration = (config) => {
      activeConfig = config || configurations[0] || null;
      if (!activeConfig) return;
      renderConfigDetails(activeConfig);
      updateEditLink(activeConfig);
      if (configSelect) {
        configSelect.value = activeConfig._key;
      }
      if (platformUI.llmDebug) {
        console.debug('[LLM] Active LLM configuration', {
          target: container.dataset.llmTarget,
          id: activeConfig.id,
          name: activeConfig.name,
        });
      }
    };

    applyActiveConfiguration(activeConfig);

    if (configSelect) {
      configSelect.addEventListener('change', () => {
        const value = configSelect.value;
        const next = configurations.find((cfg) => cfg._key === value);
        applyActiveConfiguration(next || configurations[0] || null);
      });
    }
  }


  function attachProviderModalHandlers(modal) {
    if (!modal) return;
    // Legacy hook: modal editing disabled in read-only view, so nothing to wire.
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
    if (platformUI.llmDebug) {
      console.debug('[LLM] Modal opened', {
        target: container.dataset.llmTarget,
        modalRoot: ctx?.modalRoot || 'body',
      });
    }
    // Nudge modal into view in cases where host disables scroll
    try {
      const modalEl = (modal.querySelector && modal.querySelector('[data-modal]')) || modal;
      // If our modal overlay uses fixed positioning, avoid scrolling the page; just focus it.
      const isFixedOverlay = modalEl && modalEl.classList && modalEl.classList.contains('fixed');
      setTimeout(() => {
        try {
          if (modalEl && modalEl.setAttribute) modalEl.setAttribute('tabindex', '-1');
          if (modalEl && modalEl.focus) modalEl.focus({ preventScroll: true });
          if (!isFixedOverlay && modalEl && modalEl.scrollIntoView) {
            modalEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
          }
        } catch (_) {}
      }, 0);
    } catch (_) {}
    try {
      const initModal = typeof container.llmInitModal === 'function' ? container.llmInitModal : attachProviderModalHandlers;
      initModal(modal);
    } catch (error) {
      console.warn('[LLM] Unable to initialise modal handlers', error);
    }
  }

  function closeActionMenu(menu) {
    if (!menu) return;
    const popovers = platformUI.popovers;
    if (popovers && typeof popovers.close === 'function') {
      popovers.close(menu);
      return;
    }
    menu.removeAttribute('open');
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
        const caseValue = control.getAttribute('data-case-id') || ctx.jobsState.currentCaseId || ctx.caseId;
        if (jobId && caseValue) {
          await deps.modals?.openJobLogModal(caseValue, jobId);
        }
      } else if (action === 'view-transcript') {
        const caseValue = control.getAttribute('data-case-id') || ctx.jobsState.currentCaseId || ctx.caseId;
        if (jobId && caseValue) {
          await deps.modals?.openTranscriptModal(caseValue, jobId);
        }
      } else if (action === 'view-metadata') {
        const caseValue = control.getAttribute('data-case-id') || ctx.jobsState.currentCaseId || ctx.caseId;
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

  function setAnalyzePendingSelection(jobId) {
    if (!jobId) return;
    analyzePendingSelection = jobId;
  }

  function resolveAnalyzePendingSelection() {
    const value = analyzePendingSelection;
    analyzePendingSelection = null;
    return value;
  }

  async function openSummaryTextUpload(select) {
    if (!ctx || !ctx.caseId || !deps.modals || typeof deps.modals.openFromHTML !== 'function') {
      return;
    }
    try {
      const resp = await fetch(`/cases/${ctx.caseId}/summary/upload-transcript-text/`, {
        headers: { 'HX-Request': 'true' },
        credentials: 'same-origin',
      });
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const html = await resp.text();
      const modal = deps.modals.openFromHTML(html, { container: ctx.modalRoot || undefined });
      if (!modal) {
        if (deps.notify) {
          deps.notify(global.innerWidth / 2, global.innerHeight / 2, 'Unable to open transcript text uploader');
        }
        return;
      }
      attachSummaryTextModal(modal, select);
    } catch (error) {
      console.error('Summary text upload modal failed', error);
      if (deps.notify) {
        deps.notify(global.innerWidth / 2, global.innerHeight / 2, 'Unable to load transcript text helper');
      }
    }
  }

  function attachSummaryTextModal(modal, select) {
    const container =
      modal.querySelector('[data-analyze-text-modal]') || modal.querySelector('[data-summary-text-modal]');
    if (!container) return;
    const endpoint =
      container.getAttribute('data-analyze-text-endpoint') || container.getAttribute('data-summary-text-endpoint');
    if (!endpoint) return;
    const statusEl =
      container.querySelector('[data-analyze-text-status]') || container.querySelector('[data-summary-text-status]');
    const uploadButton =
      container.querySelector('[data-analyze-text-upload-button]') ||
      container.querySelector('[data-summary-text-upload-button]');
    const uploadForm =
      container.querySelector('[data-analyze-text-upload-form]') ||
      container.querySelector('[data-summary-text-upload-form]');
    const fileInput =
      container.querySelector('[data-analyze-text-file]') || container.querySelector('[data-summary-text-file]');

    const setStatus = (message, variant = 'info') => {
      if (!statusEl) return;
      if (!message) {
        statusEl.classList.add('hidden');
        statusEl.textContent = '';
        return;
      }
      statusEl.textContent = message;
      statusEl.classList.remove('hidden');
      statusEl.classList.toggle('text-rose-300', variant === 'error');
      statusEl.classList.toggle('text-slate-400', variant !== 'error');
    };

    const resetUploadButton = () => {
      if (uploadButton) {
        uploadButton.disabled = true;
        uploadButton.textContent = 'Upload transcript';
      }
      setStatus('');
      if (fileInput) {
        fileInput.value = '';
      }
    };

    const handleSuccess = (data) => {
      if (!data || !data.job_id) {
        setStatus('Unexpected response from server.', 'error');
        return;
      }
      setAnalyzePendingSelection(data.job_id);
      if (deps.modals && typeof deps.modals.close === 'function') {
        deps.modals.close(modal);
      }
      if (deps.notify) {
        const rect = select && select.getBoundingClientRect ? select.getBoundingClientRect() : null;
        const toastX = rect ? rect.left + rect.width / 2 : global.innerWidth / 2;
        const toastY = rect ? rect.top + rect.height / 2 : global.innerHeight / 2;
        deps.notify(toastX, toastY, 'Transcript text registered');
      }
      if (deps.ui && typeof deps.ui.setActiveCard === 'function') {
        deps.ui.setActiveCard('summary');
      }
      const summaryUrl = `/cases/${ctx.caseId}/tools/summary/`;
      if (global.htmx && typeof global.htmx.ajax === 'function') {
        global.htmx.ajax('GET', summaryUrl, '#tool-workspace');
      } else {
        fetch(summaryUrl, { headers: { 'HX-Request': 'true' }, credentials: 'same-origin' })
          .then((resp) => (resp.ok ? resp.text() : null))
          .then((html) => {
            if (!html) return;
            const workspace = global.document.getElementById('tool-workspace');
            if (workspace) {
              workspace.innerHTML = html;
              deps.ui?.refreshCaseJobs?.(ctx.caseId);
            }
          })
          .catch(() => {});
      }
    };

    const handleError = (errorMessage) => {
      const message = errorMessage || 'Transcript upload failed.';
      setStatus(message, 'error');
      if (deps.notify) {
        deps.notify(global.innerWidth / 2, global.innerHeight / 2, message);
      }
    };

    const submitFixture = async (button) => {
      const name =
        button.getAttribute('data-analyze-text-fixture') || button.getAttribute('data-summary-text-fixture');
      if (!name) return;
      button.disabled = true;
      const originalText = button.textContent;
      button.textContent = 'Importing…';
      setStatus('');
      try {
        const resp = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            'X-CSRFToken': helpers.getCSRFToken(),
          },
          credentials: 'same-origin',
          body: JSON.stringify({ fixture_name: name }),
        });
        const data = await resp.json().catch(() => null);
        if (!resp.ok || !data || data.status !== 'ok') {
          const detail = data && data.detail ? data.detail : `HTTP ${resp.status}`;
          handleError(detail);
          return;
        }
        handleSuccess(data);
      } catch (error) {
        console.error('Fixture transcript import failed', error);
        handleError('Unable to copy fixture transcript.');
      } finally {
        button.disabled = false;
        button.textContent = originalText;
      }
    };

    const submitFile = async (file) => {
      if (!file) {
        handleError('Select a .txt transcript file.');
        return;
      }
      const formData = new global.FormData();
      formData.append('transcript_text', file);
      if (uploadButton) {
        uploadButton.disabled = true;
        uploadButton.textContent = 'Uploading…';
      }
      setStatus('Uploading…');
      try {
        const resp = await fetch(endpoint, {
          method: 'POST',
          headers: {
            Accept: 'application/json',
            'X-CSRFToken': helpers.getCSRFToken(),
          },
          credentials: 'same-origin',
          body: formData,
        });
        const data = await resp.json().catch(() => null);
        if (!resp.ok || !data || data.status !== 'ok') {
          const detail = data && data.detail ? data.detail : `HTTP ${resp.status}`;
          handleError(detail);
          return;
        }
        handleSuccess(data);
      } catch (error) {
        console.error('Transcript text upload failed', error);
        handleError('Upload failed.');
      } finally {
        resetUploadButton();
      }
    };

    container
      .querySelectorAll('[data-analyze-text-fixture], [data-summary-text-fixture]')
      .forEach((button) => {
        button.addEventListener('click', () => submitFixture(button));
      });

    if (uploadForm && fileInput) {
      fileInput.addEventListener('change', () => {
        if (fileInput.files && fileInput.files.length) {
          if (uploadButton) {
            uploadButton.disabled = false;
          }
        } else {
          resetUploadButton();
        }
      });
      uploadForm.addEventListener('submit', (evt) => {
        evt.preventDefault();
        const file = fileInput.files && fileInput.files.length ? fileInput.files[0] : null;
        submitFile(file);
      });
    }
  }

  function setupAnalysisActions(root) {
    if (!root) return;
    const analyzeContainer = root.querySelector('[data-analyze]') || root.querySelector('[data-summary]');
    if (platformUI.llmDebug) {
      console.debug('[LLM] setupAnalysisActions', {
        hasAnalyze: Boolean(analyzeContainer),
        hasTimeline: Boolean(root.querySelector('[data-timeline]')),
      });
    }
    if (analyzeContainer) {
      setupLLMControls(analyzeContainer);
      const select =
        analyzeContainer.querySelector('[data-analyze-source]') ||
        analyzeContainer.querySelector('[data-summary-source]');
      const button = analyzeContainer.querySelector('[data-analysis-action="analyze"]');

      const uploadOptionAttrs = ['data-analyze-upload-option', 'data-summary-upload-option'];
      const uploadTextAttrs = ['data-analyze-upload-text-option', 'data-summary-upload-text-option'];
      const isUploadOption = (option) => uploadOptionAttrs.some((attr) => option.hasAttribute(attr));
      const isUploadTextOption = (option) => uploadTextAttrs.some((attr) => option.hasAttribute(attr));
      const isSpecialOption = (option) => isUploadOption(option) || isUploadTextOption(option);

      const findFirstRunnableOption = () => {
        if (!select) return null;
        return (
          Array.from(select.options).find((option) => !option.disabled && !isSpecialOption(option)) || null
        );
      };

      let lastValidValue = null;
      if (select) {
        const current = select.selectedOptions[0];
        if (current && !current.disabled && !isSpecialOption(current)) {
          lastValidValue = current.value;
        } else {
          const firstRunnable = findFirstRunnableOption();
          if (firstRunnable) {
            lastValidValue = firstRunnable.value;
          }
        }
      }

      const openTranscriptUpload = () => {
        if (!ctx || !ctx.caseId) return;
        if (deps.ui?.setActiveCard) {
          deps.ui.setActiveCard('transcribe');
        }
        const url = `/cases/${ctx.caseId}/tools/transcribe/`;
        if (global.htmx && typeof global.htmx.ajax === 'function') {
          global.htmx.ajax('GET', url, '#tool-workspace');
        } else {
          fetch(url, { headers: { 'HX-Request': 'true' }, credentials: 'same-origin' })
            .then((resp) => (resp.ok ? resp.text() : null))
            .then((html) => {
              if (!html) return;
              const workspace = global.document.getElementById('tool-workspace');
              if (workspace) {
                workspace.innerHTML = html;
                deps.ui?.refreshCaseJobs?.(ctx.caseId);
              }
            })
            .catch(() => {});
        }
        const rect = select?.getBoundingClientRect();
        const toastX = rect ? rect.left + rect.width / 2 : global.innerWidth / 2;
        const toastY = rect ? rect.top + rect.height / 2 : global.innerHeight / 2;
        if (deps.notify) {
          deps.notify(toastX, toastY, 'Switching to transcription upload');
        }
        global.setTimeout(() => {
          try {
            const audioInput = global.document.getElementById('transcribe-audio');
            if (audioInput && typeof audioInput.focus === 'function') {
              audioInput.focus({ preventScroll: false });
            }
          } catch (_) {}
        }, 400);
      };

      const updateDisabled = () => {
        if (!button) return;
        if (!select || !select.selectedOptions.length) {
          button.disabled = true;
          return;
        }
        const selected = select.selectedOptions[0];
        const isDisabled = selected.disabled || selected.hasAttribute('disabled');
        button.disabled = isSpecialOption(selected) || isDisabled;
      };

      if (select) {
        select.addEventListener('change', (evt) => {
          const selected = select.selectedOptions[0];
          if (!selected) {
            updateDisabled();
            return;
          }
          if (isSpecialOption(selected)) {
            evt.preventDefault();
            if (isUploadOption(selected)) {
              openTranscriptUpload();
            } else if (isUploadTextOption(selected)) {
              openSummaryTextUpload(select);
            }
            if (lastValidValue) {
              select.value = lastValidValue;
            } else {
              const firstRunnable = findFirstRunnableOption();
              if (firstRunnable) {
                select.value = firstRunnable.value;
                if (!firstRunnable.disabled) {
                  lastValidValue = firstRunnable.value;
                }
              } else {
                select.selectedIndex = -1;
              }
            }
            updateDisabled();
            return;
          }
          if (!selected.disabled) {
            lastValidValue = selected.value;
          }
          const pending = resolveAnalyzePendingSelection();
          if (pending) {
            select.value = pending;
            lastValidValue = pending;
          }
          updateDisabled();
        });
        const pending = resolveAnalyzePendingSelection();
        if (pending) {
          const option = Array.from(select.options).find((opt) => opt.value === pending && !opt.disabled);
          if (option) {
            select.value = pending;
            lastValidValue = pending;
          }
        }
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
    if (action === 'analyze') {
      const analyzeContainer = button.closest('[data-analyze]') || button.closest('[data-summary]');
      const select =
        analyzeContainer?.querySelector('[data-analyze-source]') ||
        analyzeContainer?.querySelector('[data-summary-source]');
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

      const configId = analyzeContainer?.dataset.llmConfigId || null;
      if (configId) {
        payload.llm_config_id = configId;
        if (platformUI.llmDebug) console.debug('[LLM] Queueing with config', configId);
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
      const timelineConfigId = container?.dataset.llmConfigId || null;
      if (timelineConfigId) {
        payload.llm_config_id = timelineConfigId;
        if (platformUI.llmDebug) console.debug('[LLM] Queueing timeline with config', timelineConfigId);
      }
    } else if (action === 'compose') {
      const container = button.closest('[data-compose]');
      const summarySelect = container?.querySelector('[data-compose-summary]');
      if (!summarySelect || !summarySelect.value) {
        return;
      }
      if (summarySelect.value === '__upload__') {
        if (deps.notify) {
          deps.notify(evt.clientX, evt.clientY, 'Upload flow not yet supported.');
        }
        return;
      }
      jobId = summarySelect.value;
      payload.summary_job_id = jobId;
      const composeConfigId = container?.dataset.llmConfigId || container?.getAttribute('data-llm-config-id');
      if (composeConfigId) {
        payload.llm_config_id = composeConfigId;
        if (platformUI.llmDebug) console.debug('[LLM] Queueing compose with config', composeConfigId);
      }
    }
    if (!jobId) return;

    button.disabled = true;
    const toastX = evt.clientX || global.innerWidth / 2;
    const toastY = evt.clientY || global.innerHeight / 2;
    try {
      const url = endpointTemplate.replace('{job_id}', jobId);
      if (platformUI.llmDebug) {
        console.debug('[LLM] Queue request', {
          action,
          jobId,
          endpoint: url,
          payload,
        });
      }
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
      if (platformUI.llmDebug) {
        console.debug('[LLM] Queue failure details', { action, jobId, error });
      }
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
