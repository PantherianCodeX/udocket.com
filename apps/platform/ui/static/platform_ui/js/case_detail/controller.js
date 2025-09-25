(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});

  if (typeof caseDetail.init === 'function' && caseDetail.controller) {
    return;
  }

  const helpers = caseDetail.helpers || {};
  const uiModule = caseDetail.ui || {};
  const realtimeModule = caseDetail.realtime || {};
  const modalsModule = caseDetail.modals || {};
  const actionsModule = caseDetail.actions || {};

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
      };
    jobsState.currentCaseId = caseId;
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

  function createNotifier(ctx) {
    const toastAt = ctx.toastAt;
    const toast = ctx.toast;
    return function notify(x, y, text) {
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
      },
      toolCardAfter: (evt) => {
        const src = (evt.detail && evt.detail.elt) || evt.target;
        const button = src && src.closest ? src.closest('[data-tool-card]') : null;
        if (button) {
          button.classList.remove('ring-1', 'ring-primary-400/60');
          button.removeAttribute('data-tool-card-active');
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
        }
      },
      toolCardSettle: (evt) => {
        if (evt.target === controller.ctx.workspace) {
          const allCards = global.document.querySelectorAll('[data-tool-card]');
          allCards.forEach((el) => {
            el.classList.remove('ring-1', 'ring-primary-400/60');
            el.removeAttribute('data-tool-card-active');
          });
        }
      },
      toolCardAfterRequest: (evt) => {
        const src = (evt.detail && evt.detail.elt) || evt.target;
        const button = src && src.closest ? src.closest('[data-tool-card]') : null;
        if (button) {
          button.classList.remove('ring-1', 'ring-primary-400/60');
          button.removeAttribute('data-tool-card-active');
        }
      },
      toolCardError: (evt) => {
        const src = (evt.detail && evt.detail.elt) || evt.target;
        const button = src && src.closest ? src.closest('[data-tool-card]') : null;
        if (button) {
          button.classList.remove('ring-1', 'ring-primary-400/60');
          button.removeAttribute('data-tool-card-active');
        }
      },
      htmxAfterOnLoad: (evt) => {
        const headerValue = evt.detail?.xhr?.getResponseHeader('HX-Trigger');
        if (!headerValue) return;
        try {
          const payload = JSON.parse(headerValue);
          const refreshed = payload['case-view-refreshed'];
          if (!refreshed) return;
          if (refreshed.header_html) {
            const headerContainer = global.document.querySelector('[data-case-header-container]');
            if (headerContainer) headerContainer.innerHTML = refreshed.header_html;
          }
          if (refreshed.cards_html) {
            const cardsContainer = global.document.querySelector('[data-case-developer-cards]');
            if (cardsContainer) cardsContainer.innerHTML = refreshed.cards_html;
          }
          if (refreshed.active_tool) {
            ui.setActiveCard(refreshed.active_tool);
          }
          controller.ui.boost(controller.ctx.caseId);
        } catch (error) {
          console.warn('Failed to parse HX-Trigger payload', error);
        }
      },
    };

    // Rely on jobsTable to handle row click/key events
    global.document.body.addEventListener('click', handlers.jobAction);
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
