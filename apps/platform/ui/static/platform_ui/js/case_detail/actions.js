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
  let summaryPendingSelection = null;

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
    const advanced = container.querySelector('[data-llm-advanced]');
    if (!advanced) return;

    const target = container.dataset.llmTarget || 'summary';
    const llmDebug = !!platformUI.llmDebug;

    const readEmbeddedJSON = (key) => {
      try {
        const script = container.querySelector(`[data-llm-json="${key}"]`);
        if (!script) return null;
        const textContent = script.textContent || '';
        if (!textContent.trim()) return null;
        const parsed = JSON.parse(textContent);
        if (llmDebug) console.debug('[LLM] Parsed embedded JSON', key, parsed);
        return parsed;
      } catch (error) {
        if (llmDebug) console.warn('[LLM] Failed to parse embedded JSON', key, error);
        return null;
      }
    };

    let catalog = readEmbeddedJSON('catalog') || {};
    let credentials = readEmbeddedJSON('credentials') || {};
    const providerState = {
      catalog,
      credentials,
      debug: llmDebug,
    };

    const configSelect = container.querySelector('[data-llm-config-select]');
    const configNameInput = container.querySelector('[data-llm-config-name]');
    const configDescriptionInput = container.querySelector('[data-llm-config-description]');
    const configDefaultInput = container.querySelector('[data-llm-config-default]');
    const configCreateBtn = container.querySelector('[data-llm-config-create]');
    const configDuplicateBtn = container.querySelector('[data-llm-config-duplicate]');
    const configDeleteBtn = container.querySelector('[data-llm-config-delete]');
    const primarySelect = advanced.querySelector('[data-llm-provider-primary]');

    const deepClone = (value) => JSON.parse(JSON.stringify(value || {}));
    let tempIdCounter = 0;
    const assignClientId = (cfg) => {
      if (!cfg) return null;
      if (!cfg._client_id) {
        cfg._client_id = cfg.id || `temp-${Date.now()}-${tempIdCounter++}`;
      }
      return cfg._client_id;
    };

    let configurations = (readEmbeddedJSON('configurations') || []).map((cfg) => ({ ...cfg }));
    configurations.forEach(assignClientId);

    let activeConfiguration = readEmbeddedJSON('active-configuration');
    if (activeConfiguration) {
      const existing = configurations.find((cfg) => cfg.id && cfg.id === activeConfiguration.id);
      if (existing) {
        activeConfiguration = existing;
      } else {
        activeConfiguration = { ...activeConfiguration };
        assignClientId(activeConfiguration);
        configurations.push(activeConfiguration);
      }
    }
    if (!activeConfiguration) {
      activeConfiguration = configurations.find((cfg) => cfg.is_default) || configurations[0] || null;
    }
    if (!activeConfiguration) {
      activeConfiguration = {
        id: null,
        name: `${target.charAt(0).toUpperCase()}${target.slice(1)} configuration`,
        description: '',
        provider_chain: [],
        stage_map: {},
        is_default: configurations.length === 0,
      };
      assignClientId(activeConfiguration);
      configurations.push(activeConfiguration);
    }
    assignClientId(activeConfiguration);

    let stageMap = deepClone(readEmbeddedJSON('stage-map') || activeConfiguration.stage_map);
    let providerChain = Array.isArray(activeConfiguration.provider_chain)
      ? [...activeConfiguration.provider_chain]
      : [];

    const state = {
      get configs() {
        return configurations;
      },
      set configs(next) {
        configurations = next;
      },
      get activeConfig() {
        return activeConfiguration;
      },
      set activeConfig(next) {
        activeConfiguration = next;
        assignClientId(activeConfiguration);
      },
      get stageMap() {
        return stageMap;
      },
      set stageMap(next) {
        stageMap = next;
      },
      get providerChain() {
        return providerChain;
      },
      set providerChain(next) {
        providerChain = next;
      },
      target,
      providerState,
    };

    const stageMapDataset = () => {
      if (stageMap && Object.keys(stageMap).length) {
        container.dataset.llmStageMap = JSON.stringify(stageMap);
      } else {
        delete container.dataset.llmStageMap;
      }
    };

    const providerChainDataset = () => {
      if (providerChain.length) {
        container.dataset.llmProviderChain = JSON.stringify(providerChain);
      } else {
        delete container.dataset.llmProviderChain;
      }
    };

    const configIdDataset = () => {
      if (activeConfiguration && activeConfiguration.id) {
        container.dataset.llmConfigId = activeConfiguration.id;
      } else {
        delete container.dataset.llmConfigId;
      }
    };

    const refreshDatasets = () => {
      stageMapDataset();
      providerChainDataset();
      configIdDataset();
    };

    const refreshPrimarySelect = () => {
      if (!primarySelect) return;
      const currentPrimary = providerChain.length ? providerChain[0] : '';
      let matched = false;
      Array.from(primarySelect.options).forEach((option) => {
        if (option.value === currentPrimary) {
          option.selected = true;
          matched = true;
        }
      });
      if (!matched) {
        const firstEnabled = Array.from(primarySelect.options).find((option) => !option.disabled);
        if (firstEnabled) {
          firstEnabled.selected = true;
        }
      }
      const selected = primarySelect.value;
      if (selected) {
        providerChain = providerChain.filter((value) => value !== selected);
        providerChain.unshift(selected);
      }
      providerChainDataset();
    };

    const refreshConfigInputs = () => {
      if (configNameInput) configNameInput.value = activeConfiguration.name || '';
      if (configDescriptionInput) configDescriptionInput.value = activeConfiguration.description || '';
      if (configDefaultInput) configDefaultInput.checked = !!activeConfiguration.is_default;
    };

    const renderConfigSelect = () => {
      if (!configSelect) return;
      configSelect.innerHTML = '';
      configurations.forEach((cfg) => {
        const option = global.document.createElement('option');
        option.value = assignClientId(cfg);
        option.textContent = cfg.name || '(Untitled configuration)';
        if (cfg.is_default) option.textContent += ' · Default';
        if (cfg._client_id === activeConfiguration._client_id) option.selected = true;
        configSelect.appendChild(option);
      });
      if (configSelect.options.length && configSelect.selectedIndex === -1) {
        configSelect.selectedIndex = 0;
      }
    };

    const syncButtons = () => {
      if (configDuplicateBtn) configDuplicateBtn.disabled = configurations.length === 0;
      if (configDeleteBtn) configDeleteBtn.disabled = !activeConfiguration.id;
    };

    const applyActiveConfiguration = (config) => {
      state.activeConfig = config;
      stageMap = deepClone(config.stage_map);
      providerChain = Array.isArray(config.provider_chain) ? [...config.provider_chain] : [];
      refreshConfigInputs();
      refreshPrimarySelect();
      renderConfigSelect();
      refreshDatasets();
      syncButtons();
      if (llmDebug) {
        console.debug('[LLM] Active LLM configuration', {
          target,
          id: config.id,
          name: config.name,
          provider_chain: providerChain,
        });
      }
    };

    renderConfigSelect();
    refreshConfigInputs();
    refreshPrimarySelect();
    refreshDatasets();
    syncButtons();

    if (configSelect) {
      configSelect.addEventListener('change', () => {
        const selectedId = configSelect.value;
        const next = configurations.find((cfg) => cfg._client_id === selectedId);
        if (next) {
          applyActiveConfiguration(next);
        }
      });
    }

    if (configNameInput) {
      configNameInput.addEventListener('input', () => {
        activeConfiguration.name = configNameInput.value.trim();
        renderConfigSelect();
      });
    }

    if (configDescriptionInput) {
      configDescriptionInput.addEventListener('input', () => {
        activeConfiguration.description = configDescriptionInput.value;
      });
    }

    if (configDefaultInput) {
      configDefaultInput.addEventListener('change', () => {
        activeConfiguration.is_default = configDefaultInput.checked;
      });
    }

    if (primarySelect) {
      primarySelect.addEventListener('change', () => {
        const value = primarySelect.value;
        providerChain = providerChain.filter((item) => item !== value);
        if (value) {
          providerChain.unshift(value);
        }
        providerChainDataset();
      });
    }

    const createEmptyConfiguration = (label) => {
      const cfg = {
        id: null,
        name: label || `New ${target} configuration`,
        description: '',
        provider_chain: [],
        stage_map: {},
        is_default: configurations.length === 0,
      };
      assignClientId(cfg);
      return cfg;
    };

    if (configCreateBtn) {
      configCreateBtn.addEventListener('click', () => {
        const cfg = createEmptyConfiguration();
        configurations = [...configurations, cfg];
        applyActiveConfiguration(cfg);
        if (configNameInput) {
          configNameInput.focus();
          configNameInput.select();
        }
      });
    }

    if (configDuplicateBtn) {
      configDuplicateBtn.addEventListener('click', () => {
        const clone = {
          id: null,
          name: `${activeConfiguration.name || 'Untitled'} copy`,
          description: activeConfiguration.description || '',
          provider_chain: [...providerChain],
          stage_map: deepClone(stageMap),
          is_default: false,
        };
        assignClientId(clone);
        configurations = [...configurations, clone];
        applyActiveConfiguration(clone);
        if (configNameInput) {
          configNameInput.focus();
          configNameInput.select();
        }
      });
    }

    const updateStateFromResponse = (payload) => {
      configurations = (payload.configurations || []).map((cfg) => ({ ...cfg }));
      configurations.forEach(assignClientId);
      let nextActive = null;
      if (payload.active) {
        nextActive = configurations.find((cfg) => cfg.id === payload.active.id);
        if (!nextActive) {
          nextActive = { ...payload.active };
          assignClientId(nextActive);
          configurations.push(nextActive);
        }
      }
      if (!nextActive) {
        nextActive = configurations.find((cfg) => cfg.is_default) || configurations[0] || createEmptyConfiguration();
      }
      applyActiveConfiguration(nextActive);
    };

    const persistConfiguration = async (request) => {
      if (!ctx?.caseId) return null;
      const payload = {
        target,
        action: request.action || 'upsert',
      };
      if (payload.action === 'delete') {
        payload.config_id = request.configId;
      } else {
        payload.configuration = request.configuration;
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
          body: JSON.stringify(payload),
        });
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || `HTTP ${resp.status}`);
        }
        const data = await resp.json();
        updateStateFromResponse(data);
        return data;
      } catch (error) {
        console.warn('[LLM] Persist configuration failed', error);
        caseDetail.modals?.message?.({
          heading: 'Save failed',
          body: error.message || 'Unable to update configuration.',
          container: ctx?.modalRoot || undefined,
        });
        return null;
      }
    };

    if (configDeleteBtn) {
      configDeleteBtn.addEventListener('click', async () => {
        if (!activeConfiguration.id) {
          configurations = configurations.filter((cfg) => cfg !== activeConfiguration);
          const replacement = configurations[0] || createEmptyConfiguration();
          if (!configurations.length) {
            configurations = [replacement];
          }
          applyActiveConfiguration(replacement);
          renderConfigSelect();
          syncButtons();
          return;
        }
        const confirmed = await deps.modals?.confirm?.({
          heading: 'Delete LLM configuration',
          body: 'This configuration will be removed for the organization. Continue?',
          confirmLabel: 'Delete',
          cancelLabel: 'Cancel',
          destructive: true,
          container: ctx?.modalRoot || undefined,
        });
        if (confirmed === false) return;
        await persistConfiguration({ action: 'delete', configId: activeConfiguration.id });
        renderConfigSelect();
        syncButtons();
        caseDetail.modals?.message?.({
          heading: 'Configuration deleted',
          body: 'The LLM configuration was removed.',
          container: ctx?.modalRoot || undefined,
        });
      });
    }

    const ensureModelRow = (modalEl) => {
      const modelContainer = modalEl.querySelector('[data-llm-models]');
      const templateModel = modalEl.querySelector('[data-llm-model-row-template]');
      if (!modelContainer || !templateModel) return;
      if (!modelContainer.children.length) {
        modelContainer.appendChild(renderModelRow(templateModel));
      }
    };

    function renderModelRow(template, model = {}) {
      const clone = template.content.firstElementChild.cloneNode(true);
      const nameInput = clone.querySelector('[data-llm-model-name]');
      const labelInput = clone.querySelector('[data-llm-model-label]');
      const costInput = clone.querySelector('[data-llm-model-cost]');
      const maxInput = clone.querySelector('[data-llm-model-max]');
      if (nameInput) nameInput.value = model.name || '';
      if (labelInput) labelInput.value = model.label || '';
      if (costInput) costInput.value = model.cost_tier || '';
      if (maxInput) maxInput.value = model.max_output_tokens != null ? model.max_output_tokens : '';
      const removeBtn = clone.querySelector('[data-llm-model-remove]');
      if (removeBtn) {
        removeBtn.addEventListener('click', (evt) => {
          evt.preventDefault();
          clone.remove();
        });
      }
      return clone;
    }

    function renderProviderList(modalEl, stateRef) {
      const list = modalEl.querySelector('[data-llm-provider-list]');
      const empty = modalEl.querySelector('[data-llm-provider-empty]');
      if (!list) return;
      list.innerHTML = '';
      const template = modalEl.querySelector('[data-llm-provider-card-template]');
      const entries = new Map();
      Object.entries(stateRef.catalog || {}).forEach(([key, info]) => {
        entries.set(key, { key, catalog: info, credential: stateRef.credentials[key] || null });
      });
      Object.entries(stateRef.credentials || {}).forEach(([key, credential]) => {
        if (!entries.has(key)) {
          entries.set(key, { key, catalog: null, credential });
        }
      });
      if (stateRef.debug) {
        console.debug('[LLM] Render provider list', { entries: Array.from(entries.keys()) });
      }
      if (!entries.size) {
        if (empty) empty.classList.remove('hidden');
        return;
      }
      if (empty) empty.classList.add('hidden');
      entries.forEach((entry) => {
        if (!template) return;
        const card = template.content.firstElementChild.cloneNode(true);
        card.setAttribute('data-llm-provider-card', entry.key);
        const titleEl = card.querySelector('[data-llm-provider-card-title]');
        const descEl = card.querySelector('[data-llm-provider-card-description]');
        const endpointEl = card.querySelector('[data-llm-provider-card-endpoint]');
        const statusEl = card.querySelector('[data-llm-provider-card-status]');
        const catalogInfo = entry.catalog || {};
        const credentialInfo = entry.credential || {};
        if (titleEl) titleEl.textContent = catalogInfo.display_name || credentialInfo.display_name || entry.key;
        if (descEl) descEl.textContent = catalogInfo.description || credentialInfo.description || '';
        if (endpointEl) endpointEl.textContent = credentialInfo.endpoint || catalogInfo.default_endpoint || '';
        if (statusEl) {
          statusEl.textContent = credentialInfo.endpoint || credentialInfo.models ? 'Configured' : 'Not configured';
        }
        card.addEventListener('click', () => openProviderForm(modalEl, stateRef, entry.key));
        list.appendChild(card);
      });
    }

    function openProviderForm(modalEl, stateRef, providerKey) {
      const wrapper = modalEl.querySelector('[data-llm-provider-form-wrapper]');
      const form = modalEl.querySelector('[data-llm-provider-form]');
      if (!wrapper || !form) return;
      const catalogInfo = stateRef.catalog[providerKey] || {};
      const credentialInfo = stateRef.credentials[providerKey] || {};
      wrapper.classList.remove('hidden');
      wrapper.dataset.activeProvider = providerKey;
      const titleEl = wrapper.querySelector('[data-llm-provider-form-title]');
      const subtitleEl = wrapper.querySelector('[data-llm-provider-form-subtitle]');
      const keyInput = wrapper.querySelector('[data-llm-provider-key]');
      const hiddenInput = wrapper.querySelector('[data-llm-provider-input]');
      const nameInput = wrapper.querySelector('[data-llm-provider-name]');
      const endpointInput = wrapper.querySelector('[data-llm-provider-endpoint]');
      const apiKeyInput = wrapper.querySelector('[data-llm-provider-apikey]');
      const deleteBtn = wrapper.querySelector('[data-llm-provider-delete]');
      const modelsContainer = wrapper.querySelector('[data-llm-models]');
      const templateModel = wrapper.querySelector('[data-llm-model-row-template]');
      if (titleEl) titleEl.textContent = `Configure ${catalogInfo.display_name || credentialInfo.display_name || providerKey}`;
      if (subtitleEl) {
        const requiresKey = catalogInfo.requires_api_key !== false;
        subtitleEl.textContent = requiresKey ? 'Enter API credentials and adjust models.' : 'No API key required for this provider.';
      }
      if (keyInput) keyInput.value = providerKey;
      if (hiddenInput) hiddenInput.value = providerKey;
      if (nameInput) nameInput.value = credentialInfo.display_name || catalogInfo.display_name || catalogInfo.label || providerKey;
      if (endpointInput) endpointInput.value = credentialInfo.endpoint || catalogInfo.default_endpoint || '';
      if (apiKeyInput) apiKeyInput.value = '';
      if (deleteBtn) {
        if (stateRef.credentials[providerKey]) {
          deleteBtn.classList.remove('hidden');
          deleteBtn.disabled = false;
        } else {
          deleteBtn.classList.add('hidden');
        }
      }
      if (modelsContainer && templateModel) {
        modelsContainer.innerHTML = '';
        const models = (credentialInfo.models && credentialInfo.models.length ? credentialInfo.models : catalogInfo.models) || [];
        if (models.length) {
          models.forEach((model) => {
            modelsContainer.appendChild(renderModelRow(templateModel, model));
          });
        }
      }
      if (stateRef.debug) {
        console.debug('[LLM] Open provider form', { provider: providerKey, configured: Boolean(stateRef.credentials[providerKey]) });
      }
      ensureModelRow(modalEl);
    }

    function closeProviderForm(modalEl) {
      const wrapper = modalEl.querySelector('[data-llm-provider-form-wrapper]');
      if (wrapper) {
        wrapper.classList.add('hidden');
        wrapper.dataset.activeProvider = '';
      }
    }

    function addCustomProvider(modalEl, stateRef) {
      const key = global.prompt('Enter a provider key (letters, numbers, hyphen, underscore):', 'custom');
      if (!key) return;
      const normalized = key.trim().toLowerCase();
      if (!/^[a-z0-9_-]+$/.test(normalized)) {
        global.alert('Provider key must contain only letters, numbers, hyphen, or underscore.');
        return;
      }
      if (!stateRef.catalog[normalized]) {
        stateRef.catalog[normalized] = {
          display_name: normalized,
          description: 'Custom provider',
          requires_api_key: true,
        };
      }
      if (!stateRef.credentials[normalized]) {
        stateRef.credentials[normalized] = {};
      }
      renderProviderList(modalEl, stateRef);
      openProviderForm(modalEl, stateRef, normalized);
    }

    const buildStageMapFromForm = (stageRows, existingMap) => {
      const map = {};
      stageRows.forEach((row) => {
        const key = row.getAttribute('data-stage-key');
        if (!key) return;
        const providerSelectEl = row.querySelector('[data-llm-provider]');
        const modelSelectEl = row.querySelector('[data-llm-model]');
        if (!providerSelectEl) return;
        const entry = {};
        if (providerSelectEl.value) entry.provider = providerSelectEl.value;
        if (modelSelectEl && modelSelectEl.value) entry.model = modelSelectEl.value;
        const previous = existingMap[key];
        if (previous && previous.options && typeof previous.options === 'object') {
          entry.options = previous.options;
        }
        map[key] = entry;
      });
      return map;
    };

    function attachProviderModalHandlers(modalEl) {
      if (!modalEl) return;
      const panelButtons = Array.from(modalEl.querySelectorAll('[data-llm-panel-toggle]'));
      const panels = panelButtons.reduce((acc, btn) => {
        const key = btn.getAttribute('data-llm-panel-toggle');
        if (key) {
          acc[key] = modalEl.querySelector(`[data-llm-panel="${key}"]`);
        }
        return acc;
      }, {});

      function activatePanel(name) {
        panelButtons.forEach((btn) => {
          const isActive = btn.getAttribute('data-llm-panel-toggle') === name;
          btn.classList.toggle('bg-primary-500/80', isActive);
          btn.classList.toggle('shadow-primary-500/40', isActive);
          btn.classList.toggle('border-white/15', !isActive);
          btn.classList.toggle('text-white', isActive);
        });
        Object.entries(panels).forEach(([key, panel]) => {
          if (!panel) return;
          const show = key === name;
          panel.classList.toggle('hidden', !show);
          panel.hidden = !show;
          if (show) {
            panel.removeAttribute('aria-hidden');
          } else {
            panel.setAttribute('aria-hidden', 'true');
          }
        });
      }

      panelButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
          const key = btn.getAttribute('data-llm-panel-toggle');
          if (key) activatePanel(key);
        });
      });
      activatePanel('stages');

      const providerListContainer = modalEl.querySelector('[data-llm-provider-list]');
      const addProviderBtn = modalEl.querySelector('[data-llm-provider-add]');
      const refreshBtn = modalEl.querySelector('[data-llm-provider-refresh]');
      const cancelButtons = modalEl.querySelectorAll('[data-llm-provider-cancel]');
      const deleteBtn = modalEl.querySelector('[data-llm-provider-delete]');
      const providerForm = modalEl.querySelector('[data-llm-provider-form]');

      renderProviderList(modalEl, providerState);

      if (addProviderBtn) {
        addProviderBtn.addEventListener('click', (evt) => {
          evt.preventDefault();
          addCustomProvider(modalEl, providerState);
        });
      }

      if (refreshBtn) {
        refreshBtn.addEventListener('click', (evt) => {
          evt.preventDefault();
          renderProviderList(modalEl, providerState);
        });
      }

      cancelButtons.forEach((btn) => {
        btn.addEventListener('click', (evt) => {
          evt.preventDefault();
          closeProviderForm(modalEl);
        });
      });

      if (deleteBtn) {
        deleteBtn.addEventListener('click', async (evt) => {
          evt.preventDefault();
          const providerKey = modalEl.querySelector('[data-llm-provider-key]')?.value;
          if (!providerKey) return;
          const confirmed = await deps.modals?.confirm?.({
            heading: 'Remove provider credentials',
            body: 'This will remove saved credentials for the provider. Continue?',
            confirmLabel: 'Remove',
            cancelLabel: 'Cancel',
            destructive: true,
            container: ctx?.modalRoot || undefined,
          });
          if (confirmed === false) return;
          try {
            const resp = await fetch(`/cases/${ctx.caseId}/llm/providers/${providerKey}/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': helpers.getCSRFToken(),
                Accept: 'application/json',
              },
              credentials: 'same-origin',
            });
            if (!resp.ok) {
              const text = await resp.text();
              throw new Error(text || `HTTP ${resp.status}`);
            }
            const data = await resp.json();
            providerState.credentials = data.credentials || providerState.credentials;
            renderProviderList(modalEl, providerState);
            closeProviderForm(modalEl);
          } catch (error) {
            console.warn('Unable to delete provider credential', providerKey, error);
          }
        });
      }

      if (providerForm) {
        providerForm.addEventListener('submit', async (evt) => {
          evt.preventDefault();
          const formData = new global.FormData(providerForm);
          const providerKey = formData.get('provider');
          if (!providerKey) return;
          const payload = {
            provider: providerKey,
            display_name: formData.get('display_name') || providerKey,
            endpoint: formData.get('endpoint') || '',
            models: [],
          };
          const apiKeyValue = formData.get('api_key');
          if (typeof apiKeyValue === 'string') {
            payload.api_key = apiKeyValue;
          }
          const modelsContainer = providerForm.querySelector('[data-llm-models]');
          if (modelsContainer) {
            Array.from(modelsContainer.querySelectorAll('[data-llm-model-row]')).forEach((row) => {
              const nameInput = row.querySelector('[data-llm-model-name]');
              const labelInput = row.querySelector('[data-llm-model-label]');
              const costInput = row.querySelector('[data-llm-model-cost]');
              const maxInput = row.querySelector('[data-llm-model-max]');
              const entry = {};
              if (nameInput?.value) entry.name = nameInput.value.trim();
              if (labelInput?.value) entry.label = labelInput.value.trim();
              if (costInput?.value) entry.cost_tier = costInput.value.trim();
              if (maxInput?.value) {
                const parsed = Number(maxInput.value.trim());
                if (!Number.isNaN(parsed)) entry.max_output_tokens = parsed;
              }
              if (entry.name) payload.models.push(entry);
            });
          }
          try {
            const resp = await fetch(`/cases/${ctx.caseId}/llm/providers/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': helpers.getCSRFToken(),
                Accept: 'application/json',
              },
              credentials: 'same-origin',
              body: JSON.stringify(payload),
            });
            if (!resp.ok) {
              const text = await resp.text();
              throw new Error(text || `HTTP ${resp.status}`);
            }
            const data = await resp.json();
            providerState.credentials = data.credentials || providerState.credentials;
            renderProviderList(modalEl, providerState);
            openProviderForm(modalEl, providerState, providerKey);
            caseDetail.modals?.message?.({
              heading: 'Provider saved',
              body: payload.display_name,
              container: ctx?.modalRoot || undefined,
            });
          } catch (error) {
            console.warn('Unable to save provider', providerKey, error);
          }
        });
      }

      const stageForm = modalEl.querySelector('[data-llm-form]');
      if (!stageForm) return;
      const saveButton = stageForm.querySelector('[data-llm-save]');
      const stageRows = Array.from(stageForm.querySelectorAll('[data-llm-stage]'));
      const activeStageMap = deepClone(stageMap);
      stageRows.forEach((row) => {
        const stageKey = row.getAttribute('data-stage-key');
        const entry = activeStageMap[stageKey] || {};
        const providerSelectEl = row.querySelector('[data-llm-provider]');
        const modelSelectEl = row.querySelector('[data-llm-model]');
        if (providerSelectEl && entry.provider) {
          providerSelectEl.value = entry.provider;
        }
        updateModelOptions(row);
        if (modelSelectEl && entry.model) {
          modelSelectEl.value = entry.model;
        }
        if (providerSelectEl) {
          providerSelectEl.addEventListener('change', () => updateModelOptions(row));
        }
        updateModelOptions(row);
      });

      stageForm.addEventListener('submit', async (evt) => {
        evt.preventDefault();
        if (saveButton) {
          saveButton.disabled = true;
          saveButton.textContent = 'Saving…';
        }
        const updatedStageMap = buildStageMapFromForm(stageRows, stageMap);
        stageMap = updatedStageMap;
        const chainSet = new Set();
        if (primarySelect?.value) chainSet.add(primarySelect.value);
        Object.values(stageMap).forEach((entry) => {
          if (entry && entry.provider) chainSet.add(entry.provider);
        });
        providerChain = Array.from(chainSet);
        refreshDatasets();

        const configurationPayload = {
          id: activeConfiguration.id || null,
          name: configNameInput?.value.trim() || activeConfiguration.name || `${target} configuration`,
          description: configDescriptionInput?.value || '',
          provider_chain: providerChain,
          stage_map: stageMap,
          set_default: configDefaultInput?.checked || false,
        };

        activeConfiguration.name = configurationPayload.name;
        activeConfiguration.description = configurationPayload.description;
        activeConfiguration.provider_chain = [...providerChain];
        activeConfiguration.stage_map = deepClone(stageMap);
        activeConfiguration.is_default = configurationPayload.set_default;

        const result = await persistConfiguration({ action: 'upsert', configuration: configurationPayload });
        if (result && saveButton) {
          caseDetail.modals?.message?.({
            heading: 'Configuration saved',
            body: 'LLM configuration updated successfully.',
            container: ctx?.modalRoot || undefined,
          });
        }
        if (saveButton) {
          saveButton.disabled = false;
          saveButton.textContent = 'Save';
        }
        const closeButton = modalEl.querySelector('[data-modal-close]');
        if (closeButton) closeButton.click();
      });
    }

    container.llmProviderState = providerState;
    container.llmInitModal = (modalEl) => attachProviderModalHandlers(modalEl);
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

  function setSummaryPendingSelection(jobId) {
    if (!jobId) return;
    summaryPendingSelection = jobId;
  }

  function resolveSummaryPendingSelection() {
    const value = summaryPendingSelection;
    summaryPendingSelection = null;
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
    const container = modal.querySelector('[data-summary-text-modal]');
    if (!container) return;
    const endpoint = container.getAttribute('data-summary-text-endpoint');
    if (!endpoint) return;
    const statusEl = container.querySelector('[data-summary-text-status]');
    const uploadButton = container.querySelector('[data-summary-text-upload-button]');
    const uploadForm = container.querySelector('[data-summary-text-upload-form]');
    const fileInput = container.querySelector('[data-summary-text-file]');

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
      setSummaryPendingSelection(data.job_id);
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
      const name = button.getAttribute('data-summary-text-fixture');
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

    container.querySelectorAll('[data-summary-text-fixture]').forEach((button) => {
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
    if (platformUI.llmDebug) {
      console.debug('[LLM] setupAnalysisActions', {
        hasSummary: Boolean(root.querySelector('[data-summary]')),
        hasTimeline: Boolean(root.querySelector('[data-timeline]')),
      });
    }
    const summaryContainer = root.querySelector('[data-summary]');
    if (summaryContainer) {
      setupLLMControls(summaryContainer);
      const select = summaryContainer.querySelector('[data-summary-source]');
      const button = summaryContainer.querySelector('[data-analysis-action="summary"]');

      const uploadAttr = 'data-summary-upload-option';
      const uploadTextAttr = 'data-summary-upload-text-option';
      const specialAttrs = [uploadAttr, uploadTextAttr];
      const findFirstRunnableOption = () => {
        if (!select) return null;
        return (
          Array.from(select.options).find(
            (option) => !option.disabled && !specialAttrs.some((attr) => option.hasAttribute(attr)),
          ) || null
        );
      };

      let lastValidValue = null;
      if (select) {
        const current = select.selectedOptions[0];
        if (current && !current.disabled && !specialAttrs.some((attr) => current.hasAttribute(attr))) {
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
        const isSpecial = specialAttrs.some((attr) => selected.hasAttribute(attr));
        const isDisabled = selected.disabled || selected.hasAttribute('disabled');
        button.disabled = isSpecial || isDisabled;
      };

      if (select) {
        select.addEventListener('change', (evt) => {
          const selected = select.selectedOptions[0];
          if (!selected) {
            updateDisabled();
            return;
          }
          const isUpload = selected.hasAttribute(uploadAttr);
          const isUploadText = selected.hasAttribute(uploadTextAttr);
          if (isUpload || isUploadText) {
            evt.preventDefault();
            if (isUpload) {
              openTranscriptUpload();
            } else {
              openSummaryTextUpload(select);
            }
            if (lastValidValue) {
              select.value = lastValidValue;
            } else {
              const firstRunnable = findFirstRunnableOption()
                || Array.from(select.options).find(
                  (option) => !specialAttrs.some((attr) => option.hasAttribute(attr)),
                );
              if (firstRunnable) {
                select.value = firstRunnable.value;
                if (!firstRunnable.disabled && !specialAttrs.some((attr) => firstRunnable.hasAttribute(attr))) {
                  lastValidValue = firstRunnable.value;
                }
              } else {
                select.selectedIndex = -1;
              }
            }
            updateDisabled();
            return;
          }
          const isSpecial = specialAttrs.some((attr) => selected.hasAttribute(attr));
          if (!selected.disabled && !isSpecial) {
            lastValidValue = selected.value;
          }
          const pending = resolveSummaryPendingSelection();
          if (pending) {
            select.value = pending;
            lastValidValue = pending;
          }
          updateDisabled();
        });
        const pending = resolveSummaryPendingSelection();
        if (pending) {
          const option = Array.from(select.options).find((opt) => opt.value === pending);
          if (option && !option.disabled) {
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

      const configId = summaryContainer?.dataset.llmConfigId || null;
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
