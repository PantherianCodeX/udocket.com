(function () {
  const doc = window.document;

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

  function createModelRow(template, data) {
    const clone = template.content.firstElementChild.cloneNode(true);
    const name = clone.querySelector('input[name="model_name"]');
    const label = clone.querySelector('input[name="model_label"]');
    const tier = clone.querySelector('input[name="model_cost_tier"]');
    const maxTokens = clone.querySelector('input[name="model_max_output_tokens"]');
    const ctxTokens = clone.querySelector('input[name="model_context_window_tokens"]');
    if (name && data?.name) name.value = data.name;
    if (label && data?.label) label.value = data.label;
    if (tier && data?.cost_tier) tier.value = data.cost_tier;
    if (maxTokens && data?.max_output_tokens != null) {
      maxTokens.value = data.max_output_tokens;
    }
    if (ctxTokens && data?.context_window_tokens != null) {
      ctxTokens.value = data.context_window_tokens;
    }
    const removeBtn = clone.querySelector('[data-provider-model-remove]');
    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        clone.remove();
      });
    }
    return clone;
  }

  function setupProviderPanel() {
    const panel = doc.querySelector('[data-provider-panel]');
    if (!panel) return;

    const providers = parseJSONScript('organization-provider-data', []);
    const catalog = parseJSONScript('organization-provider-catalog', {});
    const credentials = parseJSONScript('organization-provider-credentials', {});
    const selectedInitial = parseJSONScript('organization-provider-selected', '');

    const form = panel.querySelector('[data-provider-form]');
    const select = form?.querySelector('[data-provider-select]');
    const displayInput = form?.querySelector('[data-provider-display]');
    const endpointInput = form?.querySelector('[data-provider-endpoint]');
    const apiKeyInput = form?.querySelector('[data-provider-apikey]');
    const clearCheckbox = form?.querySelector('[data-provider-clear]');
    const enabledCheckbox = form?.querySelector('[data-provider-enabled]');
    const modelContainer = form?.querySelector('[data-provider-model-rows]');
    const template = form?.querySelector('[data-provider-model-template]');
    const addModelBtn = form?.querySelector('[data-provider-model-add]');
    const modelJsonOverride = form?.querySelector('[data-provider-model-json]');
    const metadataJson = form?.querySelector('[data-provider-metadata-json]');
    const compiledInput = form?.querySelector('[data-provider-models-compiled]');
    const resetBtn = form?.querySelector('[data-provider-reset]');

    const providerMap = providers.reduce((acc, item) => {
      acc[item.key] = item;
      return acc;
    }, {});
    let currentProviderKey = selectedInitial && providerMap[selectedInitial]
      ? selectedInitial
      : '';

    function clearModels() {
      if (!modelContainer) return;
      modelContainer.innerHTML = '';
    }

    function populateModels(list) {
      if (!modelContainer || !template) return;
      clearModels();
      (list || []).forEach((model) => {
        modelContainer.appendChild(createModelRow(template, model));
      });
    }

    function buildModelsPayload() {
      if (!modelContainer) return [];
      const rows = Array.from(modelContainer.querySelectorAll('[data-provider-model-row]'));
      return rows.map((row) => {
        const name = row.querySelector('input[name="model_name"]')?.value?.trim();
        if (!name) return null;
        const payload = {
          name,
          label: row.querySelector('input[name="model_label"]')?.value?.trim() || name,
          cost_tier: row.querySelector('input[name="model_cost_tier"]')?.value?.trim() || 'standard',
        };
        const maxTokens = row.querySelector('input[name="model_max_output_tokens"]')?.value?.trim();
        const ctxTokens = row.querySelector('input[name="model_context_window_tokens"]')?.value?.trim();
        if (maxTokens) {
          const parsed = Number(maxTokens);
          if (!Number.isNaN(parsed)) payload.max_output_tokens = parsed;
        }
        if (ctxTokens) {
          const parsed = Number(ctxTokens);
          if (!Number.isNaN(parsed)) payload.context_window_tokens = parsed;
        }
        return payload;
      }).filter(Boolean);
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
        })),
      };
    }

    function getCredential(key) {
      return credentials[key] || null;
    }

    function fillForm(key) {
      if (!form) return;
      const cred = getCredential(key);
      const catalogDefaults = resolveCatalog(key);
      const providerInfo = providerMap[key];

      if (select) select.value = key || '';
      if (displayInput) displayInput.value = cred?.display_name || catalogDefaults?.display_name || providerInfo?.label || key || '';
      if (endpointInput) endpointInput.value = cred?.endpoint || catalogDefaults?.endpoint || '';
      if (apiKeyInput) apiKeyInput.value = '';
      if (clearCheckbox) clearCheckbox.checked = false;
      if (enabledCheckbox) enabledCheckbox.checked = cred?.is_enabled ?? true;
      if (modelJsonOverride) modelJsonOverride.value = '';
      if (metadataJson) metadataJson.value = cred?.metadata ? JSON.stringify(cred.metadata, null, 2) : '';
      populateModels(cred?.models?.length ? cred.models : catalogDefaults?.models || []);
      if (compiledInput) compiledInput.value = '';
      currentProviderKey = key;
    }

    function resetForm() {
      fillForm(select?.value || '');
      if (displayInput) displayInput.value = '';
      if (endpointInput) endpointInput.value = '';
      if (apiKeyInput) apiKeyInput.value = '';
      if (clearCheckbox) clearCheckbox.checked = false;
      if (enabledCheckbox) enabledCheckbox.checked = true;
      if (modelJsonOverride) modelJsonOverride.value = '';
      if (metadataJson) metadataJson.value = '';
      clearModels();
      if (compiledInput) compiledInput.value = '';
      select && select.focus();
    }

    select?.addEventListener('change', () => {
      fillForm(select.value);
    });

    addModelBtn?.addEventListener('click', () => {
      if (!template || !modelContainer) return;
      modelContainer.appendChild(createModelRow(template, {}));
    });

    resetBtn?.addEventListener('click', (event) => {
      event.preventDefault();
      resetForm();
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

    panel.querySelectorAll('[data-provider-edit]').forEach((button) => {
      button.addEventListener('click', () => {
        const row = button.closest('[data-provider-row]');
        if (!row) return;
        const key = row.getAttribute('data-provider-key');
        fillForm(key || '');
        form?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });

    panel.querySelectorAll('[data-provider-toggle]').forEach((checkbox) => {
      checkbox.addEventListener('change', (event) => {
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
        const confirmed = window.confirm(message);
        if (!confirmed) {
          target.checked = !desired;
          return;
        }
        const form = row.querySelector('[data-provider-toggle-form]');
        if (!form) return;
        const enabledField = form.querySelector('input[name="enabled"]');
        if (enabledField) enabledField.value = desired ? '1' : '0';
        form.submit();
      });
    });

    if (providers.length) {
      const initialKey = currentProviderKey && providerMap[currentProviderKey]
        ? currentProviderKey
        : providers[0].key;
      fillForm(initialKey);
    }

    // no-op when no providers configured yet
  }

  function setupStagePanel() {
    const panel = doc.querySelector('[data-config-panel]');
    if (!panel) return;

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

  setupProviderPanel();
  setupStagePanel();
})();
