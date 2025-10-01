(function () {
  const doc = window.document;
  const platformUI = (window.platformUI = window.platformUI || {});

  function toBool(value, fallback = false) {
    if (value == null) return fallback;
    const normalized = String(value).toLowerCase();
    if (['true', '1', 'yes', 'on'].includes(normalized)) return true;
    if (['false', '0', 'no', 'off'].includes(normalized)) return false;
    return fallback;
  }

  function resolveConfirmMessage(message, source) {
    if (message && message.trim()) return message;
    const ds = (source && source.dataset) || {};
    if (ds.confirmMessage && ds.confirmMessage.trim()) {
      return ds.confirmMessage;
    }
    return 'Are you sure?';
  }

  function resolveConfirmOptions(source, overrides = {}) {
    const ds = (source && source.dataset) || {};
    const options = { ...overrides };
    if (ds.confirmHeading) options.heading = ds.confirmHeading;
    if (ds.confirmTitle) options.title = ds.confirmTitle;
    if (ds.confirmConfirmLabel) options.confirmLabel = ds.confirmConfirmLabel;
    if (ds.confirmCancelLabel) options.cancelLabel = ds.confirmCancelLabel;
    if (ds.confirmDestructive != null) {
      options.destructive = toBool(ds.confirmDestructive, options.destructive === true);
    }
    if (ds.confirmContainer) options.container = ds.confirmContainer;
    return options;
  }

  async function confirmAction(message, overrides = {}, source) {
    const resolvedMessage = resolveConfirmMessage(message, source);
    const options = resolveConfirmOptions(source, overrides);
    const modalApi = platformUI.modal || {};
    if (modalApi && typeof modalApi.confirm === 'function') {
      try {
        return await modalApi.confirm({
          heading: options.heading || 'Confirm action',
          title: options.title || 'Please confirm',
          body: resolvedMessage,
          confirmLabel: options.confirmLabel || 'Confirm',
          cancelLabel: options.cancelLabel || 'Cancel',
          destructive: options.destructive === true,
          container: options.container,
        });
      } catch (error) {
        console.warn('[OrgSettings] Confirmation modal failed', error);
        return false;
      }
    }
    if (typeof window.confirm === 'function') {
      return window.confirm(resolvedMessage);
    }
    return true;
  }

  function parseJSONScript(id, fallback) {
    const el = doc.getElementById(id);
    if (!el) return fallback;
    try {
      return JSON.parse(el.textContent || "");
    } catch (error) {
      console.warn("[OrgSettings] Failed to parse JSON for", id, error);
      return fallback;
    }
  }

  function toNumber(raw) {
    if (raw == null || raw === "") return null;
    const value = Number(raw);
    return Number.isNaN(value) ? null : value;
  }

  function toFloat(raw) {
    if (raw == null || raw === "") return null;
    const value = parseFloat(raw);
    return Number.isNaN(value) ? null : value;
  }

  function populateCreatorSelect(select, creators, selected) {
    if (!select) return;
    if (!select.dataset.initialised) {
      creators.forEach((creator) => {
        const opt = doc.createElement("option");
        opt.value = creator.value;
        opt.textContent = creator.label;
        select.appendChild(opt);
      });
      select.dataset.initialised = "true";
    }
    if (selected) {
      select.value = selected;
    } else {
      select.value = "";
    }
  }

  function createModelRow(template, data, creatorOptions, handlers = {}) {
    const clone = template.content.firstElementChild.cloneNode(true);
    const name = clone.querySelector('input[name="model_name"]');
    const label = clone.querySelector('input[name="model_label"]');
    const tier = clone.querySelector('input[name="model_cost_tier"]');
    const maxTokens = clone.querySelector('input[name="model_max_output_tokens"]');
    const ctxTokens = clone.querySelector('input[name="model_context_window_tokens"]');
    const defaultTemp = clone.querySelector('input[name="model_default_temperature"]');
    const maxInputTokens = clone.querySelector('input[name="model_max_input_tokens"]');
    const maxChunkChars = clone.querySelector('input[name="model_max_chunk_chars"]');
    const chunkOverlap = clone.querySelector('input[name="model_chunk_overlap_tokens"]');
    const maxPromptChars = clone.querySelector('input[name="model_max_prompt_chars"]');
    const maxPromptSegments = clone.querySelector('input[name="model_max_prompt_segments"]');
    const deploymentEnv = clone.querySelector('input[name="model_deployment_env"]');
    const optionsJson = clone.querySelector('textarea[name="model_options_json"]');
    const enabledCheckbox = clone.querySelector('input[name="model_enabled"]');
    const originSelect = clone.querySelector('[data-model-origin]');
    const testButton = clone.querySelector('[data-provider-model-test]');

    const optionsRaw = (data && typeof data.options === 'object' && data.options)
      ? { ...data.options }
      : {};

    if (name && data?.name) name.value = data.name;
    if (label && data?.label) label.value = data.label;
    if (tier && data?.cost_tier) tier.value = data.cost_tier;
    if (maxTokens && data?.max_output_tokens != null) maxTokens.value = data.max_output_tokens;
    if (ctxTokens && data?.context_window_tokens != null) ctxTokens.value = data.context_window_tokens;
    if (defaultTemp && data?.default_temperature != null) defaultTemp.value = data.default_temperature;

    const resolveNumeric = (primary, fallback) => (
      primary != null ? primary : (fallback != null ? fallback : null)
    );

    const resolvedMaxInput = resolveNumeric(data?.max_input_tokens, optionsRaw.max_input_tokens);
    if (maxInputTokens && resolvedMaxInput != null) maxInputTokens.value = resolvedMaxInput;
    const resolvedMaxChunk = resolveNumeric(data?.max_chunk_chars, optionsRaw.max_chunk_chars);
    if (maxChunkChars && resolvedMaxChunk != null) maxChunkChars.value = resolvedMaxChunk;
    const resolvedChunkOverlap = resolveNumeric(
      data?.chunk_overlap_tokens,
      optionsRaw.chunk_overlap_tokens,
    );
    if (chunkOverlap && resolvedChunkOverlap != null) chunkOverlap.value = resolvedChunkOverlap;
    const resolvedMaxPromptChars = resolveNumeric(
      data?.max_prompt_chars,
      optionsRaw.max_prompt_chars,
    );
    if (maxPromptChars && resolvedMaxPromptChars != null) maxPromptChars.value = resolvedMaxPromptChars;
    const resolvedMaxPromptSegments = resolveNumeric(
      data?.max_prompt_segments,
      optionsRaw.max_prompt_segments,
    );
    if (maxPromptSegments && resolvedMaxPromptSegments != null) {
      maxPromptSegments.value = resolvedMaxPromptSegments;
    }

    const resolvedDeployment = data?.deployment_env || optionsRaw.azure_deployment;
    if (deploymentEnv && resolvedDeployment) deploymentEnv.value = resolvedDeployment;

    const advancedOptions = { ...optionsRaw };
    [
      'max_input_tokens',
      'max_chunk_chars',
      'chunk_overlap_tokens',
      'max_prompt_chars',
      'max_prompt_segments',
    ].forEach((key) => {
      if (key in advancedOptions) delete advancedOptions[key];
    });
    if (resolvedDeployment && advancedOptions.azure_deployment === resolvedDeployment) {
      delete advancedOptions.azure_deployment;
    }
    if (optionsJson) {
      if (Object.keys(advancedOptions).length) {
        optionsJson.value = JSON.stringify(advancedOptions, null, 2);
      } else {
        optionsJson.value = '';
      }
    }
    if (enabledCheckbox) enabledCheckbox.checked = data?.enabled !== false;
    populateCreatorSelect(originSelect, creatorOptions, data?.origin);

    const removeBtn = clone.querySelector('[data-provider-model-remove]');
    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        clone.remove();
      });
    }

    if (testButton && typeof handlers.onTest === 'function') {
      testButton.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        handlers.onTest({ row: clone, button: testButton });
      });
    }

    return clone;
  }

  function serializeModelRow(row) {
    const name = row.querySelector('input[name="model_name"]')?.value?.trim();
    if (!name) return null;
    const label = row.querySelector('input[name="model_label"]')?.value?.trim();
    const costTier = row.querySelector('input[name="model_cost_tier"]')?.value?.trim();
    const origin = row.querySelector('[data-model-origin]')?.value?.trim();
    const enabled = row.querySelector('input[name="model_enabled"]')?.checked ?? true;
    const payload = {
      name,
      label: label || name,
      cost_tier: costTier || "standard",
      enabled,
    };

    const maxTokens = toNumber(row.querySelector('input[name="model_max_output_tokens"]')?.value?.trim());
    if (maxTokens != null) payload.max_output_tokens = maxTokens;
    const ctxTokens = toNumber(row.querySelector('input[name="model_context_window_tokens"]')?.value?.trim());
    if (ctxTokens != null) payload.context_window_tokens = ctxTokens;
    const defaultTemp = toFloat(row.querySelector('input[name="model_default_temperature"]')?.value?.trim());
    if (defaultTemp != null) payload.default_temperature = defaultTemp;
    if (origin) payload.origin = origin;

    const options = {};
    const maxInputTokens = toNumber(row.querySelector('input[name="model_max_input_tokens"]')?.value?.trim());
    if (maxInputTokens != null) {
      payload.max_input_tokens = maxInputTokens;
      options.max_input_tokens = maxInputTokens;
    }
    const maxChunkChars = toNumber(row.querySelector('input[name="model_max_chunk_chars"]')?.value?.trim());
    if (maxChunkChars != null) {
      payload.max_chunk_chars = maxChunkChars;
      options.max_chunk_chars = maxChunkChars;
    }
    const chunkOverlap = toNumber(row.querySelector('input[name="model_chunk_overlap_tokens"]')?.value?.trim());
    if (chunkOverlap != null) {
      payload.chunk_overlap_tokens = chunkOverlap;
      options.chunk_overlap_tokens = chunkOverlap;
    }
    const maxPromptChars = toNumber(row.querySelector('input[name="model_max_prompt_chars"]')?.value?.trim());
    if (maxPromptChars != null) {
      payload.max_prompt_chars = maxPromptChars;
      options.max_prompt_chars = maxPromptChars;
    }
    const maxPromptSegments = toNumber(row.querySelector('input[name="model_max_prompt_segments"]')?.value?.trim());
    if (maxPromptSegments != null) {
      payload.max_prompt_segments = maxPromptSegments;
      options.max_prompt_segments = maxPromptSegments;
    }
    const deploymentEnv = row.querySelector('input[name="model_deployment_env"]')?.value?.trim();
    if (deploymentEnv) {
      payload.deployment_env = deploymentEnv;
      options.azure_deployment = deploymentEnv;
    }

    const optionsJson = row.querySelector('textarea[name="model_options_json"]')?.value?.trim();
    if (optionsJson) {
      try {
        const parsed = JSON.parse(optionsJson);
        if (parsed && typeof parsed === 'object') {
          Object.assign(options, parsed);
        }
      } catch (error) {
        console.warn('[OrgSettings] Failed to parse model options JSON', error);
      }
    }

    if (Object.keys(options).length) {
      payload.options = options;
    }

    return payload;
  }

  function setupProviderPanel() {
    const panel = doc.querySelector('[data-provider-panel]');
    if (!panel) return;

    const providers = parseJSONScript('organization-provider-data', []);
    const catalog = parseJSONScript('organization-provider-catalog', {});
    const credentials = parseJSONScript('organization-provider-credentials', {});
    const creators = parseJSONScript('organization-provider-model-creators', []);
    const selectedUuid = parseJSONScript('organization-provider-selected-uuid', '');

    const form = panel.querySelector('[data-provider-form]');
    const select = form?.querySelector('[data-provider-select]');
    const providerKeyHidden = form?.querySelector('[data-provider-key]');
    const providerUuidHidden = form?.querySelector('[data-provider-uuid]');

    function slugifyProviderName(name) {
      return String(name || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 64);
    }
    const displayInput = form?.querySelector('[data-provider-display]');
    const endpointInput = form?.querySelector('[data-provider-endpoint]');
    const apiKeyInput = form?.querySelector('[data-provider-apikey]');
    const clearCheckbox = form?.querySelector('[data-provider-clear]');
    const modelContainer = form?.querySelector('[data-provider-model-rows]');
    const template = form?.querySelector('[data-provider-model-template]');
    const addModelBtn = form?.querySelector('[data-provider-model-add]');
    const modelJsonOverride = form?.querySelector('[data-provider-model-json]');
    const metadataJson = form?.querySelector('[data-provider-metadata-json]');
    const compiledInput = form?.querySelector('[data-provider-models-compiled]');
    const resetBtn = form?.querySelector('[data-provider-reset]');
    const templateSelect = form?.querySelector('[data-provider-template]');
    const templateApplyBtn = form?.querySelector('[data-provider-template-apply]');
    const deleteButton = form?.querySelector('[data-provider-delete]');
    const modelTestPayloadInput = form?.querySelector('[data-provider-model-test-payload]');

    const providerMap = providers.reduce((acc, item) => {
      acc[item.key] = item;
      return acc;
    }, {});
    const uuidToProviderKey = Object.entries(credentials || {}).reduce((acc, [key, value]) => {
      if (!value) return acc;
      const uid = value.uid != null ? String(value.uid) : '';
      if (uid) acc[uid] = key;
      return acc;
    }, {});

    let currentProviderKey = '';
    let currentProviderUuid = '';
    if (selectedUuid && uuidToProviderKey[selectedUuid]) {
      currentProviderKey = uuidToProviderKey[selectedUuid];
      currentProviderUuid = selectedUuid;
    } else if (providers.length) {
      currentProviderKey = providers[0].key || '';
      const initialCred = credentials[currentProviderKey];
      if (initialCred?.uid) {
        currentProviderUuid = String(initialCred.uid);
      }
    }

    function setDeleteVisible(visible) {
      if (!deleteButton) return;
      deleteButton.classList.toggle('hidden', !visible);
    }

    function updateDeleteConfirmDetails(name) {
      if (!deleteButton) return;
      const trimmed = (name || '').trim();
      const targetName = trimmed ? `“${trimmed}”` : 'this provider';
      deleteButton.dataset.confirmHeading = deleteButton.dataset.confirmHeading || 'Confirm action';
      deleteButton.dataset.confirmTitle = 'Delete provider';
      deleteButton.dataset.confirmConfirmLabel = 'Delete';
      deleteButton.dataset.confirmCancelLabel = 'Cancel';
      deleteButton.dataset.confirmDestructive = 'true';
      deleteButton.dataset.confirmMessage = `Delete provider ${targetName}? This cannot be undone.`;
    }

    function clearModels() {
      if (!modelContainer) return;
      modelContainer.innerHTML = '';
    }

    function handleModelTest({ row, button }) {
      if (!form || !row || !button) return;
      const payload = serializeModelRow(row);
      if (!payload) {
        window.alert('Provide a model ID before testing this model.');
        return;
      }
      if (!modelTestPayloadInput) return;
      modelTestPayloadInput.value = JSON.stringify(payload);
      form.requestSubmit(button);
    }

    function populateModels(list) {
      if (!modelContainer || !template) return;
      clearModels();
      (list || []).forEach((model) => {
        const normalized = {
          ...model,
          options: model.options || {},
        };
        modelContainer.appendChild(
          createModelRow(template, normalized, creators, { onTest: handleModelTest }),
        );
      });
    }

    function buildModelsPayload() {
      if (!modelContainer) return [];
      const rows = Array.from(modelContainer.querySelectorAll('[data-provider-model-row]'));
      return rows.map(serializeModelRow).filter(Boolean);
    }

    function resolveCatalog(key) {
      const entry = catalog?.[key];
      if (!entry) return null;
      const models = entry.models || {};
      return {
        display_name: entry.display_name || key,
        endpoint: entry.default_endpoint || '',
        models: Object.entries(models).map(([value, meta]) => ({
          name: value,
          label: meta.label || value,
          cost_tier: meta.cost_tier || 'standard',
          max_output_tokens: meta.max_output_tokens,
          context_window_tokens: meta.context_window_tokens,
          default_temperature: meta.default_temperature,
          origin: meta.origin,
          max_input_tokens: meta.max_input_tokens,
          max_chunk_chars: meta.max_chunk_chars,
          chunk_overlap_tokens: meta.chunk_overlap_tokens,
          max_prompt_chars: meta.max_prompt_chars,
          max_prompt_segments: meta.max_prompt_segments,
          enabled: meta.default_enabled !== false,
          options: meta.options || {},
          deployment_env: meta.deployment_env,
        })),
      };
    }

    function applyTemplate(templateKey) {
      if (!form) return;
      const templateData = resolveCatalog(templateKey);
      if (!templateData) return;
      const providerValue = (providerKeyHidden?.value || '').trim() || templateKey;
      applyFormValues({
        providerKey: providerValue,
        providerUuid: '',
        displayName: templateData.display_name || providerValue,
        endpoint: templateData.endpoint || '',
        models: templateData.models || [],
        metadata: {},
      });
      if (templateSelect) templateSelect.value = templateKey;
      setDeleteVisible(false);
      currentProviderKey = '';
      currentProviderUuid = '';
      if (providerKeyHidden && !providerKeyHidden.value) {
        providerKeyHidden.value = templateKey;
      }
    }

    function getCredential(key) {
      return credentials[key] || null;
    }

    function applyFormValues({
      providerKey,
      providerUuid,
      displayName,
      endpoint,
      models,
      metadata,
    }) {
      if (!form) return;
      if (select) select.value = providerKey || '';
      if (providerKeyHidden) providerKeyHidden.value = providerKey || '';
      if (displayInput) displayInput.value = displayName || '';
      updateDeleteConfirmDetails(displayName || providerKey);
      if (endpointInput) endpointInput.value = endpoint || '';
      if (apiKeyInput) apiKeyInput.value = '';
      if (clearCheckbox) clearCheckbox.checked = false;
      if (modelJsonOverride) modelJsonOverride.value = '';
      if (metadataJson) {
        metadataJson.value = metadata && Object.keys(metadata).length
          ? JSON.stringify(metadata, null, 2)
          : '';
      }
      populateModels(models || []);
      if (compiledInput) compiledInput.value = '';
      if (modelTestPayloadInput) modelTestPayloadInput.value = '';
      const uuidHidden = form?.querySelector('[data-provider-uuid]');
      const resolvedUuid = providerUuid ? String(providerUuid) : '';
      if (uuidHidden) uuidHidden.value = resolvedUuid;
      currentProviderUuid = resolvedUuid;
    }

    function fillForm(key, uuidOverride) {
      if (!form) return;
      const cred = getCredential(key);
      const providerInfo = providerMap[key] || {};
      const catalogDefaults = resolveCatalog(key);
      applyFormValues({
        providerKey: key,
        providerUuid: uuidOverride || cred?.uid || providerInfo.uid || '',
        displayName: cred?.display_name
          || providerInfo.label
          || catalogDefaults?.display_name
          || key,
        endpoint: cred?.endpoint
          || providerInfo.endpoint
          || catalogDefaults?.endpoint
          || '',
        models: cred?.models?.length ? cred.models : providerInfo.models || catalogDefaults?.models || [],
        metadata: cred?.metadata || {},
      });
      if (templateSelect) templateSelect.value = '';
      setDeleteVisible(Boolean(cred));
      currentProviderKey = key;
      currentProviderUuid = uuidOverride
        || (cred?.uid ? String(cred.uid) : (providerInfo.uid ? String(providerInfo.uid) : ''));
      const uuidHidden2 = form?.querySelector('[data-provider-uuid]');
      if (uuidHidden2) uuidHidden2.value = currentProviderUuid;
    }

    function resetForm() {
      currentProviderKey = '';
      currentProviderUuid = '';
      applyFormValues({
        providerKey: '',
        providerUuid: '',
        displayName: '',
        endpoint: '',
        models: [],
        metadata: {},
      });
      if (templateSelect) templateSelect.value = '';
      if (providerKeyHidden) providerKeyHidden.value = '';
      const uuidHidden3 = form?.querySelector('[data-provider-uuid]');
      if (uuidHidden3) uuidHidden3.value = '';
      setDeleteVisible(false);
      (displayInput || endpointInput)?.focus();
    }

    function updateModelCount(row, models, providerKey) {
      const summaryEl = row.querySelector('[data-provider-model-summary]');
      if (!summaryEl) return;
      const total = models.length;
      const enabled = models.filter((model) => model.enabled !== false).length;
      summaryEl.textContent = `Models: ${enabled} / ${total}`;
      if (providerMap[providerKey]) {
        providerMap[providerKey].models_enabled_count = enabled;
        providerMap[providerKey].models_total_count = total;
      }
    }

    function submitProviderUpdate(providerKey, { models, enabled }) {
      if (!form) return;
      const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
      if (!csrfInput) {
        console.warn('[OrgSettings] Missing CSRF token');
        return;
      }
      const providerInfo = providerMap[providerKey] || {};
      const cred = credentials[providerKey] || {};
      const tempForm = doc.createElement('form');
      tempForm.method = 'post';
      tempForm.action = form.getAttribute('action') || window.location.href;
      tempForm.className = 'hidden';
      const csrfClone = csrfInput.cloneNode(true);
      tempForm.appendChild(csrfClone);

      const appendHidden = (name, value) => {
        const input = doc.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        tempForm.appendChild(input);
      };

      appendHidden('action', 'provider-upsert');
      appendHidden('provider', providerKey);
      appendHidden('display_name', cred.display_name || providerInfo.label || providerKey);
      appendHidden('endpoint', cred.endpoint || providerInfo.endpoint || '');
      appendHidden('models_payload_compiled', JSON.stringify(models));
      appendHidden('metadata_json', JSON.stringify(cred.metadata || {}));
      appendHidden('is_enabled', (enabled != null ? enabled : (cred.is_enabled ?? providerInfo.enabled ?? false)) ? '1' : '0');
      appendHidden('provider_uuid', cred.uid ? String(cred.uid) : '');

      doc.body.appendChild(tempForm);
      tempForm.submit();
    }

    if (select) {
      select.addEventListener('change', () => {
        const key = (select.value || '').trim();
        if (key) {
          const cred = getCredential(key);
          const info = providerMap[key] || {};
          const uuid = cred?.uid ? String(cred.uid) : (info.uid ? String(info.uid) : '');
          fillForm(key, uuid);
        } else {
          resetForm();
        }
        if (providerKeyHidden) providerKeyHidden.value = key || '';
      });
    }

    if (displayInput) {
      displayInput.addEventListener('input', () => {
        if (!currentProviderKey && providerKeyHidden) {
          providerKeyHidden.value = slugifyProviderName(displayInput.value || '');
        }
      });
    }

    templateApplyBtn?.addEventListener('click', async () => {
      const key = (templateSelect?.value || '').trim();
      if (!key) return;
      if (currentProviderKey) {
        const confirmed = await confirmAction(
          'Loading a template will overwrite the form values. Continue?',
          {
            title: 'Load template',
            confirmLabel: 'Load template',
            cancelLabel: 'Cancel',
          },
          templateApplyBtn,
        );
        if (!confirmed) return;
      }
      applyTemplate(key);
    });

    if (templateSelect && !templateApplyBtn) {
      templateSelect.addEventListener('change', async () => {
        const key = (templateSelect.value || '').trim();
        if (!key) return;
        if (currentProviderKey) {
          const confirmed = await confirmAction(
            'Loading a template will overwrite the form values. Continue?',
            {
              title: 'Load template',
              confirmLabel: 'Load template',
              cancelLabel: 'Cancel',
            },
            templateSelect,
          );
          if (!confirmed) {
            templateSelect.value = '';
            return;
          }
        }
        applyTemplate(key);
      });
    }

    addModelBtn?.addEventListener('click', () => {
      if (!template || !modelContainer) return;
      modelContainer.appendChild(
        createModelRow(template, { enabled: true, options: {} }, creators, { onTest: handleModelTest }),
      );
    });

    resetBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      resetForm();
    });

    deleteButton?.addEventListener('click', async (event) => {
      event.preventDefault();
      const confirmed = await confirmAction(
        '',
        {
          title: 'Delete provider',
          confirmLabel: 'Delete',
          cancelLabel: 'Cancel',
          destructive: true,
        },
        deleteButton,
      );
      if (!confirmed) return;
      const formEl = deleteButton.closest('form');
      if (formEl) {
        formEl.submit();
      }
    });

    form?.addEventListener('submit', () => {
      if (!compiledInput) return;
      if (modelJsonOverride && modelJsonOverride.value.trim()) {
        compiledInput.value = '';
        return;
      }
      const modelsPayload = buildModelsPayload();
      compiledInput.value = modelsPayload.length ? JSON.stringify(modelsPayload) : '';
    });

    // Edit buttons removed with Actions column; row click still loads editor.

    doc.querySelectorAll('[data-provider-row]').forEach((row) => {
      const providerKey = row.getAttribute('data-provider-key');
      const providerUuid = row.getAttribute('data-provider-uuid') || '';
      if (!providerKey) return;

      row.addEventListener('click', (event) => {
        const interactive = event.target.closest('button, input, label, a, textarea, select, form');
        if (interactive) return;
        fillForm(providerKey, providerUuid);
        form?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });

      const entry = providerMap[providerKey];
      if (!entry) return;

      const modelItems = Array.from(row.querySelectorAll('[data-provider-model-item]'));
      modelItems.forEach((item) => {
        const modelKey = item.getAttribute('data-model-name');
        const checkbox = item.querySelector('[data-provider-model-toggle]');
        if (!modelKey || !checkbox) return;
        checkbox.addEventListener('change', () => {
          const updatedModels = (entry.models || []).map((model) => {
            if (!model || !model.value) return model;
            if (model.value === modelKey) {
              return { ...model, enabled: checkbox.checked };
            }
            return model;
          });
          entry.models = updatedModels;
          if (credentials[providerKey]) {
            credentials[providerKey] = {
              ...credentials[providerKey],
              models: updatedModels,
            };
          }
          updateModelCount(row, updatedModels, providerKey);
          submitProviderUpdate(providerKey, { models: updatedModels });
        });
      });

      updateModelCount(row, entry.models || [], providerKey);
    });

    doc.querySelectorAll('[data-provider-toggle]').forEach((checkbox) => {
      checkbox.addEventListener('change', async (event) => {
        const target = event.currentTarget;
        if (!target) return;
        const row = target.closest('[data-provider-row]');
        if (!row) return;
        const desired = target.checked;
        const canEnableAttr = target.getAttribute('data-provider-can-enable');
        const canEnable = canEnableAttr !== 'false';
        if (desired && !canEnable) {
          window.alert('Complete the required provider settings before enabling.');
          target.checked = false;
          return;
        }
        const message = desired
          ? 'Enable this provider for LLM selection?'
          : 'Disable this provider? Active configurations using it may fail.';
        const confirmed = await confirmAction(
          message,
          {
            title: desired ? 'Enable provider' : 'Disable provider',
            confirmLabel: desired ? 'Enable' : 'Disable',
            cancelLabel: 'Cancel',
            destructive: !desired,
          },
          target,
        );
        if (!confirmed) {
          target.checked = !desired;
          return;
        }
        const formToggle = row.querySelector('[data-provider-toggle-form]');
        if (!formToggle) return;
        const enabledField = formToggle.querySelector('input[name="enabled"]');
        if (enabledField) enabledField.value = desired ? '1' : '0';
        formToggle.submit();
      });
    });

    const initialPreference = currentProviderKey || select?.value || '';
    if (initialPreference) {
      fillForm(initialPreference, currentProviderUuid);
    } else if (providers.length) {
      const first = providers[0];
      const fallbackUuid = first?.uid ? String(first.uid) : '';
      fillForm(first.key, fallbackUuid);
    }
  }

  function setupStagePanel() {
    const panel = doc.querySelector('[data-config-panel]');
    if (!panel) return;

    panel.querySelectorAll('[data-config-delete]').forEach((form) => {
      form.addEventListener('submit', async (event) => {
        if (form.dataset.confirming === '1') return;
        event.preventDefault();
        const confirmed = await confirmAction(
          '',
          {
            title: 'Delete configuration',
            confirmLabel: 'Delete',
            cancelLabel: 'Cancel',
            destructive: true,
          },
          form,
        );
        if (!confirmed) return;
        form.dataset.confirming = '1';
        try {
          form.submit();
        } finally {
          delete form.dataset.confirming;
        }
      });
    });

    const stageData = parseJSONScript('organization-stage-data', []);
    const stageMap = stageData.reduce((acc, item) => {
      acc[item.key] = item;
      return acc;
    }, {});

    function filterModels(card) {
      const providerSelect = card.querySelector('select[name$="provider"]');
      const modelSelect = card.querySelector('[data-stage-model]');
      if (!modelSelect) return;
      const provider = providerSelect?.value || '';
      Array.from(modelSelect.options).forEach((option) => {
        const optProvider = option.getAttribute('data-provider');
        if (!provider || !optProvider || provider === optProvider) {
          option.hidden = false;
        } else {
          option.hidden = true;
          if (option.selected) option.selected = false;
        }
      });
    }

    panel.querySelectorAll('[data-stage-card]').forEach((card) => {
      const providerSelect = card.querySelector('select[name$="provider"]');
      if (providerSelect) {
        providerSelect.addEventListener('change', () => filterModels(card));
      }
      filterModels(card);
    });

    const form = panel.querySelector('[data-config-form]');
    const newButton = panel.querySelector('[data-config-new]');
    const configIdInput = form?.querySelector('[data-config-id-input]');
    const nameInput = form?.querySelector('input[name="name"]');
    const descriptionInput = form?.querySelector('textarea[name="description"]');
    const providerChainSelect = form?.querySelector('select[data-provider-chain]');

    function resetStageCard(card) {
      const key = card.getAttribute('data-stage-key');
      const defaults = stageMap[key] || {};
      const providerSelect = card.querySelector('select[name$="provider"]');
      const modelSelect = card.querySelector('[data-stage-model]');
      const fields = {
        [defaults.field_max_tokens]: defaults.selected_max_tokens,
        [defaults.field_temperature]: defaults.selected_temperature,
        [defaults.field_opt_azure_deployment]: defaults.selected_options?.azure_deployment,
        [defaults.field_opt_max_input_tokens]: defaults.selected_options?.max_input_tokens,
        [defaults.field_opt_max_chunk_chars]: defaults.selected_options?.max_chunk_chars,
        [defaults.field_opt_chunk_overlap_tokens]: defaults.selected_options?.chunk_overlap_tokens,
        [defaults.field_opt_max_prompt_chars]: defaults.selected_options?.max_prompt_chars,
        [defaults.field_opt_max_prompt_segments]: defaults.selected_options?.max_prompt_segments,
      };
      Object.entries(fields).forEach(([fieldName, value]) => {
        if (!fieldName) return;
        const input = card.querySelector(`input[name="${fieldName}"]`);
        if (input) input.value = value ?? '';
      });
      const optionsTextarea = defaults.field_options
        ? card.querySelector(`textarea[name="${defaults.field_options}"]`)
        : null;
      if (optionsTextarea) optionsTextarea.value = defaults.selected_options_json || '';
      if (providerSelect) providerSelect.value = defaults.selected_provider || '';
      if (modelSelect) {
        modelSelect.value = defaults.selected_model || '';
        filterModels(card);
      }
    }

    function resetStageCards() {
      panel.querySelectorAll('[data-stage-card]').forEach(resetStageCard);
    }

    newButton?.addEventListener('click', () => {
      if (configIdInput) configIdInput.value = '';
      if (nameInput) nameInput.value = '';
      if (descriptionInput) descriptionInput.value = '';
      if (providerChainSelect) {
        Array.from(providerChainSelect.options).forEach((opt) => (opt.selected = false));
      }
      resetStageCards();
      nameInput?.focus();
    });
  }

  function setupGuardianPanel() {
    const section = doc.querySelector('[data-guardian-settings]');
    if (!section) return;

    section.querySelectorAll('[data-guardian-delete]').forEach((form) => {
      form.addEventListener('submit', async (event) => {
        if (form.dataset.confirming === '1') return;
        event.preventDefault();
        const confirmed = await confirmAction(
          '',
          {
            title: 'Delete instruction',
            confirmLabel: 'Delete',
            cancelLabel: 'Cancel',
            destructive: true,
          },
          form,
        );
        if (!confirmed) return;
        form.dataset.confirming = '1';
        try {
          form.submit();
        } finally {
          delete form.dataset.confirming;
        }
      });
    });
  }

  function setupNavDropdowns() {
    const groups = doc.querySelectorAll('[data-nav-group]');
    groups.forEach((group) => {
      const trigger = group.querySelector('[data-nav-group-trigger]');
      const panel = group.querySelector('[data-nav-group-panel]');
      if (!trigger || !panel) return;

      const close = () => {
        group.dataset.open = 'false';
        panel.dataset.open = 'false';
      };
      const open = () => {
        // Close siblings
        doc.querySelectorAll('[data-nav-group][data-open="true"]').forEach((g) => {
          if (g !== group) {
            g.dataset.open = 'false';
            const p = g.querySelector('[data-nav-group-panel]');
            if (p) p.dataset.open = 'false';
          }
        });
        group.dataset.open = 'true';
        panel.dataset.open = 'true';
      };

      trigger.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        const isOpen = group.dataset.open === 'true' || panel.dataset.open === 'true';
        if (isOpen) {
          close();
        } else {
          open();
        }
      });

      // Do not auto-close on minor pointer gaps; rely on outside clicks below.

      // Keyboard accessibility
      trigger.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          const isOpen = group.dataset.open === 'true' || panel.dataset.open === 'true';
          if (isOpen) {
            close();
          } else {
            open();
          }
        }
        if (event.key === 'Escape') {
          close();
        }
      });
    });

    doc.addEventListener('click', (event) => {
      if (event.target.closest('[data-nav-group]')) return;
      doc.querySelectorAll('[data-nav-group-panel]').forEach((panel) => {
        panel.dataset.open = 'false';
      });
      doc.querySelectorAll('[data-nav-group]').forEach((g) => {
        g.dataset.open = 'false';
      });
    });
  }

  setupProviderPanel();
  setupStagePanel();
  setupGuardianPanel();
  setupNavDropdowns();
})();
