(function () {
  const EXCALIDRAW_MODULE_URL = 'https://esm.sh/@excalidraw/excalidraw@0.18.0?external=react,react-dom';
  const RUNTIME_LOAD_TIMEOUT_MS = 12000;
  const SCENE_LOAD_TIMEOUT_MS = 8000;
  const EDITOR_READY_TIMEOUT_MS = 10000;
  const state = {
    runtime: null,
    runtimePromise: null,
    sceneCache: new Map(),
    editorRoot: null,
    editorScene: null,
    editorOriginalScene: null,
    editorStepId: null,
    editorSceneSrc: null,
    editorFrameId: null,
    editorTitle: '',
    editorReady: false,
    editorDirty: false,
    runtimeErrorHandler: null,
    editorReadyTimer: 0,
    previewRefreshTimer: 0,
    renderSeq: 0
  };

  function $(selector, root = document) {
    return root.querySelector(selector);
  }

  function $all(selector, root = document) {
    return [...root.querySelectorAll(selector)];
  }

  function getMainGeneratedArea() {
    return $('#proto-generated-area');
  }

  function getSteps(root = document) {
    return $all('.journey-step[data-proto-id]', root);
  }

  function getActiveStep() {
    const area = getMainGeneratedArea();
    return (
      area?.querySelector('.journey-step.is-active[data-proto-id]') ||
      area?.querySelector('.journey-step.is-prd-focus[data-proto-id]') ||
      area?.querySelector('.journey-step[data-proto-id]') ||
      null
    );
  }

  function getStepById(stepId, root = document) {
    if (!stepId) return null;
    return root.querySelector(`.journey-step[data-proto-id="${CSS.escape(stepId)}"]`);
  }

  function getSceneCard(step) {
    return step?.querySelector('.proto-excalidraw-card[data-scene-src]') || null;
  }

  function sceneInfoFromStep(step) {
    const card = getSceneCard(step);
    if (!step || !card) return null;
    return {
      step,
      card,
      stepId: card.dataset.stepId || step.dataset.protoId,
      sceneSrc: card.dataset.sceneSrc,
      frameId: card.dataset.frameId || '',
      boardId: card.dataset.boardId || '',
      title: card.dataset.sceneTitle || step.dataset.protoLabel || step.id || 'Excalidraw scene'
    };
  }

  function showToast(message) {
    const toast = $('#toast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove('hidden');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.add('hidden'), 2600);
  }

  function setSaveStatus(message) {
    const node = $('#excalidraw-save-status');
    if (node) node.textContent = message;
  }

  function diagnostics() {
    return window.ProtoPilotDiagnostics || null;
  }

  function diagEvent(event, payload) {
    diagnostics()?.add?.(event, payload);
  }

  function diagError(event, error, payload) {
    diagnostics()?.error?.(event, error, payload);
  }

  function revealDiagnostics(reason) {
    diagnostics()?.reveal?.(reason);
  }

  function setEditMode(enabled) {
    const next = Boolean(enabled);
    document.body.classList.toggle('proto-excalidraw-edit-mode', next);
    const button = $('#proto-excalidraw-edit-btn');
    const mainToolbar = $('#proto-main-toolbar');
    const editToolbar = $('#proto-excalidraw-mode-toolbar');
    if (button) {
      button.classList.toggle('is-active', next);
      button.setAttribute('aria-pressed', next ? 'true' : 'false');
      button.title = next ? '退出原型编辑模式' : '进入原型编辑模式';
    }
    if (mainToolbar) mainToolbar.classList.toggle('hidden', next);
    if (editToolbar) editToolbar.classList.toggle('hidden', !next);
    getSteps().forEach((step) => {
      const card = getSceneCard(step);
      if (!card) return;
      card.tabIndex = next ? 0 : -1;
      card.setAttribute('role', next ? 'button' : 'group');
      card.setAttribute('aria-label', next ? `编辑 ${card.dataset.sceneTitle || step.dataset.protoLabel || '画布'}` : 'Excalidraw 原型预览');
    });
  }

  function toggleExcalidrawEditMode(force) {
    const enabled = typeof force === 'boolean' ? force : !document.body.classList.contains('proto-excalidraw-edit-mode');
    if (enabled) {
      if (window.ProtoPilotShell?.resetModes) window.ProtoPilotShell.resetModes();
    }
    setEditMode(enabled);
  }

  async function loadExcalidrawRuntime() {
    if (state.runtime) return state.runtime;
    if (!state.runtimePromise) {
      diagEvent('sketch_runtime_load_start', { module: EXCALIDRAW_MODULE_URL });
      state.runtimePromise = withTimeout(
        Promise.all([
          import('react'),
          import('react-dom/client'),
          import(EXCALIDRAW_MODULE_URL)
        ]),
        RUNTIME_LOAD_TIMEOUT_MS,
        'Excalidraw 运行时加载超时。请检查当前网络是否能访问外部模块，或稍后改用本地化运行时方案。'
      )
        .then(([ReactModule, ReactDomModule, ExcalidrawModule]) => {
          const React = ReactModule.default || ReactModule;
          const ReactDOM = ReactDomModule.default || ReactDomModule;
          const Excalidraw = ExcalidrawModule.Excalidraw || ExcalidrawModule.default;
          const exportToSvg = ExcalidrawModule.exportToSvg;
          if (!React?.createElement || !ReactDOM?.createRoot || !Excalidraw || typeof exportToSvg !== 'function') {
            throw new Error('Excalidraw runtime did not expose the expected component/export API.');
          }
          state.runtime = { React, ReactDOM, Excalidraw, exportToSvg };
          diagEvent('sketch_runtime_load_ok', {
            hasReact: Boolean(React?.createElement),
            hasReactRoot: Boolean(ReactDOM?.createRoot),
            hasExcalidraw: Boolean(Excalidraw),
            hasExportToSvg: typeof exportToSvg === 'function'
          });
          return state.runtime;
        })
        .catch((error) => {
          state.runtimePromise = null;
          diagError('sketch_runtime_load_failed', error, { module: EXCALIDRAW_MODULE_URL });
          throw error;
        });
    }
    return state.runtimePromise;
  }

  async function fetchScene(sceneSrc) {
    if (state.sceneCache.has(sceneSrc)) return state.sceneCache.get(sceneSrc);
    diagEvent('sketch_board_fetch_start', { sceneSrc });
    const request = withTimeout(
      fetch(sceneSrc, { cache: 'no-store' }),
      SCENE_LOAD_TIMEOUT_MS,
      `Board 文件读取超时：${sceneSrc}`
    )
      .then((response) => {
        if (!response.ok) throw new Error(`Board 文件读取失败：HTTP ${response.status}`);
        return response.text().then((text) => {
          const scene = JSON.parse(text);
          Object.defineProperty(scene, '__protoPilotMeta', {
            value: {
              sceneSrc,
              byteLength: new Blob([text]).size,
              contentLength: response.headers.get('content-length') || null
            },
            enumerable: false,
            configurable: true
          });
          diagEvent('sketch_board_fetch_ok', {
            sceneSrc,
            byteLength: scene.__protoPilotMeta.byteLength,
            stats: sceneStats(scene)
          });
          return scene;
        });
      })
      .catch((error) => {
        state.sceneCache.delete(sceneSrc);
        diagError('sketch_board_fetch_failed', error, { sceneSrc });
        throw error;
      });
    state.sceneCache.set(sceneSrc, request);
    return request;
  }

  function cleanInitialAppState(appState) {
    const source = appState && typeof appState === 'object' ? appState : {};
    const clean = {
      viewBackgroundColor: source.viewBackgroundColor || '#ffffff',
      currentItemFontFamily: source.currentItemFontFamily || 2,
      currentItemStrokeColor: source.currentItemStrokeColor || '#1e1e1e',
      currentItemBackgroundColor: source.currentItemBackgroundColor || 'transparent',
      currentItemFillStyle: source.currentItemFillStyle || 'hachure',
      currentItemStrokeWidth: source.currentItemStrokeWidth || 2,
      currentItemRoughness: source.currentItemRoughness || 1,
      currentItemOpacity: source.currentItemOpacity || 100,
      currentItemRoundness: source.currentItemRoundness || 'round',
      currentItemStartArrowhead: source.currentItemStartArrowhead || null,
      currentItemEndArrowhead: source.currentItemEndArrowhead || 'arrow',
      theme: source.theme || 'light'
    };
    return clean;
  }

  function normalizeScene(scene) {
    return {
      elements: sanitizeElementsForEditor(scene?.elements),
      appState: cleanInitialAppState(scene?.appState),
      files: scene?.files && typeof scene.files === 'object' ? scene.files : {},
      scrollToContent: true
    };
  }

  function sanitizeElementsForEditor(elements) {
    const source = Array.isArray(elements) ? elements : [];
    return source.map((element) => {
      const clean = jsonSafe(element);
      // Older generated boards used frame index values such as "a010".
      // Excalidraw's embedded fractional-indexing runtime rejects those keys,
      // while the official import flow can repair them. Let the runtime assign
      // fresh order keys instead of passing invalid generated values through.
      if (clean && Object.prototype.hasOwnProperty.call(clean, 'index')) delete clean.index;
      return clean;
    });
  }

  function sceneStats(scene) {
    const elements = Array.isArray(scene?.elements) ? scene.elements : [];
    const visible = elements.filter((element) => !element?.isDeleted);
    const typeCounts = {};
    visible.forEach((element) => {
      const type = element?.type || 'unknown';
      typeCounts[type] = (typeCounts[type] || 0) + 1;
    });
    return {
      elementCount: elements.length,
      visibleElementCount: visible.length,
      frameCount: visible.filter((element) => element?.type === 'frame').length,
      fileCount: scene?.files && typeof scene.files === 'object' ? Object.keys(scene.files).length : 0,
      appStateKeys: scene?.appState && typeof scene.appState === 'object' ? Object.keys(scene.appState).sort().slice(0, 80) : [],
      indexCount: visible.filter((element) => Object.prototype.hasOwnProperty.call(element || {}, 'index')).length,
      indexSamples: visible
        .filter((element) => Object.prototype.hasOwnProperty.call(element || {}, 'index'))
        .slice(0, 20)
        .map((element) => element.index),
      typeCounts
    };
  }

  function jsonSafe(value) {
    return JSON.parse(
      JSON.stringify(value || {}, (key, current) => {
        if (key === 'collaborators') return undefined;
        if (current instanceof Map) return Object.fromEntries(current);
        return current;
      })
    );
  }

  function makeScene(elements, appState, files) {
    const cleanAppState = jsonSafe(appState || {});
    delete cleanAppState.collaborators;
    return {
      type: 'excalidraw',
      version: 2,
      source: 'Finn ProtoPilot Excalidraw',
      elements: jsonSafe(elements || []),
      appState: cleanAppState,
      files: jsonSafe(files || {})
    };
  }

  function renderEditorLoading(message) {
    const rootElement = $('#excalidraw-editor-root');
    if (rootElement) rootElement.innerHTML = `<div class="excalidraw-editor-loading">${escapeHtml(message)}</div>`;
  }

  function renderEditorError(message, detail) {
    const rootElement = $('#excalidraw-editor-root');
    if (!rootElement) return;
    const detailHtml = detail ? `<p>${escapeHtml(detail)}</p>` : '';
    rootElement.innerHTML = `<div class="excalidraw-editor-error"><div><strong>${escapeHtml(message)}</strong>${detailHtml}<button type="button" class="proto-float-btn excalidraw-copy-diagnostics" data-excalidraw-copy-diagnostics>复制调试日志</button></div></div>`;
    revealDiagnostics('sketch_editor_error');
  }

  function withTimeout(promise, timeoutMs, message) {
    let timer = 0;
    const timeout = new Promise((_, reject) => {
      timer = window.setTimeout(() => reject(new Error(message)), timeoutMs);
    });
    return Promise.race([promise, timeout]).finally(() => window.clearTimeout(timer));
  }

  function editorLoadingState(rootElement) {
    const text = rootElement?.textContent || '';
    return {
      hasExcalidrawRoot: Boolean(rootElement?.querySelector('.excalidraw')),
      hasCanvas: Boolean(rootElement?.querySelector('canvas')),
      hasToolbar: Boolean(rootElement?.querySelector('.Island, [data-testid], .App-toolbar, .ToolIcon')),
      textSnippet: text.trim().replace(/\s+/g, ' ').slice(0, 180),
      stillLoading:
        text.includes('正在加载绘图') ||
        text.includes('Loading scene') ||
        text.includes('Loading') ||
        Boolean(rootElement?.querySelector('.LoadingMessage'))
    };
  }

  function markEditorReady(reason) {
    if (state.editorReady) return;
    state.editorReady = true;
    window.clearTimeout(state.editorReadyTimer);
    setSaveStatus('就绪');
    diagEvent('sketch_editor_ready', { reason });
  }

  function failEditorInternalLoading(rootElement, info) {
    const loading = editorLoadingState(rootElement);
    const error = new Error('Excalidraw 画布还没有完成加载。');
    diagError('editor_internal_loading_timeout', error, {
      sceneSrc: info.sceneSrc,
      frameId: info.frameId || '',
      boardId: info.boardId || '',
      loading
    });
    setSaveStatus('加载未完成');
    if (state.editorRoot) {
      try {
        state.editorRoot.unmount();
      } catch (_error) {
        // Ignore unmount failures while reporting the original loading problem.
      }
      state.editorRoot = null;
    }
    renderEditorError('画布还没有完成加载。', '已生成调试日志，请复制后发给维护者排查。');
  }

  async function openExcalidrawEditor(stepId) {
    const step = getStepById(stepId) || getActiveStep();
    const info = sceneInfoFromStep(step);
    if (!info?.sceneSrc) {
      showToast('当前步骤没有绑定 Excalidraw scene');
      return;
    }

    const modal = $('#excalidraw-editor-modal');
    const rootElement = $('#excalidraw-editor-root');
    const title = $('#excalidraw-editor-title');
    if (!modal || !rootElement) return;

    modal.classList.remove('hidden');
    renderEditorLoading('正在加载画布...');
    if (title) title.textContent = info.title;
    setSaveStatus('加载中');
    if (window.ProtoPilotShell?.resetModes) window.ProtoPilotShell.resetModes();
    setEditMode(true);
    diagEvent('sketch_editor_open', {
      stepId: info.stepId,
      sceneSrc: info.sceneSrc,
      frameId: info.frameId || '',
      boardId: info.boardId || '',
      title: info.title
    });

    try {
      attachRuntimeErrorTrap();
      renderEditorLoading('正在加载 Excalidraw 运行时...');
      setSaveStatus('加载运行时');
      const runtime = await loadExcalidrawRuntime();
      renderEditorLoading('正在读取 board 文件...');
      setSaveStatus('读取 board');
      const scene = await fetchScene(info.sceneSrc);
      const normalizedScene = normalizeScene(scene);
      const stats = sceneStats(scene);
      diagEvent('sketch_editor_scene_parsed', {
        sceneSrc: info.sceneSrc,
        frameId: info.frameId || '',
        meta: scene.__protoPilotMeta || null,
        stats
      });
      if (info.frameId && !elementsForFrame(normalizedScene, info.frameId).length) {
        throw new Error(`Frame 不存在或为空：${info.frameId}`);
      }
      state.editorScene = scene;
      state.editorOriginalScene = JSON.parse(JSON.stringify(scene));
      state.editorStepId = info.stepId;
      state.editorSceneSrc = info.sceneSrc;
      state.editorFrameId = info.frameId || '';
      state.editorTitle = info.title;
      state.editorReady = false;
      state.editorDirty = false;
      if (state.editorRoot) state.editorRoot.unmount();
      rootElement.innerHTML = '';
      setSaveStatus('初始化编辑器');
      state.editorRoot = runtime.ReactDOM.createRoot(rootElement);
      diagEvent('sketch_editor_initial_data_ready', {
        sceneSrc: info.sceneSrc,
        frameId: info.frameId || '',
        stats: sceneStats(normalizedScene),
        appStateKeys: Object.keys(normalizedScene.appState || {}).sort()
      });
      state.editorRoot.render(
        runtime.React.createElement(runtime.Excalidraw, {
          initialData: normalizedScene,
          viewModeEnabled: false,
          zenModeEnabled: false,
          gridModeEnabled: false,
          autoFocus: true,
          detectScroll: false,
          langCode: 'zh-CN',
          aiEnabled: false,
          name: info.title,
          UIOptions: {
            canvasActions: {
              loadScene: false,
              saveToActiveFile: false,
              export: false
            }
          },
          onChange(elements, appState, files) {
            state.editorScene = makeScene(elements, appState, files);
            if (!state.editorReady) markEditorReady('onChange');
            if (state.editorReady && sceneElementsChanged(elements)) {
              state.editorDirty = true;
              setSaveStatus('未保存');
            }
          }
        })
      );
      window.clearTimeout(state.editorReadyTimer);
      state.editorReadyTimer = window.setTimeout(() => {
        if (state.editorReady) return;
        const loading = editorLoadingState(rootElement);
        if (loading.hasCanvas && loading.hasExcalidrawRoot && !loading.stillLoading) {
          markEditorReady('dom_ready_without_onchange');
          return;
        }
        failEditorInternalLoading(rootElement, info);
      }, EDITOR_READY_TIMEOUT_MS);
    } catch (error) {
      setSaveStatus('加载失败');
      diagError('sketch_editor_open_failed', error, {
        sceneSrc: info.sceneSrc,
        frameId: info.frameId || '',
        boardId: info.boardId || ''
      });
      renderEditorError(error.message || String(error), `board: ${info.sceneSrc} / frame: ${info.frameId || 'all'}`);
    }
  }

  function attachRuntimeErrorTrap() {
    if (state.runtimeErrorHandler) return;
    state.runtimeErrorHandler = (event) => {
      if ($('#excalidraw-editor-modal')?.classList.contains('hidden')) return;
      const message = event?.message || event?.reason?.message || 'Excalidraw runtime error';
      diagError('sketch_runtime_error', event?.error || event?.reason || new Error(message), {
        editorSceneSrc: state.editorSceneSrc,
        editorFrameId: state.editorFrameId
      });
      setSaveStatus('运行异常');
      const rootElement = $('#excalidraw-editor-root');
      if (rootElement && !rootElement.querySelector('canvas')) {
        renderEditorError(message, '运行时异常已记录到调试日志。');
      }
    };
    window.addEventListener('error', state.runtimeErrorHandler);
    window.addEventListener('unhandledrejection', state.runtimeErrorHandler);
  }

  function closeExcalidrawEditor() {
    $('#excalidraw-editor-modal')?.classList.add('hidden');
    window.clearTimeout(state.editorReadyTimer);
    if (state.editorRoot) {
      state.editorRoot.unmount();
      state.editorRoot = null;
    }
    diagEvent('sketch_editor_close', {
      sceneSrc: state.editorSceneSrc,
      frameId: state.editorFrameId,
      dirty: state.editorDirty
    });
    state.editorScene = null;
    state.editorOriginalScene = null;
    state.editorStepId = null;
    state.editorSceneSrc = null;
    state.editorFrameId = null;
    state.editorReady = false;
    state.editorDirty = false;
    setSaveStatus('就绪');
    renderEditorLoading('正在准备画布...');
  }

  function resetExcalidrawEditor() {
    if (!state.editorOriginalScene || !state.editorStepId) return;
    const stepId = state.editorStepId;
    closeExcalidrawEditor();
    openExcalidrawEditor(stepId);
  }

  async function saveExcalidrawScene() {
    if (!state.editorScene || !state.editorSceneSrc) return;
    setSaveStatus('保存中');
    diagEvent('sketch_save_start', {
      sceneSrc: state.editorSceneSrc,
      frameId: state.editorFrameId,
      stats: sceneStats(state.editorScene)
    });
    try {
      const healthResponse = await fetch('/.protopilot-preview-health', { cache: 'no-store' });
      if (!healthResponse.ok) throw new Error(`Preview health unavailable (${healthResponse.status})`);
      const health = await healthResponse.json();
      if (!health || !health.ok || !health.token) throw new Error('Current page is not running under ProtoPilot preview.');
      const response = await fetch('/__protopilot_excalidraw/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-ProtoPilot-Preview-Token': health.token
        },
        body: JSON.stringify({ scene_path: state.editorSceneSrc, scene: state.editorScene })
      });
      if (!response.ok) throw new Error(`Save API unavailable (${response.status}) at /__protopilot_excalidraw/save`);
      state.editorOriginalScene = JSON.parse(JSON.stringify(state.editorScene));
      state.editorDirty = false;
      state.sceneCache.set(state.editorSceneSrc, Promise.resolve(state.editorScene));
      setSaveStatus('已保存');
      await refreshPreviewForSceneSrc(state.editorSceneSrc, state.editorScene);
      showToast('画布已保存');
      diagEvent('sketch_save_ok', { sceneSrc: state.editorSceneSrc });
    } catch (_error) {
      diagError('sketch_save_failed_download_backup', _error, { sceneSrc: state.editorSceneSrc });
      downloadScene(state.editorScene, sceneFilename(state.editorSceneSrc));
      setSaveStatus('已下载备份');
      showToast('保存服务不可用，已生成本地备份');
    }
  }

  function elementsForFrame(scene, frameId) {
    const elements = (Array.isArray(scene?.elements) ? scene.elements : []).filter((element) => !element?.isDeleted);
    if (!frameId) return elements;
    const frame = elements.find((element) => element?.type === 'frame' && element.id === frameId);
    if (!frame) throw new Error(`Frame not found: ${frameId}`);
    const fx = Number(frame.x || 0);
    const fy = Number(frame.y || 0);
    const fw = Number(frame.width || 0);
    const fh = Number(frame.height || 0);
    return elements.filter((element) => {
      if (element === frame || element.id === frameId || element.frameId === frameId) return true;
      const x = Number(element.x || 0);
      const y = Number(element.y || 0);
      const w = Number(element.width || 0);
      const h = Number(element.height || 0);
      return x >= fx && y >= fy && x + w <= fx + fw + 4 && y + h <= fy + fh + 4;
    });
  }

  function frameElement(scene, frameId) {
    if (!frameId) return null;
    const elements = (Array.isArray(scene?.elements) ? scene.elements : []).filter((element) => !element?.isDeleted);
    return elements.find((element) => element?.type === 'frame' && element.id === frameId) || null;
  }

  function isPreviewAuxElement(element) {
    const id = String(element?.id || '');
    return element?.type === 'text' && id.endsWith('-trace');
  }

  function makeEmptyPreviewSvg() {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svg.setAttribute('viewBox', '0 0 320 560');
    svg.setAttribute('width', '320');
    svg.setAttribute('height', '560');
    svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    background.setAttribute('x', '0');
    background.setAttribute('y', '0');
    background.setAttribute('width', '320');
    background.setAttribute('height', '560');
    background.setAttribute('fill', '#ffffff');
    svg.appendChild(background);
    return svg;
  }

  async function renderSceneToSvg(scene, frameId = '') {
    const runtime = await loadExcalidrawRuntime();
    const normalized = normalizeScene(scene);
    const previewElements = elementsForFrame(normalized, frameId).filter((element) => !isPreviewAuxElement(element));
    if (!previewElements.length) {
      const emptySvg = makeEmptyPreviewSvg();
      emptySvg.setAttribute('role', 'img');
      emptySvg.setAttribute('aria-label', 'Excalidraw scene preview');
      emptySvg.classList.add('proto-excalidraw-official-svg');
      emptySvg.style.width = '100%';
      emptySvg.style.height = '100%';
      return emptySvg;
    }
    const svg = await runtime.exportToSvg({
      elements: previewElements,
      appState: {
        ...normalized.appState,
        exportBackground: true,
        exportWithDarkMode: false,
        viewBackgroundColor: normalized.appState.viewBackgroundColor || '#ffffff'
      },
      files: normalized.files,
      exportPadding: 24
    });
    if (sceneHasCjkText(normalized) && svgTextLooksBroken(svg)) {
      throw new Error('Official SVG export produced placeholder text for CJK content.');
    }
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Excalidraw scene preview');
    svg.classList.add('proto-excalidraw-official-svg');
    svg.style.width = '100%';
    svg.style.height = '100%';
    return svg;
  }

  function sceneElementsChanged(elements) {
    try {
      return JSON.stringify(jsonSafe(elements || [])) !== JSON.stringify(jsonSafe(state.editorOriginalScene?.elements || []));
    } catch (_error) {
      return true;
    }
  }

  function sceneHasCjkText(scene) {
    return (Array.isArray(scene?.elements) ? scene.elements : []).some((element) => {
      return element?.type === 'text' && /[\u3400-\u9fff]/.test(String(element.text || ''));
    });
  }

  function svgTextLooksBroken(svg) {
    return /\?{2,}/.test(String(svg?.textContent || ''));
  }

  function makePreviewError(message) {
    const node = document.createElement('div');
    node.className = 'proto-excalidraw-placeholder';
    node.textContent = message || 'Preview render failed';
    return node;
  }

  function beginPreviewRender(preview) {
    const token = String(++state.renderSeq);
    preview.dataset.renderToken = token;
    preview.dataset.renderState = 'loading';
    return token;
  }

  function previewTokenIsCurrent(preview, token) {
    return preview?.dataset.renderToken === token;
  }

  async function renderPreviewCard(card) {
    const sceneSrc = card?.dataset.sceneSrc;
    const preview = card?.querySelector('.proto-excalidraw-preview');
    if (!sceneSrc || !preview) return;
    const previousState = preview.dataset.renderState || '';
    const token = beginPreviewRender(preview);
    try {
      const scene = await fetchScene(sceneSrc);
      const svg = await renderSceneToSvg(scene, card.dataset.frameId || '');
      if (!previewTokenIsCurrent(preview, token)) return;
      preview.replaceChildren(svg);
      preview.dataset.renderState = 'official';
    } catch (error) {
      if (!previewTokenIsCurrent(preview, token)) return;
      if (previousState === 'official') {
        preview.replaceChildren(makePreviewError(error?.message || 'Preview render failed'));
        preview.dataset.renderState = 'failed';
      } else {
        preview.dataset.renderState = 'fallback';
      }
      preview.dataset.renderError = String(error?.message || error || 'render failed');
    }
  }

  async function renderAllPreviews() {
    const cards = $all('.proto-excalidraw-card[data-scene-src]', getMainGeneratedArea() || document);
    await Promise.all(cards.map((card) => renderPreviewCard(card)));
    scheduleShellRefresh();
  }

  async function refreshPreviewCardWithScene(card, scene) {
    const preview = card?.querySelector('.proto-excalidraw-preview');
    if (!preview || !scene) return;
    const token = beginPreviewRender(preview);
    try {
      const svg = await renderSceneToSvg(scene, card.dataset.frameId || '');
      if (!previewTokenIsCurrent(preview, token)) return;
      preview.replaceChildren(svg);
      preview.dataset.renderState = 'official';
    } catch (error) {
      if (!previewTokenIsCurrent(preview, token)) return;
      preview.replaceChildren(makePreviewError(error?.message || 'Preview render failed'));
      preview.dataset.renderState = 'failed';
      preview.dataset.renderError = String(error?.message || error || 'render failed');
    }
  }

  async function refreshPreviewForSceneSrc(sceneSrc, scene) {
    const cards = $all(`.proto-excalidraw-card[data-scene-src="${CSS.escape(sceneSrc)}"]`, getMainGeneratedArea() || document);
    await Promise.all(cards.map((card) => refreshPreviewCardWithScene(card, scene)));
    scheduleShellRefresh();
  }

  function scheduleShellRefresh() {
    window.clearTimeout(state.previewRefreshTimer);
    state.previewRefreshTimer = window.setTimeout(() => {
      if (window.ProtoPilotShell?.refresh) window.ProtoPilotShell.refresh({ preserveActiveId: true });
    }, 60);
  }

  function openCurrentExcalidrawEditor() {
    const info = sceneInfoFromStep(getActiveStep());
    if (info?.stepId) openExcalidrawEditor(info.stepId);
  }

  function downloadScene(scene, filename) {
    const blob = new Blob([JSON.stringify(scene, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'scene.excalidraw';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function sceneFilename(sceneSrc) {
    return String(sceneSrc || 'scene.excalidraw').split(/[\\/]/).pop() || 'scene.excalidraw';
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function onDocumentClick(event) {
    if (event.target.closest?.('[data-excalidraw-copy-diagnostics]')) {
      event.preventDefault();
      window.ProtoPilotDiagnostics?.copy?.();
      return;
    }
    if (!document.body.classList.contains('proto-excalidraw-edit-mode')) return;
    const card = event.target.closest?.('.proto-excalidraw-card[data-scene-src]');
    if (!card || !getMainGeneratedArea()?.contains(card)) return;
    event.preventDefault();
    const step = card.closest('.journey-step[data-proto-id]');
    const info = sceneInfoFromStep(step);
    if (info?.stepId) openExcalidrawEditor(info.stepId);
  }

  function onDocumentKeydown(event) {
    if (event.key === 'Escape' && document.body.classList.contains('proto-excalidraw-edit-mode')) {
      setEditMode(false);
      return;
    }
    if (!document.body.classList.contains('proto-excalidraw-edit-mode')) return;
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const card = event.target.closest?.('.proto-excalidraw-card[data-scene-src]');
    if (!card) return;
    event.preventDefault();
    const step = card.closest('.journey-step[data-proto-id]');
    const info = sceneInfoFromStep(step);
    if (info?.stepId) openExcalidrawEditor(info.stepId);
  }

  function init() {
    setEditMode(false);
    document.addEventListener('click', onDocumentClick);
    document.addEventListener('keydown', onDocumentKeydown);
    renderAllPreviews();
    if (window.lucide) window.lucide.createIcons();
  }

  window.openExcalidrawEditor = openExcalidrawEditor;
  window.openCurrentExcalidrawEditor = openCurrentExcalidrawEditor;
  window.closeExcalidrawEditor = closeExcalidrawEditor;
  window.resetExcalidrawEditor = resetExcalidrawEditor;
  window.saveExcalidrawScene = saveExcalidrawScene;
  window.toggleExcalidrawEditMode = toggleExcalidrawEditMode;
  window.ProtoPilotExcalidraw = {
    open: openCurrentExcalidrawEditor,
    toggleEditMode: toggleExcalidrawEditMode,
    renderAllPreviews
  };

  document.addEventListener('DOMContentLoaded', init);
})();

