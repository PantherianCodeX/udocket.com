(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  const JSONU = platformUI.json;

  if (typeof caseDetail.init === 'function' && caseDetail.controller) {
    return;
  }

  const helpers = caseDetail.helpers || {};
  const uiModule = caseDetail.ui || {};
  const realtimeModule = caseDetail.realtime || {};
  const modalsModule = caseDetail.modals || {};
  const actionsModule = caseDetail.actions || {};

  function debugEnabled() {
    try {
      if (global.platformUI && global.platformUI.debug) return true;
      return localStorage.getItem('platformUI.debug') === '1';
    } catch (_) {
      return false;
    }
  }
  function dbg(tag, data) {
    if (!debugEnabled()) return;
    try {
      // eslint-disable-next-line no-console
      console.debug('[caseDetail]', tag, data || '');
    } catch (_) {}
  }

  function createContext(options = {}) {
    const caseView = options.root || global.document.querySelector('[data-case-view]');
    if (!caseView) {
      return null;
    }
    const caseId = options.caseId || caseView.getAttribute('data-case-id');
    const initialToolKey = options.initialToolKey || caseView.getAttribute('data-initial-tool') || '';
    const workspace = options.workspace || caseView.querySelector('#tool-workspace');
    const modalRoot = options.modalRoot || global.document.getElementById('modal-root');

    const jobsState =
      caseDetail.state ||
      global.JobsState || {
        currentCaseId: caseId,
        pollers: {},
        sockets: {},
        lastStatus: {},
        refreshTranscribeScheduled: false,
        fallbackJobs: new Set(),
        fallbackTimer: null,
        connectTimeouts: {},
      };
    jobsState.currentCaseId = caseId;
    if (!(jobsState.fallbackJobs instanceof Set)) {
      const existing = Array.isArray(jobsState.fallbackJobs)
        ? jobsState.fallbackJobs
        : [];
      jobsState.fallbackJobs = new Set(existing);
    }
    jobsState.connectTimeouts = jobsState.connectTimeouts || {};
    jobsState.pollers = jobsState.pollers || {};
    jobsState.sockets = jobsState.sockets || {};
    jobsState.lastStatus = jobsState.lastStatus || {};
    global.JobsState = jobsState;

    const ctx = {
      global,
      caseView,
      caseId,
      initialToolKey,
      workspace,
      modalRoot,
      jobsState,
      jobsTableApi: platformUI.jobsTable,
      statusUtils: platformUI.status || {},
      jobActions: platformUI.jobActions || {},
      modalApi: platformUI.modal || {},
      toastAt: typeof platformUI.toastAt === 'function' ? platformUI.toastAt : null,
      toast: typeof platformUI.toast === 'function' ? platformUI.toast : null,
    };

    caseDetail.state = jobsState;
    return ctx;
  }

  function ensureMessageStack() {
    let stack = global.document.getElementById('platform-ui-message-stack');
    if (!stack) {
      stack = global.document.createElement('div');
      stack.id = 'platform-ui-message-stack';
      stack.className = 'pointer-events-none fixed inset-x-0 top-4 z-50 flex flex-col items-center gap-2 px-4 sm:items-end sm:px-8';
      global.document.body.appendChild(stack);
    }
    return stack;
  }

  function renderMessage(options) {
    const stack = ensureMessageStack();
    const variant = options.type || 'info';
    const message = options.message || '';
    const action = options.action || null;
    const card = global.document.createElement('div');
    const variantClass =
      variant === 'error'
        ? 'border-rose-400/40 bg-rose-950/90 text-rose-100'
        : 'border-white/20 bg-slate-900/90 text-slate-100';
    card.className = `pointer-events-auto relative w-full max-w-md rounded-xl border px-4 py-3 shadow-xl shadow-black/40 backdrop-blur ${variantClass}`;

    const messageEl = global.document.createElement('p');
    messageEl.className = 'pr-8 text-sm leading-relaxed';
    messageEl.textContent = message || 'An unexpected error occurred.';
    card.appendChild(messageEl);

    if (action && action.href) {
      const actionBtn = global.document.createElement('a');
      actionBtn.href = action.href;
      actionBtn.className = 'mt-3 inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-semibold text-white transition hover:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-400/60';
      actionBtn.textContent = action.label || 'Review configuration';
      if (action.target) actionBtn.target = action.target;
      card.appendChild(actionBtn);
    }

    const closeBtn = global.document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'absolute right-2 top-2 rounded-full p-1 text-xs text-white/70 transition hover:text-white focus:outline-none focus:ring-2 focus:ring-white/40';
    closeBtn.innerHTML = '<span aria-hidden="true">×</span><span class="sr-only">Dismiss</span>';
    closeBtn.addEventListener('click', () => {
      card.remove();
    });
    card.appendChild(closeBtn);

    stack.appendChild(card);

    if (variant !== 'error') {
      global.setTimeout(() => {
        card.classList.add('opacity-0');
        card.style.transition = 'opacity 150ms ease-in-out';
        global.setTimeout(() => {
          card.remove();
        }, 180);
      }, options.timeout || 3000);
    }
  }

  function createNotifier(ctx) {
    const toastAt = ctx.toastAt;
    const toast = ctx.toast;
    return function notify(x, y, text) {
      if (arguments.length === 1 && typeof x === 'object' && x !== null && !Array.isArray(x)) {
        renderMessage({
          type: x.type || 'info',
          message: x.message || '',
          action: x.action || null,
          timeout: x.timeout,
        });
        return;
      }
      if (toastAt) {
        toastAt(x, y, text);
      } else if (toast) {
        toast(text);
      }
    };
  }

  function bindGlobalEvents(controller) {
    if (caseDetail._listenersBound) return;

    const { actions, ui } = controller;

    const handlers = {
      // Row click/key handlers are owned by platformUI.jobsTable; avoid double toggles here.
      jobAction: (evt) => actions.handleJobAction(evt),
      jobNotesSave: (evt) => actions.handleJobNotesSave(evt),
      verifyHash: (evt) => actions.handleVerifyHash(evt),
      audioRefresh: (evt) => actions.handleAudioRefresh(evt),
      transcriptAction: (evt) => actions.handleTranscriptAction(evt),
      jobLink: (evt) => actions.handleJobLinkClick(evt),
      jobLog: (evt) => actions.handleJobViewLog(evt),
      analysisAction: (evt) => actions.handleAnalysisAction(evt),
      toolCardBefore: (evt) => {
        const src = (evt.detail && evt.detail.elt) || evt.target;
        const button = src && src.closest ? src.closest('[data-tool-card]') : null;
        if (!button) return;
        global.document.querySelectorAll('[data-tool-card]').forEach((el) => {
          el.classList.remove('ring-1', 'ring-primary-400/60');
        });
        const key = button.getAttribute('data-tool-card');
        ui.setActiveCard(key);
        button.classList.add('ring-1', 'ring-primary-400/60');
        button.setAttribute('data-tool-card-active', 'true');
        dbg('toolCardBefore', {
          key,
          hxGet: button.getAttribute('hx-get'),
          hxTarget: button.getAttribute('hx-target'),
          hxSwap: button.getAttribute('hx-swap'),
        });
      },
      toolCardAfter: (evt) => {
        const src = (evt.detail && evt.detail.elt) || evt.target;
        const button = src && src.closest ? src.closest('[data-tool-card]') : null;
        if (button) {
          button.classList.remove('ring-1', 'ring-primary-400/60');
          button.removeAttribute('data-tool-card-active');
          dbg('toolCardAfter(button)', { key: button.getAttribute('data-tool-card') });
          return;
        }
        if (evt.target === controller.ctx.workspace || (evt.target && evt.target.id === 'tool-workspace')) {
          // Clean up any stale UI state on tool cards after panel swaps
          const allCards = global.document.querySelectorAll('[data-tool-card]');
          allCards.forEach((el) => {
            el.classList.remove('ring-1', 'ring-primary-400/60');
            el.removeAttribute('data-tool-card-active');
          });
          const table = ui.getTableController();
          if (table && typeof table.collapseAll === 'function') {
            table.collapseAll();
          }
          controller.ui.boost(controller.ctx.caseId);
          dbg('toolCardAfter(workspace)', { targetId: evt.target && evt.target.id });
        }
      },
      toolCardSettle: (evt) => {
        if (evt.target === controller.ctx.workspace) {
          const allCards = global.document.querySelectorAll('[data-tool-card]');
          allCards.forEach((el) => {
            el.classList.remove('ring-1', 'ring-primary-400/60');
            el.removeAttribute('data-tool-card-active');
          });
          dbg('toolCardSettle', { targetId: evt.target && evt.target.id });
        }
      },
      toolCardAfterRequest: (evt) => {
        const src = (evt.detail && evt.detail.elt) || evt.target;
        const button = src && src.closest ? src.closest('[data-tool-card]') : null;
        if (button) {
          button.classList.remove('ring-1', 'ring-primary-400/60');
          button.removeAttribute('data-tool-card-active');
          dbg('toolCardAfterRequest', { key: button.getAttribute('data-tool-card') });
        }
      },
      toolCardError: (evt) => {
        const src = (evt.detail && evt.detail.elt) || evt.target;
        const button = src && src.closest ? src.closest('[data-tool-card]') : null;
        if (button) {
          button.classList.remove('ring-1', 'ring-primary-400/60');
          button.removeAttribute('data-tool-card-active');
          dbg('toolCardError', { key: button.getAttribute('data-tool-card') });
        }
      },
      htmxAfterOnLoad: (evt) => {
        const headerValue = evt.detail?.xhr?.getResponseHeader('HX-Trigger');
        if (!headerValue) return;
        try {
          const payload = JSONU.parse(headerValue, null);
          if (!payload) return;
          const refreshed = payload['case-view-refreshed'];
          if (!refreshed) return;
          if (refreshed.header_html) {
            const headerContainer = global.document.querySelector('[data-case-header-container]');
            if (headerContainer) headerContainer.innerHTML = refreshed.header_html;
            try { if (global.htmx && global.htmx.process) { global.htmx.process(headerContainer); } } catch (_) {}
          }
          if (refreshed.cards_html) {
            const cardsContainer = global.document.querySelector('[data-case-developer-cards]');
            if (cardsContainer) {
              cardsContainer.innerHTML = refreshed.cards_html;
              try { if (global.htmx && global.htmx.process) { global.htmx.process(cardsContainer); } } catch (_) {}
            }
          }
          if (Object.prototype.hasOwnProperty.call(refreshed, 'collaboration_html')) {
            const collabContainer = global.document.querySelector('[data-case-collaboration]');
            if (collabContainer) {
              collabContainer.innerHTML = refreshed.collaboration_html || '';
              try { if (global.htmx && global.htmx.process) { global.htmx.process(collabContainer); } } catch (_) {}
            }
          }
          if (refreshed.active_tool) {
            ui.setActiveCard(refreshed.active_tool);
          }
          controller.ui.boost(controller.ctx.caseId);
          dbg('htmxAfterOnLoad', { refreshed });
        } catch (error) {
          console.warn('Failed to parse HX-Trigger payload', error);
        }
      },
    };

    // Rely on jobsTable to handle row click/key events
    global.document.body.addEventListener('click', handlers.jobAction);
    global.document.body.addEventListener('click', handlers.jobNotesSave);
    global.document.body.addEventListener('click', handlers.verifyHash);
    global.document.body.addEventListener('click', handlers.audioRefresh);
    global.document.body.addEventListener('click', handlers.transcriptAction);
    global.document.body.addEventListener('click', handlers.jobLink);
    global.document.body.addEventListener('click', handlers.jobLog);
    global.document.body.addEventListener('click', handlers.analysisAction);
    global.document.body.addEventListener('htmx:beforeRequest', handlers.toolCardBefore);
    global.document.body.addEventListener('htmx:afterSwap', handlers.toolCardAfter);
    global.document.body.addEventListener('htmx:afterSettle', handlers.toolCardSettle);
    global.document.body.addEventListener('htmx:afterRequest', handlers.toolCardAfterRequest);
    global.document.body.addEventListener('htmx:error', handlers.toolCardError);
    global.document.body.addEventListener('htmx:afterOnLoad', handlers.htmxAfterOnLoad);

    // Instrument clicks on tool cards to observe state
    try {
      global.document.body.addEventListener('click', (evt) => {
        const el = evt.target && evt.target.closest ? evt.target.closest('[data-tool-card]') : null;
        if (!el) return;
        dbg('tool-card-click', {
          key: el.getAttribute('data-tool-card'),
          hasActive: el.hasAttribute('data-tool-card-active'),
          hxGet: el.getAttribute('hx-get'),
          hxTarget: el.getAttribute('hx-target'),
          hxSwap: el.getAttribute('hx-swap'),
        });
      }, true);
    } catch (_) {}

    caseDetail._listenersBound = true;
    caseDetail._handlers = handlers;
  }

  function bootstrap(controller) {
    const { ctx, ui } = controller;
    ui.initJobsTable();
    ui.setActiveCard(ctx.initialToolKey);
    ui.boost(ctx.caseId);
  }

  function init(options = {}) {
    if (caseDetail.controller) {
      return caseDetail.controller;
    }

    const ctx = createContext(options);
    if (!ctx) {
      return null;
    }

    const notify = createNotifier(ctx);

    uiModule.setContext?.(ctx);
    realtimeModule.setContext?.(ctx);
    modalsModule.setContext?.(ctx);
    modalsModule.setNotify?.(notify);
    actionsModule.setContext?.(ctx);

    const controller = {
      ctx,
      notify,
      helpers,
      ui: uiModule,
      realtime: realtimeModule,
      modals: modalsModule,
      actions: actionsModule,
    };

    controller.ui.setDeps?.({
      helpers,
      realtime: controller.realtime,
      notify: controller.notify,
      actions: controller.actions,
      onTranscribeRefresh: () => controller.ui.refreshCaseJobs(ctx.caseId),
    });
    controller.realtime.setDeps?.({
      ui: controller.ui,
      scheduleTranscribeRefresh: () => controller.ui.scheduleTranscribeRefresh(),
    });
    controller.actions.setDeps?.({
      helpers,
      ui: controller.ui,
      realtime: controller.realtime,
      modals: controller.modals,
      notify: controller.notify,
    });

    caseDetail.controller = controller;
    caseDetail.refresh = controller.ui.refreshCaseJobs;
    caseDetail.boost = (caseIdParam) => controller.ui.boost(caseIdParam || controller.ctx.caseId);
    bindGlobalEvents(controller);
    bootstrap(controller);
    return controller;
  }

  caseDetail.init = init;
  init();
})(window);
