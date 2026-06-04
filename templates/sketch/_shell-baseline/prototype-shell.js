/**
 * Finn ProtoPilot HTML presentation stage — navigation, Markdown Viewer, spotlight, revision/edit authoring.
 * Expects prototype-base.css, Lucide UMD loaded before this script, and required DOM (see references/quality.md).
 */
    const revisionNotes = [];
    let selectedRevisionTarget = null;
    let editingRevisionIndex = null;
    let selectedEditTarget = null;
    let editSessionSnapshot = null;
    let editSessionOutput = false;
    let editSessionDirty = false;
    let editSessionSaving = false;
    const protoStateKey = 'finn-protopilot-html:prototype:ui-state';
    const textPatchSavePath = '/__protopilot_html/save-text-patch';
    const PRD_FONT_STEPS = Array.from({ length: 13 }, (_, index) => Number((1 + index * 0.05).toFixed(2)));
    let prdFontStepIndex = 0;
    let spotlightPlaceholder = null;
    let spotlightMountedStep = null;
    let spotlightOriginalState = null;
    let spotlightBaseScale = 1;
    let spotlightUserZoom = 1;
    let annotationLayoutRaf = null;

    function clampPrdFontIndex(index) {
      return Math.max(0, Math.min(PRD_FONT_STEPS.length - 1, index));
    }

    function applyPrdViewerFontScale() {
      prdFontStepIndex = clampPrdFontIndex(prdFontStepIndex);
      const viewer = document.querySelector('#prd-drawer .proto-prd-viewer');
      const label = document.getElementById('prd-font-step-label');
      const mult = PRD_FONT_STEPS[prdFontStepIndex];
      if (viewer) viewer.style.setProperty('--proto-prd-font-mult', String(mult));
      if (label) label.textContent = `${Math.round(mult * 100)}%`;
      const down = document.getElementById('prd-font-down');
      const up = document.getElementById('prd-font-up');
      if (down) down.disabled = prdFontStepIndex <= 0;
      if (up) up.disabled = prdFontStepIndex >= PRD_FONT_STEPS.length - 1;
    }

    function adjustPrdViewerFont(delta) {
      prdFontStepIndex = clampPrdFontIndex(prdFontStepIndex + (delta || 0));
      applyPrdViewerFontScale();
      persistUiState();
      if (window.lucide) window.lucide.createIcons();
    }

    const autoRevisionTargetSelectors = [
      '.journey-step',
      '.phone-frame',
      '.phone-screen',
      '.app-screen',
      '.web-surface',
      '.nav-bar',
      '.step-number',
      '.step-title',
      '.branch-caption',
      '.nav-icon',
      '.nav-title',
      '.demo-pill',
      '.screen-title',
      '.mini-meta',
      '.muted',
      '.segment-btn',
      '.list-row',
      '.row-main',
      '.row-desc',
      '.switch',
      '.toast',
      '.dialog-backdrop',
      '.dialog',
      '.primary-btn',
      '.secondary-btn',
      '.btn',
      '.card',
      '.card h3',
      '.card p',
      '.list-group',
      '.web-topbar strong',
      '.input',
      '.rail-link',
      '.kp-card',
      '.fake-row',
      '.skill-chip',
      '.empty-illus',
      '.error-callout',
      '.annotation',
      '.app-content',
      '.web-content',
      '[role="button"]'
    ];

    const editableTextSelectors = [
      '[data-proto-editable="text"]',
      'h1',
      'h2',
      'h3',
      'h4',
      'p',
      'li',
      'span',
      'label',
      'small',
      'strong',
      'button',
      'a',
      '.step-title',
      '.branch-caption',
      '.nav-title',
      '.demo-pill',
      '.screen-title',
      '.mini-meta',
      '.muted',
      '.segment-btn',
      '.row-main',
      '.row-desc',
      '.card h3',
      '.card p',
      '.web-topbar strong',
      '.annotation',
      '.primary-btn',
      '.secondary-btn',
      '.btn',
      '.rail-link',
      '.kp-card span',
      '.fake-row span',
      '.skill-chip',
      '[class*="title"]',
      '[class*="label"]',
      '[class*="desc"]',
      '[class*="caption"]',
      '[class*="meta"]',
      '[class*="badge"]',
      '[class*="tag"]',
      '[class*="chip"]',
      '[class*="pill"]'
    ];

    const protectedEditTargetSelectors = [
      '.proto-generated-area',
      '.journey-row',
      '.journey-step',
      '.step-header',
      '.section-divider',
      '.proto-content-screen',
      '.phone-frame',
      '.phone-screen',
      '.app-screen',
      '.web-surface',
      '.phone-status-bar',
      '.phone-home-indicator',
      '.nav-bar',
      '.app-content',
      '.web-content'
    ];

    function activateStepForced(id) {
      activateStep(id, { forceScroll: true });
    }

    function scrollStepIntoCanvas(id) {
      if (
        document.body.classList.contains('proto-edit-mode') ||
        document.body.classList.contains('proto-revision-mode')
      ) {
        return;
      }
      const target = document.getElementById(id);
      if (!target) return;
      const anchor = target.querySelector(':scope > .step-header') || target;
      anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function getMainGeneratedArea() {
      return (
        document.getElementById('proto-generated-area') ||
        document.querySelector('main.proto-page > .proto-generated-area') ||
        document.querySelector('main.proto-page .proto-generated-area')
      );
    }

    function queryMainGenerated(selector) {
      return getMainGeneratedArea()?.querySelector(selector) || null;
    }

    function queryAllMainGenerated(selector) {
      const area = getMainGeneratedArea();
      return area ? [...area.querySelectorAll(selector)] : [];
    }

    function activateStep(id, opts) {
      const options = opts && typeof opts === 'object' ? opts : {};
      const forceScroll = options.forceScroll === true;
      const suppressScroll = options.suppressScroll === true;
      const prevActiveId = queryMainGenerated('.journey-step.is-active[id]')?.id || null;
      queryAllMainGenerated('.journey-step').forEach((step) => step.classList.remove('is-active'));
      const target = document.getElementById(id);
      if (target) {
        target.classList.add('is-active');
        if (document.body.classList.contains('proto-prd-mode')) {
          focusPrdStep(target);
          collapseProtoNavDock();
          if (document.body.classList.contains('proto-spotlight-open')) refreshProtoStepSpotlightMountIfOpen();
        } else {
          const authoring =
            document.body.classList.contains('proto-edit-mode') || document.body.classList.contains('proto-revision-mode');
          const skipAutoCanvasScroll = authoring && !forceScroll;
          if (!suppressScroll && !skipAutoCanvasScroll && prevActiveId !== id) scrollStepIntoCanvas(id);
        }
      }
      setProtoNavActive(id);
      suppressProtoNavViewportSyncBriefly();
      scheduleAnnotationLayout();
    }

    function scrollProtoTarget(id) {
      activateStep(id);
    }

    /** 演讲模式下半页锁定：目录切换不能只依赖页级滚动 */
    function focusPrdStep(step) {
      const area = getMainGeneratedArea();
      if (!document.body.classList.contains('proto-prd-mode')) return;
      if (!step) {
        if (area) area.dataset.prdEmpty = 'true';
        return;
      }
      if (area) delete area.dataset.prdEmpty;
      clearPrdFocusStep();
      queryAllMainGenerated('.journey-step').forEach((s) => s.classList.remove('is-active'));
      step.classList.add('is-active');
      step.classList.add('is-prd-focus');
      step.closest('.journey-row')?.classList.add('is-prd-row-focus');
      setProtoNavActive(step.id);
      suppressProtoNavViewportSyncBriefly();
      fitPrdFocusStep(step);
      scheduleAnnotationLayout();
    }

    function collapseProtoNavDock() {
      const dock = document.getElementById('proto-nav-dock');
      const trigger = document.getElementById('proto-nav-trigger');
      const scroll = document.getElementById('proto-nav-scroll');
      if (!dock || !trigger) return;
      const ae = document.activeElement;
      if (ae && scroll && scroll.contains(ae)) ae.blur();
      dock.classList.remove('is-open');
      trigger.setAttribute('aria-expanded', 'false');
    }

    /** 点击目录后与滚动对齐短暂停权，减轻 smooth scroll 抖动 */
    let __protoNavScrollSuppressUntil = 0;

    function suppressProtoNavViewportSyncBriefly() {
      __protoNavScrollSuppressUntil = performance.now() + 720;
    }

    function setProtoNavActive(id) {
      const nav = document.getElementById('proto-nav-scroll');
      if (!nav || !id) return;
      nav.querySelectorAll('.proto-nav-link[data-proto-nav-target]').forEach((btn) => {
        const on = btn.dataset.protoNavTarget === id;
        btn.classList.toggle('is-active', on);
        if (on) btn.setAttribute('aria-current', 'location');
        else btn.removeAttribute('aria-current');
      });
    }

    function pickVisibleJourneyStepId() {
      if (document.body.classList.contains('proto-prd-mode')) {
        const focused = queryMainGenerated('.journey-step.is-prd-focus[id]');
        if (focused) return focused.id;
        const active = queryMainGenerated('.journey-step.is-active[id]');
        if (active) return active.id;
        const fallback = queryMainGenerated('.journey-step[id]');
        return fallback ? fallback.id : null;
      }
      const steps = queryAllMainGenerated('.journey-step[id]');
      if (!steps.length) return null;
      const marginTop = Math.min(180, window.innerHeight * 0.22);
      let currentId = steps[0].id;
      for (const el of steps) {
        const top = el.getBoundingClientRect().top;
        if (top <= marginTop) currentId = el.id;
      }
      return currentId;
    }

    function syncProtoNavActiveWithViewport() {
      if (performance.now() < __protoNavScrollSuppressUntil) return;
      const id = pickVisibleJourneyStepId();
      if (id) setProtoNavActive(id);
    }

    let __protoOutlineNavViewportBound = false;
    let __protoNavDockAriaBound = false;

    function bindProtoOutlineNavViewport() {
      if (__protoOutlineNavViewportBound) return;
      __protoOutlineNavViewportBound = true;
      let raf = null;
      const schedule = () => {
        if (raf != null) return;
        raf = requestAnimationFrame(() => {
          raf = null;
          syncProtoNavActiveWithViewport();
        });
      };
      window.addEventListener('scroll', schedule, { passive: true });
      window.addEventListener('resize', schedule);
    }

    function toggleSkillSheet(show) {
      const sheet = document.getElementById('skill-sheet');
      if (!sheet) return;
      sheet.classList.toggle('hidden', !show);
    }

    function showToast(message) {
      const toast = document.getElementById('toast');
      toast.textContent = message || 'Toast';
      toast.classList.remove('hidden');
      window.clearTimeout(window.__toastTimer);
      window.__toastTimer = window.setTimeout(() => toast.classList.add('hidden'), 2200);
    }

    function createProtoDiagnostics() {
      const entries = [];
      const maxEntries = 240;
      let visible = new URLSearchParams(window.location.search).get('protoDebug') === '1';
      let button = null;

      function currentMode() {
        const modes = [];
        if (document.body.classList.contains('proto-prd-mode')) modes.push('prd');
        if (document.body.classList.contains('proto-edit-mode')) modes.push('text_edit');
        if (document.body.classList.contains('proto-revision-mode')) modes.push('revision');
        if (document.body.classList.contains('proto-excalidraw-edit-mode')) modes.push('sketch_edit');
        if (document.body.classList.contains('proto-spotlight-open')) modes.push('spotlight');
        return modes.length ? modes.join(',') : 'canvas';
      }

      function activeStepInfo() {
        const active =
          document.querySelector('.journey-step.is-active[data-proto-id]') ||
          document.querySelector('.journey-step.is-prd-focus[data-proto-id]');
        if (!active) return null;
        return {
          id: active.dataset.protoId || active.id || null,
          label: active.dataset.protoLabel || active.querySelector('.step-title')?.textContent?.trim() || null
        };
      }

      function normalizePayload(payload) {
        if (!payload || typeof payload !== 'object') return payload ?? null;
        try {
          return JSON.parse(
            JSON.stringify(payload, (key, value) => {
              if (typeof value === 'function') return undefined;
              if (value instanceof Error) {
                return { name: value.name, message: value.message, stack: value.stack };
              }
              if (value instanceof Element) {
                return {
                  tag: value.tagName,
                  id: value.id || null,
                  className: typeof value.className === 'string' ? value.className : null
                };
              }
              if (typeof value === 'string' && value.length > 1200) return `${value.slice(0, 1200)}...<truncated>`;
              return value;
            })
          );
        } catch (error) {
          return { serialization_error: error?.message || String(error) };
        }
      }

      function ensureButton() {
        if (button || !document.body) return button;
        button = document.createElement('button');
        button.type = 'button';
        button.id = 'proto-diagnostics-copy';
        button.className = 'proto-diagnostics-copy hidden';
        button.textContent = '复制调试日志';
        button.addEventListener('click', () => copy());
        document.body.appendChild(button);
        updateButton();
        return button;
      }

      function updateButton() {
        if (!button) return;
        button.classList.toggle('hidden', !visible);
      }

      function reveal(reason) {
        visible = true;
        ensureButton();
        updateButton();
        if (reason) add('diagnostics_revealed', { reason });
      }

      function add(event, payload, level = 'info') {
        entries.push({
          ts: new Date().toISOString(),
          level,
          event,
          mode: currentMode(),
          activeStep: activeStepInfo(),
          payload: normalizePayload(payload)
        });
        while (entries.length > maxEntries) entries.shift();
      }

      function error(event, err, payload) {
        add(
          event,
          {
            ...(payload && typeof payload === 'object' ? payload : {}),
            error: {
              name: err?.name || null,
              message: err?.message || String(err),
              stack: err?.stack || null
            }
          },
          'error'
        );
        reveal(event);
      }

      function report() {
        return {
          schema_version: 1,
          generated_at: new Date().toISOString(),
          page: {
            url: window.location.href,
            title: document.title,
            userAgent: navigator.userAgent,
            prototypeKind: document.body?.dataset?.prototypeKind || null
          },
          state: {
            mode: currentMode(),
            activeStep: activeStepInfo(),
            entryCount: entries.length
          },
          entries: [...entries]
        };
      }

      async function copy() {
        const text = JSON.stringify(report(), null, 2);
        try {
          await navigator.clipboard.writeText(text);
          showToast('已复制调试日志');
        } catch (_error) {
          window.prompt('复制调试日志', text);
        }
      }

      window.addEventListener('error', (event) => {
        error('window_error', event.error || new Error(event.message || 'window error'), {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno
        });
      });
      window.addEventListener('unhandledrejection', (event) => {
        error('unhandled_rejection', event.reason || new Error('unhandled rejection'));
      });
      document.addEventListener('keydown', (event) => {
        if (event.ctrlKey && event.altKey && event.key.toLowerCase() === 'd') {
          event.preventDefault();
          reveal('keyboard');
        }
      });
      if (visible) window.setTimeout(() => reveal('query'), 0);
      window.addEventListener('DOMContentLoaded', () => ensureButton(), { once: true });

      return {
        add,
        event: add,
        error,
        reveal,
        report,
        copy,
        export: report
      };
    }

    window.ProtoPilotDiagnostics = window.ProtoPilotDiagnostics || createProtoDiagnostics();

    function showDialog() {
      document.getElementById('dialog').classList.remove('hidden');
    }

    function hideDialog() {
      document.getElementById('dialog').classList.add('hidden');
    }

    function toggleAnnotations() {
      const hidden = !document.body.classList.contains('hide-annotations');
      document.body.classList.toggle('hide-annotations', hidden);
      scheduleAnnotationLayout();
      updateAnnotationButton();
      persistUiState();
    }

    function annotationsOverlap(a, b) {
      return !(
        a.right <= b.left ||
        a.left >= b.right ||
        a.bottom <= b.top ||
        a.top >= b.bottom
      );
    }

    function layoutAnnotations() {
      document.querySelectorAll('.proto-generated-area .annotation').forEach((annotation) => {
        annotation.style.removeProperty('--proto-annotation-shift-x');
        annotation.style.removeProperty('--proto-annotation-shift-y');
      });
      if (document.body.classList.contains('hide-annotations')) return;

      document.querySelectorAll('.proto-generated-area .journey-step').forEach((step) => {
        const annotations = [...step.querySelectorAll('.annotation')].filter((annotation) => {
          const style = window.getComputedStyle(annotation);
          return style.display !== 'none' && style.visibility !== 'hidden';
        });
        const placed = [];
        annotations.forEach((annotation) => {
          let shiftY = 0;
          for (let tries = 0; tries < 8; tries += 1) {
            annotation.style.setProperty('--proto-annotation-shift-y', `${shiftY}px`);
            const rect = annotation.getBoundingClientRect();
            const hit = placed.some((other) => annotationsOverlap(rect, other));
            if (!hit) {
              placed.push(rect);
              return;
            }
            shiftY += 18;
          }
          placed.push(annotation.getBoundingClientRect());
        });
      });
    }

    function scheduleAnnotationLayout() {
      if (annotationLayoutRaf !== null) cancelAnimationFrame(annotationLayoutRaf);
      annotationLayoutRaf = requestAnimationFrame(() => {
        annotationLayoutRaf = null;
        layoutAnnotations();
      });
    }

    function readUiState() {
      try {
        return JSON.parse(localStorage.getItem(protoStateKey) || '{}') || {};
      } catch (error) {
        return {};
      }
    }

    function persistUiState() {
      const state = {
        annotationsHidden: document.body.classList.contains('hide-annotations'),
        prdFontStepIndex,
        prdFontVersion: 2
      };
      try {
        localStorage.setItem(protoStateKey, JSON.stringify(state));
      } catch (error) {}
    }

    /** PRD / 宣讲台三处控件 id，需与 `.proto-float-btn.proto-float-btn--symbol` 样式一致维护 */
    const ANNOTATION_BUTTON_IDS = [
      'annotation-toggle',
      'annotation-toggle-prd',
      'annotation-toggle-spotlight'
    ];

    /** 演讲光标：常显光球 + 按住绘制轨迹；默认关；不参与 localStorage（applyUiState 会强制关闭）。 */
    const LASER_BUTTON_IDS = [
      'presentation-laser-toggle',
      'presentation-laser-toggle-prd',
      'presentation-laser-toggle-spotlight'
    ];
    let laserOverlayEl = null;
    let laserSvg = null;
    let laserPath = null;
    let laserCursorEl = null;
    const laserTrails = [];
    let currentLaserTrail = null;
    let laserPointerId = null;
    const laserCursor = { x: 0, y: 0, visible: false };
    let laserRafId = null;
    let laserResizeTimer = null;

    function ensureLaserOverlay() {
      const existing = document.getElementById('proto-laser-overlay');
      if (existing) {
        laserOverlayEl = existing;
        laserSvg = laserOverlayEl.querySelector('svg.proto-laser-svg');
        laserPath = laserOverlayEl.querySelector('path.proto-laser-path');
        laserCursorEl = laserOverlayEl.querySelector('.proto-laser-cursor');
        return;
      }
      const svgNs = 'http://www.w3.org/2000/svg';
      laserOverlayEl = document.createElement('div');
      laserOverlayEl.id = 'proto-laser-overlay';
      laserOverlayEl.className = 'proto-laser-overlay';
      laserOverlayEl.setAttribute('aria-hidden', 'true');
      laserSvg = document.createElementNS(svgNs, 'svg');
      laserSvg.classList.add('proto-laser-svg');
      laserSvg.setAttribute('focusable', 'false');
      const defs = document.createElementNS(svgNs, 'defs');
      const filter = document.createElementNS(svgNs, 'filter');
      filter.setAttribute('id', 'proto-laser-glow');
      filter.setAttribute('x', '-100%');
      filter.setAttribute('y', '-100%');
      filter.setAttribute('width', '300%');
      filter.setAttribute('height', '300%');
      const blurSoft = document.createElementNS(svgNs, 'feGaussianBlur');
      blurSoft.setAttribute('stdDeviation', '2.2');
      blurSoft.setAttribute('result', 'soft');
      const blurGlow = document.createElementNS(svgNs, 'feGaussianBlur');
      blurGlow.setAttribute('stdDeviation', '6');
      blurGlow.setAttribute('result', 'glow');
      const merge = document.createElementNS(svgNs, 'feMerge');
      ['glow', 'soft', 'SourceGraphic'].forEach((input) => {
        const node = document.createElementNS(svgNs, 'feMergeNode');
        node.setAttribute('in', input);
        merge.appendChild(node);
      });
      filter.append(blurSoft, blurGlow, merge);
      defs.appendChild(filter);
      laserPath = document.createElementNS(svgNs, 'path');
      laserPath.classList.add('proto-laser-path');
      laserPath.setAttribute('filter', 'url(#proto-laser-glow)');
      laserSvg.append(defs, laserPath);
      laserCursorEl = document.createElement('div');
      laserCursorEl.className = 'proto-laser-cursor';
      laserOverlayEl.append(laserSvg, laserCursorEl);
      document.body.appendChild(laserOverlayEl);
    }

    function fitLaserCanvas() {
      ensureLaserOverlay();
      const w = window.innerWidth || 0;
      const h = window.innerHeight || 0;
      if (w <= 0 || h <= 0) return;
      if (laserSvg) laserSvg.setAttribute('viewBox', `0 0 ${w} ${h}`);
      if (document.documentElement.classList.contains('proto-laser-pointer-on')) ensureLaserAnimationFrame();
    }

    function scheduleLaserFit() {
      window.clearTimeout(laserResizeTimer);
      laserResizeTimer = window.setTimeout(fitLaserCanvas, 60);
    }

    function laserEventAllowed(ev) {
      if (!document.documentElement.classList.contains('proto-laser-pointer-on')) return false;
      if (document.body.classList.contains('proto-edit-mode')) return false;
      if (document.body.classList.contains('proto-revision-mode')) return false;
      if (document.body.classList.contains('proto-excalidraw-edit-mode')) return false;
      if (ev?.target?.closest?.('button, a[href], input, textarea, select, [contenteditable="true"], label, .excalidraw-editor-modal, .proto-prd-backdrop')) return false;
      return true;
    }

    function updateLaserCursor(clientX, clientY) {
      laserCursor.x = clientX;
      laserCursor.y = clientY;
      laserCursor.visible = true;
      ensureLaserAnimationFrame();
    }

    function laserPrimaryRgb() {
      return getComputedStyle(document.documentElement).getPropertyValue('--proto-primary-rgb').trim() || '69, 125, 239';
    }

    function pushLaserPoint(clientX, clientY) {
      if (!currentLaserTrail) return;
      const t = performance.now();
      const last = currentLaserTrail.points[currentLaserTrail.points.length - 1];
      if (last && Math.hypot(clientX - last.x, clientY - last.y) < 2) return;
      const point = last
        ? { x: last.x * 0.62 + clientX * 0.38, y: last.y * 0.62 + clientY * 0.38, t }
        : { x: clientX, y: clientY, t };
      currentLaserTrail.points.push(point);
      if (currentLaserTrail.points.length > 220) currentLaserTrail.points.shift();
      ensureLaserAnimationFrame();
    }

    function onLaserPointerDown(ev) {
      if (ev.button != null && ev.button !== 0) return;
      if (!laserEventAllowed(ev)) return;
      laserPointerId = ev.pointerId;
      currentLaserTrail = { points: [], doneAt: 0 };
      laserTrails.push(currentLaserTrail);
      updateLaserCursor(ev.clientX, ev.clientY);
      pushLaserPoint(ev.clientX, ev.clientY);
      ev.preventDefault();
    }

    function onLaserPointerMove(ev) {
      if (!document.documentElement.classList.contains('proto-laser-pointer-on')) return;
      updateLaserCursor(ev.clientX, ev.clientY);
      if (currentLaserTrail && (laserPointerId == null || ev.pointerId === laserPointerId)) {
        const events = typeof ev.getCoalescedEvents === 'function' ? ev.getCoalescedEvents() : [ev];
        events.forEach((item) => pushLaserPoint(item.clientX, item.clientY));
      }
    }

    function onLaserPointerUp(ev) {
      if (laserPointerId != null && ev.pointerId !== laserPointerId) return;
      if (currentLaserTrail) currentLaserTrail.doneAt = performance.now();
      currentLaserTrail = null;
      laserPointerId = null;
      ensureLaserAnimationFrame();
    }

    function onLaserPointerLeave() {
      if (currentLaserTrail) currentLaserTrail.doneAt = performance.now();
      currentLaserTrail = null;
      laserPointerId = null;
      laserCursor.visible = false;
      ensureLaserAnimationFrame();
    }

    function stopLaserFrameLoop() {
      if (laserRafId != null) {
        cancelAnimationFrame(laserRafId);
        laserRafId = null;
      }
    }

    function ensureLaserAnimationFrame() {
      if (!document.documentElement.classList.contains('proto-laser-pointer-on')) return;
      if (laserRafId != null) return;
      laserRafId = requestAnimationFrame(laserFrameLoop);
    }

    function laserFrameLoop() {
      laserRafId = null;
      if (!document.documentElement.classList.contains('proto-laser-pointer-on')) return;
      drawLaserFrame();
    }

    function laserSmoothPath(points) {
      if (!points.length) return '';
      if (points.length === 1) return `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
      let d = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
      for (let i = 1; i < points.length - 1; i += 1) {
        const p = points[i];
        const next = points[i + 1];
        const mx = (p.x + next.x) / 2;
        const my = (p.y + next.y) / 2;
        d += ` Q ${p.x.toFixed(2)} ${p.y.toFixed(2)} ${mx.toFixed(2)} ${my.toFixed(2)}`;
      }
      const last = points[points.length - 1];
      d += ` L ${last.x.toFixed(2)} ${last.y.toFixed(2)}`;
      return d;
    }

    function drawLaserFrame() {
      if (!laserPath || !laserCursorEl) return;
      const now = performance.now();
      const primaryRgb = laserPrimaryRgb();
      laserTrails.forEach((trail) => {
        trail.points = trail.points.filter((p) => now - p.t < 900);
      });
      for (let trailIndex = laserTrails.length - 1; trailIndex >= 0; trailIndex -= 1) {
        if (!laserTrails[trailIndex].points.length && laserTrails[trailIndex] !== currentLaserTrail) {
          laserTrails.splice(trailIndex, 1);
        }
      }
      const paths = [];
      let maxLife = 0;
      laserTrails.forEach((trail) => {
        const pts = trail.points;
        if (pts.length < 2) return;
        const latest = pts[pts.length - 1]?.t || now;
        const life = Math.max(0, 1 - (now - latest) / 900);
        maxLife = Math.max(maxLife, life);
        paths.push(laserSmoothPath(pts));
      });
      laserPath.setAttribute('d', paths.join(' '));
      laserPath.setAttribute('stroke', `rgb(${primaryRgb})`);
      laserPath.setAttribute('stroke-opacity', String(Math.min(0.9, 0.2 + maxLife * 0.62)));
      laserPath.setAttribute('stroke-width', '3.2');
      laserPath.setAttribute('stroke-linecap', 'round');
      laserPath.setAttribute('stroke-linejoin', 'round');
      laserPath.setAttribute('fill', 'none');
      if (laserCursor.visible) {
        const head = laserCursor;
        laserCursorEl.style.setProperty('--proto-laser-rgb', primaryRgb);
        laserCursorEl.style.transform = `translate(${head.x}px, ${head.y}px)`;
        laserCursorEl.classList.add('is-visible');
      } else {
        laserCursorEl.classList.remove('is-visible');
      }

      if (
        document.documentElement.classList.contains('proto-laser-pointer-on') &&
        (laserCursor.visible || laserTrails.length > 0)
      ) {
        laserRafId = requestAnimationFrame(laserFrameLoop);
      }
    }

    function updatePresentationLaserButtons() {
      const on = document.documentElement.classList.contains('proto-laser-pointer-on');
      const titleOff = '演讲光标：已关闭（点按开启高光与拖尾）';
      const titleOn = '演讲光标：已开启（点按关闭）';
      LASER_BUTTON_IDS.forEach((id) => {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.classList.toggle('is-active', on);
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        btn.title = on ? titleOn : titleOff;
      });
    }

    function teardownPresentationLaserInternal() {
      document.documentElement.classList.remove('proto-laser-pointer-on');
      document.removeEventListener('pointerdown', onLaserPointerDown);
      document.removeEventListener('pointermove', onLaserPointerMove);
      document.removeEventListener('pointerup', onLaserPointerUp);
      document.removeEventListener('pointercancel', onLaserPointerUp);
      document.removeEventListener('pointerleave', onLaserPointerLeave);
      window.removeEventListener('blur', onLaserPointerLeave);
      window.removeEventListener('resize', scheduleLaserFit, { passive: true });
      stopLaserFrameLoop();
      laserTrails.length = 0;
      currentLaserTrail = null;
      laserPointerId = null;
      laserCursor.visible = false;
      window.clearTimeout(laserResizeTimer);
      laserResizeTimer = null;
      if (laserPath) laserPath.setAttribute('d', '');
      if (laserCursorEl) laserCursorEl.classList.remove('is-visible');
      updatePresentationLaserButtons();
    }

    function togglePresentationLaser(force) {
      const prev = document.documentElement.classList.contains('proto-laser-pointer-on');
      const next = typeof force === 'boolean' ? force : !prev;
      if (prev === next) {
        updatePresentationLaserButtons();
        return;
      }
      if (!next) {
        teardownPresentationLaserInternal();
        if (window.lucide) window.lucide.createIcons();
        return;
      }
      ensureLaserOverlay();
      fitLaserCanvas();
      document.documentElement.classList.add('proto-laser-pointer-on');
      document.addEventListener('pointerdown', onLaserPointerDown, { passive: false });
      document.addEventListener('pointermove', onLaserPointerMove, { passive: true });
      document.addEventListener('pointerup', onLaserPointerUp, { passive: true });
      document.addEventListener('pointercancel', onLaserPointerUp, { passive: true });
      document.addEventListener('pointerleave', onLaserPointerLeave, { passive: true });
      window.addEventListener('blur', onLaserPointerLeave, { passive: true });
      window.addEventListener('resize', scheduleLaserFit, { passive: true });
      stopLaserFrameLoop();
      laserTrails.length = 0;
      currentLaserTrail = null;
      laserPointerId = null;
      laserCursor.visible = false;
      updatePresentationLaserButtons();
      if (window.lucide) window.lucide.createIcons();
    }

    function applyUiState() {
      teardownPresentationLaserInternal();
      const state = readUiState();
      if (state.prdFontVersion === 2 && typeof state.prdFontStepIndex === 'number' && Number.isFinite(state.prdFontStepIndex)) {
        prdFontStepIndex = clampPrdFontIndex(Math.round(state.prdFontStepIndex));
      }
      applyPrdViewerFontScale();
      document.body.classList.remove('proto-prd-mode');
      document.body.classList.toggle('hide-annotations', Boolean(state.annotationsHidden));
      document.body.classList.remove('hide-frame-guide');
      clearPrdFocusStep();
      restoreProtoSpotlightSource();
      document.body.classList.remove('proto-spotlight-open');
      document.getElementById('proto-step-spotlight')?.classList.add('hidden');
      document.getElementById('proto-spotlight-mount')?.replaceChildren();
      updateAnnotationButton();
      updatePresentationLaserButtons();
      syncPresenterChromeAria();
      updateChromeModeButtons();
      if (window.lucide) window.lucide.createIcons();
    }

    function updateAnnotationButton() {
      const hidden = document.body.classList.contains('hide-annotations');
      const titleHidden = '标注：已隐藏（未高亮）；点此显示标注';
      const titleShown = '标注：已显示（高亮）；点此隐藏标注';
      ANNOTATION_BUTTON_IDS.forEach((buttonId) => {
        const btn = document.getElementById(buttonId);
        if (!btn) return;
        btn.classList.toggle('is-active', !hidden);
        btn.setAttribute('aria-pressed', hidden ? 'false' : 'true');
        btn.title = hidden ? titleHidden : titleShown;
      });
    }

    function syncPresenterChromeAria() {
      const rail = document.getElementById('proto-prd-proto-rail-wrap');
      if (!rail) return;
      rail.setAttribute('aria-hidden', document.body.classList.contains('proto-prd-mode') ? 'false' : 'true');
    }

    function updateChromeModeButtons() {
      const prdBtn = document.getElementById('float-prd-btn');
      const editBtn = document.getElementById('float-edit-btn');
      const revBtn = document.getElementById('float-revision-btn');
      const mainToolbar = document.getElementById('proto-main-toolbar');
      const editToolbar = document.getElementById('proto-edit-toolbar');
      const revisionToolbar = document.getElementById('proto-revision-toolbar');
      const saveBtn = document.getElementById('proto-edit-save-btn');
      const prdActive = document.body.classList.contains('proto-prd-mode');
      const editActive = document.body.classList.contains('proto-edit-mode');
      const revActive = document.body.classList.contains('proto-revision-mode');
      const sketchActive = document.body.classList.contains('proto-excalidraw-edit-mode');
      if (mainToolbar) mainToolbar.classList.toggle('hidden', editActive || revActive || sketchActive);
      if (editToolbar) editToolbar.classList.toggle('hidden', !editActive);
      if (revisionToolbar) revisionToolbar.classList.add('hidden');
      if (saveBtn) saveBtn.disabled = editSessionSaving;
      if (prdBtn) {
        prdBtn.classList.toggle('is-active', prdActive);
        prdBtn.setAttribute('aria-pressed', prdActive ? 'true' : 'false');
        prdBtn.title = prdActive ? '退出 PRD 演讲模式' : '进入 PRD 演讲模式';
      }
      if (editBtn) {
        editBtn.classList.toggle('is-active', editActive);
        editBtn.setAttribute('aria-pressed', editActive ? 'true' : 'false');
        editBtn.title = editActive ? '退出改文字' : '改文字';
      }
      if (revBtn) {
        revBtn.classList.toggle('is-active', revActive);
        revBtn.setAttribute('aria-pressed', revActive ? 'true' : 'false');
      }
    }

    function buildProtoOutlineNav() {
      const scroll = document.getElementById('proto-nav-scroll');
      const area = getMainGeneratedArea();
      if (!scroll || !area) return;
      scroll.textContent = '';

      /** 仅在有 `section-divider` 且文案非空时插入分组标题，避免首段步骤前出现虚构标签 */
      let groupHeading = '';
      let groupBannerAllowed = false;
      let emittedGroupBanner = false;

      function sanitizeHeading(text) {
        return String(text || '')
          .replace(/\s+/g, ' ')
          .trim();
      }

      function ensureGroupBanner() {
        if (emittedGroupBanner) return;
        emittedGroupBanner = true;
        if (!groupBannerAllowed || !groupHeading) return;
        const label = document.createElement('div');
        label.className = 'proto-nav-group-label';
        label.textContent = groupHeading;
        scroll.appendChild(label);
      }

      function addStepLink(stepEl) {
        const id = stepEl.id;
        if (!id) return;
        ensureGroupBanner();

        const titleEl = stepEl.querySelector(':scope > .step-header .step-title');
        const numEl = stepEl.querySelector(':scope > .step-header .step-number');
        const captionEl = stepEl.querySelector(':scope > .branch-caption');

        const num = (numEl?.textContent || '').trim();
        const titleRaw = sanitizeHeading(titleEl?.textContent || stepEl.dataset.protoLabel || '');
        const subtitle = sanitizeHeading(captionEl?.textContent || '');

        let label = `${num ? `${num}. ` : ''}${titleRaw || id}`;
        if (subtitle) label += ` · ${subtitle}`;

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'proto-nav-link';
        btn.dataset.protoNavTarget = id;
        btn.textContent = label;
        btn.addEventListener('click', () => scrollProtoTarget(id));
        scroll.appendChild(btn);
      }

      const flow = [...area.children].filter((el) => !el.matches('.proto-area-label'));
      for (const node of flow) {
        if (node.classList.contains('section-divider')) {
          const next = sanitizeHeading(node.textContent);
          groupHeading = next;
          groupBannerAllowed = Boolean(next);
          emittedGroupBanner = false;
          continue;
        }
        if (!node.classList.contains('journey-row')) continue;
        node.querySelectorAll(':scope > .journey-step[id]').forEach(addStepLink);
      }
      bindProtoOutlineNavViewport();
      syncProtoNavActiveWithViewport();
    }

    function wireProtoNavDockAria() {
      if (__protoNavDockAriaBound) return;
      const dock = document.getElementById('proto-nav-dock');
      const trigger = document.getElementById('proto-nav-trigger');
      const sheet = dock?.querySelector('.proto-nav-sheet');
      if (!dock || !trigger) return;
      __protoNavDockAriaBound = true;
      const expand = () => {
        dock.classList.add('is-open');
        trigger.setAttribute('aria-expanded', 'true');
      };
      trigger.addEventListener('mouseenter', expand);
      trigger.addEventListener('focus', expand);
      sheet?.addEventListener('mouseenter', expand);
      dock.addEventListener('mouseleave', collapseProtoNavDock);
      dock.addEventListener('focusout', (event) => {
        if (!dock.contains(event.relatedTarget)) collapseProtoNavDock();
      });
    }

    function togglePrdViewer(force, opts) {
      const options = opts && typeof opts === 'object' ? opts : {};
      const suppressResumeScroll = options.suppressResumeScroll === true;

      const drawer = document.getElementById('prd-drawer');
      if (!drawer) return false;
      const enabled = typeof force === 'boolean' ? force : !drawer.classList.contains('is-open');
      if (enabled) {
        toggleProtoStepSpotlight(false);
        if (document.body.classList.contains('proto-edit-mode') && !toggleEditMode(false)) return false;
        if (document.body.classList.contains('proto-revision-mode')) toggleRevisionMode(false);
        drawer.classList.add('is-open');
        document.body.classList.add('proto-prd-mode');
        setPrdFocusStep();
        initPrdViewer(true);
      } else {
        toggleProtoStepSpotlight(false);
        const wasPrd = document.body.classList.contains('proto-prd-mode');
        const resumeId = wasPrd
          ? queryMainGenerated('.journey-step.is-prd-focus[id]')?.id ||
            queryMainGenerated('.journey-step.is-active[id]')?.id ||
            null
          : null;
        clearPrdFocusStep();
        drawer.classList.remove('is-open');
        document.body.classList.remove('proto-prd-mode');
        if (wasPrd && resumeId && !suppressResumeScroll) {
          requestAnimationFrame(() => {
            const el = document.getElementById(resumeId);
            if (!el) return;
            suppressProtoNavViewportSyncBriefly();
            const anchor = el.querySelector(':scope > .step-header') || el;
            const rect = anchor.getBoundingClientRect();
            const headerVisibleEnough = rect.top >= 10 && rect.top < window.innerHeight * 0.72;
            if (!headerVisibleEnough) anchor.scrollIntoView({ behavior: 'auto', block: 'start' });
          });
        }
      }
      syncPresenterChromeAria();
      updateChromeModeButtons();
      updatePresentationLaserButtons();
      if (window.lucide) window.lucide.createIcons();
      return true;
    }

    function clearPrdFocusStep() {
      const area = getMainGeneratedArea();
      if (area) delete area.dataset.prdEmpty;
      document.querySelectorAll('.is-prd-focus').forEach((element) => {
        element.classList.remove('is-prd-focus');
        element.style.removeProperty('--proto-prd-preview-scale');
      });
      document.querySelectorAll('.is-prd-row-focus').forEach((element) => element.classList.remove('is-prd-row-focus'));
    }

    function setPrdFocusStep() {
      const visibleId = pickVisibleJourneyStepId();
      const step = (visibleId && document.getElementById(visibleId)) || queryMainGenerated('.journey-step');
      focusPrdStep(step);
    }

    function fitPrdFocusStep(step = document.querySelector('.journey-step.is-prd-focus')) {
      const preview = getMainGeneratedArea();
      if (!step || !preview) return;
      step.style.setProperty('--proto-prd-preview-scale', '1');
      requestAnimationFrame(() => {
        const available = preview.getBoundingClientRect();
        const rect = step.getBoundingClientRect();
        if (!available.width || !available.height || !rect.width || !rect.height) return;
        /** 仅用宽度推导缩放：超高界面保持可读宽度，纵向在左侧 `.proto-page` 内滚动 */
        const pad = 14;
        let scale = (available.width - pad * 2) / rect.width;
        scale = Math.min(1, scale);
        scale = Math.max(0.24, Math.min(scale, 1));
        step.style.setProperty('--proto-prd-preview-scale', scale.toFixed(3));
      });
    }

    function pickSpotlightSourceStep() {
      let step =
        queryMainGenerated('.journey-step.is-prd-focus[id]') ||
        queryMainGenerated('.journey-step.is-active[id]');
      if (!step) {
        const id = pickVisibleJourneyStepId();
        step = id ? document.getElementById(id) : null;
      }
      return step || queryMainGenerated('.journey-step[id]');
    }

    function restoreProtoSpotlightSource() {
      const mount = document.getElementById('proto-spotlight-mount');
      mount?.replaceChildren();
      spotlightMountedStep = null;
      spotlightPlaceholder = null;
      spotlightOriginalState = null;
      spotlightBaseScale = 1;
      spotlightUserZoom = 1;
    }

    function mountProtoSpotlightSource(src, mount) {
      if (!src || !mount) return;
      if (spotlightMountedStep?.dataset?.protoSpotlightSourceId === src.id) return;
      restoreProtoSpotlightSource();
      const clone = src.cloneNode(true);
      clone.classList.remove('is-prd-focus');
      clone.classList.add('is-spotlight-live');
      clone.style.removeProperty('--proto-prd-preview-scale');
      clone.dataset.protoSpotlightSourceId = src.id || '';
      mount.replaceChildren(clone);
      spotlightMountedStep = clone;
      spotlightUserZoom = 1;
    }

    function refreshProtoStepSpotlightMountIfOpen() {
      if (!document.body.classList.contains('proto-spotlight-open')) return;
      const mount = document.getElementById('proto-spotlight-mount');
      if (!mount) return;
      const src = pickSpotlightSourceStep();
      if (!src) return;
      mountProtoSpotlightSource(src, mount);
      fitSpotlightMount();
      scheduleAnnotationLayout();
      if (window.lucide) window.lucide.createIcons();
    }

    function fitSpotlightMount() {
      const mount = document.getElementById('proto-spotlight-mount');
      const stage = document.getElementById('proto-spotlight-stage');
      const kid = mount?.firstElementChild;
      if (!mount || !stage || !kid) return;
      mount.style.setProperty('--proto-spotlight-scale', '1');
      requestAnimationFrame(() => {
        const box = stage.getBoundingClientRect();
        const rect = kid.getBoundingClientRect();
        if (!box.width || !box.height || !rect.width || !rect.height) return;
        const pad = 22;
        let scale = (box.width - pad * 2) / rect.width;
        scale = Math.min(1, scale);
        scale = Math.max(0.18, Math.min(scale, 1));
        spotlightBaseScale = scale;
        applySpotlightScale();
      });
    }

    function applySpotlightScale() {
      const mount = document.getElementById('proto-spotlight-mount');
      if (!mount) return;
      const scale = Math.max(0.12, Math.min(3, spotlightBaseScale * spotlightUserZoom));
      mount.style.setProperty('--proto-spotlight-scale', scale.toFixed(3));
    }

    function handleSpotlightWheel(event) {
      if (!document.body.classList.contains('proto-spotlight-open')) return;
      const stage = document.getElementById('proto-spotlight-stage');
      if (!stage || !stage.contains(event.target)) return;
      event.preventDefault();
      const next = spotlightUserZoom * Math.exp(-event.deltaY * 0.0015);
      spotlightUserZoom = Math.max(0.55, Math.min(2.8, next));
      applySpotlightScale();
    }

    function toggleProtoStepSpotlight(force, options) {
      const opts = options && typeof options === 'object' ? options : {};
      const root = document.getElementById('proto-step-spotlight');
      const mount = document.getElementById('proto-spotlight-mount');
      if (!root || !mount) return;

      let nextOpen;
      if (typeof force === 'boolean') nextOpen = force;
      else nextOpen = root.classList.contains('hidden');

      if (!nextOpen) {
        restoreProtoSpotlightSource();
        mount.replaceChildren();
        root.classList.add('hidden');
        document.body.classList.remove('proto-spotlight-open');
        syncPresenterChromeAria();
        updateAnnotationButton();
        updatePresentationLaserButtons();
        if (window.lucide) window.lucide.createIcons();
        return;
      }

      if (!document.body.classList.contains('proto-prd-mode') && !opts.allowCanvas) return;

      const src = pickSpotlightSourceStep();
      if (!src) {
        mount.replaceChildren(Object.assign(document.createElement('div'), {
          className: 'proto-spotlight-empty',
          textContent: '未找到可用的界面步骤'
        }));
        root.classList.remove('hidden');
        document.body.classList.add('proto-spotlight-open');
        syncPresenterChromeAria();
        return;
      }

      mountProtoSpotlightSource(src, mount);

      root.classList.remove('hidden');
      document.body.classList.add('proto-spotlight-open');
      syncPresenterChromeAria();
      fitSpotlightMount();
      scheduleAnnotationLayout();
      updateAnnotationButton();
      updatePresentationLaserButtons();
      if (window.lucide) window.lucide.createIcons();
    }

    function toggleEditMode(force, options) {
      const enabled = typeof force === 'boolean' ? force : !document.body.classList.contains('proto-edit-mode');
      const opts = options && typeof options === 'object' ? options : {};
      if (!enabled && document.body.classList.contains('proto-edit-mode') && !opts.skipConfirm && hasTextEditChanges()) {
        const ok = window.confirm('文字修改尚未保存，确认放弃本次修改并退出吗？');
        if (!ok) return false;
      }
      if (enabled) {
        togglePresentationLaser(false);
        togglePrdViewer(false, { suppressResumeScroll: true });
        startEditSession();
        ensureRevisionTargets();
        ensureEditTargets();
        toggleRevisionMode(false);
      } else {
        finishEditSession();
      }
      document.body.classList.toggle('proto-edit-mode', enabled);
      document.getElementById('edit-panel')?.classList.add('hidden');
      document.querySelectorAll('[data-editable-text]').forEach((element) => {
        element.setAttribute('contenteditable', enabled ? 'true' : 'false');
      });
      if (!enabled) selectEditTarget(null);
      if (enabled) hideEditDeletePopover();
      updateChromeModeButtons();
      return true;
    }

    function startEditSession() {
      if (document.body.classList.contains('proto-edit-mode')) return;
      const area = getMainGeneratedArea();
      editSessionSnapshot = area ? area.innerHTML : null;
      editSessionOutput = false;
      editSessionDirty = false;
      editSessionSaving = false;
    }

    function finishEditSession() {
      if (!editSessionOutput) restoreEditSession();
      editSessionSnapshot = null;
      editSessionOutput = false;
      editSessionDirty = false;
      editSessionSaving = false;
    }

    function restoreEditSession() {
      const area = getMainGeneratedArea();
      if (!area || editSessionSnapshot === null) return;
      area.innerHTML = editSessionSnapshot;
      selectEditTarget(null);
      ensureRevisionTargets();
      ensureEditTargets();
      if (document.body.classList.contains('proto-edit-mode')) {
        document.querySelectorAll('[data-editable-text]').forEach((element) => {
          element.setAttribute('contenteditable', 'true');
        });
      }
      buildProtoOutlineNav();
      if (window.lucide) window.lucide.createIcons();
    }

    function resetEditSession() {
      if (!editSessionSnapshot) return;
      const ok = window.confirm('确认重置本次改文字？\n\n本次进入改文字模式后的文本调整都会恢复。');
      if (!ok) return;
      restoreEditSession();
      editSessionDirty = false;
      updateChromeModeButtons();
      showToast('已重置本次文字修改');
    }

    function toggleRevisionMode(force) {
      const enabled = typeof force === 'boolean' ? force : !document.body.classList.contains('proto-revision-mode');
      if (enabled) {
        togglePresentationLaser(false);
        togglePrdViewer(false, { suppressResumeScroll: true });
        if (document.body.classList.contains('proto-edit-mode') && !toggleEditMode(false)) return false;
        ensureRevisionTargets();
      }
      document.body.classList.toggle('proto-revision-mode', enabled);
      document.getElementById('revision-panel').classList.toggle('hidden', !enabled);
      if (!enabled) {
        closeRevisionPopover();
        selectRevisionTarget(null);
      }
      updateChromeModeButtons();
      return true;
    }

    function compactText(value) {
      return (value || '').replace(/\s+/g, ' ').trim();
    }

    function getRevisionTargetKind(element) {
      if (element.matches('.journey-step')) return '界面步骤';
      if (element.matches('.phone-frame, .phone-screen, .app-screen')) return '移动端界面';
      if (element.matches('.web-surface')) return 'Web 界面';
      if (element.matches('.nav-bar')) return '导航栏';
      if (element.matches('.step-number')) return '步骤编号';
      if (element.matches('.step-title')) return '步骤标题';
      if (element.matches('.branch-caption')) return '分支标题';
      if (element.matches('.nav-icon')) return '导航图标';
      if (element.matches('.nav-title')) return '导航标题';
      if (element.matches('.demo-pill')) return '标签';
      if (element.matches('.screen-title, .card h3')) return '标题';
      if (element.matches('.mini-meta')) return '栏目标题';
      if (element.matches('.segment-btn')) return '分段按钮';
      if (element.matches('.row-main')) return '列表主文案';
      if (element.matches('.row-desc')) return '列表说明';
      if (element.matches('.list-row')) return '列表行';
      if (element.matches('.list-group')) return '列表组';
      if (element.matches('.switch')) return '开关';
      if (element.matches('.primary-btn, .secondary-btn, .btn, [role="button"]')) return '按钮';
      if (element.matches('.dialog-backdrop')) return '弹窗遮罩';
      if (element.matches('.dialog')) return '弹窗';
      if (element.matches('.toast')) return 'Toast';
      if (element.matches('.web-topbar strong')) return 'Web 顶栏';
      if (element.matches('.input')) return '输入框';
      if (element.matches('.rail-link')) return '侧栏导航';
      if (element.matches('.kp-card')) return '统计卡';
      if (element.matches('.fake-row')) return '表格行';
      if (element.matches('.skill-chip')) return '技能标签';
      if (element.matches('.empty-illus')) return '空态区域';
      if (element.matches('.error-callout')) return '错误提示';
      if (element.matches('.annotation')) return '标注';
      if (element.matches('.app-content, .web-content')) return '内容区';
      if (element.matches('.muted, .card p')) return '说明文案';
      return '元素';
    }

    function getRevisionTargetContext(element) {
      const step = element.closest('.journey-step');
      if (!step) return 'Prototype';
      return step.dataset.protoLabel || step.id || 'Step';
    }

    function buildAutoRevisionLabel(element) {
      const kind = getRevisionTargetKind(element);
      const text = compactText(element.innerText || element.value || element.getAttribute('aria-label') || '');
      const context = getRevisionTargetContext(element);
      return text ? `${context} · ${kind}「${text.slice(0, 28)}」` : `${context} · ${kind}`;
    }

    function ensureRevisionTargets() {
      const area = getMainGeneratedArea();
      if (!area) return;
      const selector = autoRevisionTargetSelectors.join(', ');
      area.querySelectorAll(selector).forEach((element, index) => {
        if (!element.dataset.protoId) {
          element.dataset.protoId = `auto-revision-target-${index + 1}`;
          element.dataset.protoAuto = 'true';
        }
        if (!element.dataset.protoLabel) {
          element.dataset.protoLabel = buildAutoRevisionLabel(element);
        }
      });
    }

    function hasOwnVisibleText(element) {
      return Array.from(element.childNodes).some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
    }

    function hasNestedEditableText(element) {
      return Boolean(
        element.querySelector(
          'h1,h2,h3,h4,p,li,small,strong,span,[data-proto-editable="text"],[class*="title"],[class*="label"],[class*="desc"],[class*="caption"],[class*="meta"]'
        )
      );
    }

    function isProtectedEditTarget(element) {
      if (!element || !element.matches) return true;
      if (element.matches(protectedEditTargetSelectors.join(', '))) return true;
      return Boolean(element.closest('#proto-nav-dock, #prd-drawer, #revision-panel, #edit-panel, #proto-step-spotlight'));
    }

    function isEditableTextCandidate(element) {
      if (!element || !element.matches || isProtectedEditTarget(element)) return false;
      if (element.matches('[data-proto-editable="false"]')) return false;
      const tag = element.tagName.toLowerCase();
      const text = element.textContent.trim();
      if (!text) return false;
      if (element.matches('[data-proto-editable="text"]')) return true;
      if (['h1', 'h2', 'h3', 'h4', 'p', 'li', 'small', 'strong', 'span', 'label'].includes(tag) && !hasNestedEditableText(element)) return true;
      if (['button', 'a'].includes(tag) && text.length <= 40) return true;
      const className = String(element.className || '').toLowerCase();
      if (/(^|[-_\s])(title|label|desc|caption|meta|muted|badge|tag|chip|pill|btn|button)([-_\s]|$)/.test(className) && text.length <= 140) {
        return hasOwnVisibleText(element) || !hasNestedEditableText(element);
      }
      return false;
    }

    function ensureEditTargets() {
      const area = getMainGeneratedArea();
      if (!area) return;
      area.querySelectorAll(editableTextSelectors.join(', ')).forEach((element) => {
        if (!isEditableTextCandidate(element)) return;
        if (!element.dataset.protoId) {
          return;
        }
        if (element.dataset.protoAuto) return;
        element.dataset.editableText = 'true';
        if (!element.dataset.protoLabel) element.dataset.protoLabel = buildAutoRevisionLabel(element);
      });

      area.querySelectorAll('[data-edit-removable]').forEach((element) => {
        element.removeAttribute('data-edit-removable');
      });
    }

    function selectEditTarget(element) {
      document.querySelectorAll('[data-edit-selected="true"]').forEach((item) => item.removeAttribute('data-edit-selected'));
      selectedEditTarget = element;
      if (!element) {
        hideEditDeletePopover();
        return;
      }
      element.dataset.editSelected = 'true';
      hideEditDeletePopover();
    }

    function findSmallEditTarget(startNode, area) {
      if (!startNode || !area) return null;
      const path = typeof startNode.composedPath === 'function' ? startNode.composedPath() : [];
      const candidates = [];
      const pushCandidate = (node) => {
        if (!node || node === document || node === window || !node.matches || !area.contains(node)) return;
        if (node.matches('[data-editable-text]')) candidates.push(node);
      };
      path.forEach(pushCandidate);
      let node = startNode.nodeType === Node.ELEMENT_NODE ? startNode : startNode.parentElement;
      while (node && node !== area) {
        pushCandidate(node);
        node = node.parentElement;
      }
      const unique = [...new Set(candidates)].filter((element) => !isProtectedEditTarget(element));
      return (
        unique.find((element) => element.dataset.editableText === 'true') ||
        null
      );
    }

    function selectRevisionTarget(element) {
      document.querySelectorAll('.is-revision-selected').forEach((item) => item.classList.remove('is-revision-selected'));
      selectedRevisionTarget = element;

      const label = document.getElementById('revision-target');
      if (!element) {
        label.textContent = '当前未选择元素';
        return;
      }

      element.classList.add('is-revision-selected');
      label.textContent = `当前选择：${element.dataset.protoLabel || element.dataset.protoId}`;
    }

    function positionRevisionPopover(x, y) {
      const popover = document.getElementById('revision-popover');
      const padding = 16;
      popover.classList.remove('hidden');
      const rect = popover.getBoundingClientRect();
      const left = Math.min(Math.max(x + 12, padding), window.innerWidth - rect.width - padding);
      const top = Math.min(Math.max(y + 12, padding), window.innerHeight - rect.height - padding);
      popover.style.left = `${left}px`;
      popover.style.top = `${top}px`;
    }

    function openRevisionPopover(element, x, y, editIndex) {
      editingRevisionIndex = typeof editIndex === 'number' ? editIndex : null;
      selectRevisionTarget(element);
      const input = document.getElementById('revision-note');
      input.value = editingRevisionIndex === null ? '' : revisionNotes[editingRevisionIndex].note;
      positionRevisionPopover(x || window.innerWidth / 2, y || window.innerHeight / 2);
      input.focus();
    }

    function closeRevisionPopover() {
      document.getElementById('revision-popover').classList.add('hidden');
      document.getElementById('revision-note').value = '';
      editingRevisionIndex = null;
    }

    function saveRevisionNote() {
      const note = document.getElementById('revision-note').value.trim();
      if (!selectedRevisionTarget || !note) return;

      const item = {
        id: selectedRevisionTarget.dataset.protoId,
        label: selectedRevisionTarget.dataset.protoLabel || selectedRevisionTarget.dataset.protoId,
        note
      };

      if (editingRevisionIndex === null) {
        revisionNotes.push(item);
      } else {
        revisionNotes[editingRevisionIndex] = item;
      }

      renderRevisionNotes();
      closeRevisionPopover();
    }

    function renderRevisionNotes() {
      const list = document.getElementById('revision-list');
      if (!revisionNotes.length) {
        list.innerHTML = '';
        return;
      }

      list.innerHTML = revisionNotes
        .map(
          (item, index) =>
            `<div class="proto-revision-item"><div class="proto-revision-item-body"><strong class="proto-revision-item-title">#${index + 1} ${escapeHtml(
              item.label
            )}</strong><p class="proto-revision-item-note">${escapeHtml(item.note)}</p></div><div class="proto-revision-item-actions" role="toolbar" aria-label="条目操作"><button type="button" class="proto-revision-icon-btn" title="编辑" aria-label="编辑备注" onclick="editRevisionNote(${index})"><i data-lucide="pencil"></i></button><button type="button" class="proto-revision-icon-btn" title="删除" aria-label="删除本条" onclick="deleteRevisionNote(${index})"><i data-lucide="trash-2"></i></button></div></div>`
        )
        .join('');
      if (window.lucide) window.lucide.createIcons();
    }

    function editRevisionNote(index) {
      const item = revisionNotes[index];
      if (!item) return;
      const escaped =
        typeof CSS !== 'undefined' && typeof CSS.escape === 'function'
          ? CSS.escape(item.id)
          : String(item.id).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
      const target = document.querySelector(`[data-proto-id="${escaped}"]`);
      if (!target) return;

      const step = target.closest('.journey-step[id]');
      if (step && step.id) activateStep(step.id, { forceScroll: true });

      window.requestAnimationFrame(() => {
        target.scrollIntoView({ block: 'center', behavior: 'smooth' });
        const rect = target.getBoundingClientRect();
        openRevisionPopover(target, rect.left + rect.width / 2, rect.top + rect.height / 2, index);
      });
    }

    function deleteRevisionNote(index) {
      revisionNotes.splice(index, 1);
      renderRevisionNotes();
    }

    function hideEditDeletePopover() {
      const button = document.getElementById('edit-delete-popover');
      if (!button) return;
      button.classList.add('hidden');
    }

    function updateEditDeletePopover() {
      const button = document.getElementById('edit-delete-popover');
      if (!button) return;
      if (!document.body.classList.contains('proto-edit-mode') || !selectedEditTarget || !selectedEditTarget.dataset.editRemovable) {
        hideEditDeletePopover();
        return;
      }
      const rect = selectedEditTarget.getBoundingClientRect();
      const padding = 12;
      const left = Math.min(Math.max(rect.right + 8, padding), window.innerWidth - 42);
      const top = Math.min(Math.max(rect.top - 8, padding), window.innerHeight - 42);
      button.style.left = `${left}px`;
      button.style.top = `${top}px`;
      button.classList.remove('hidden');
    }

    function removeSelectedEditTarget() {
      window.alert('改文字现在只支持文本修订。删除卡片、移除模块或调整结构请使用大改备注。');
    }

    function sanitizeEditedDocument(clone) {
      clone.classList.remove('proto-edit-mode', 'proto-revision-mode', 'proto-prd-mode', 'hide-annotations');
      clone.querySelectorAll('[contenteditable]').forEach((node) => node.setAttribute('contenteditable', 'false'));
      clone.querySelectorAll('[data-proto-auto]').forEach((node) => {
        node.removeAttribute('data-proto-id');
        node.removeAttribute('data-proto-label');
        node.removeAttribute('data-proto-auto');
      });
      clone.querySelectorAll('[data-editable-text], [data-edit-removable]').forEach((node) => {
        node.removeAttribute('data-editable-text');
        node.removeAttribute('data-edit-removable');
      });
      clone.querySelectorAll('[data-edit-selected], .is-revision-selected, .is-prd-focus, .is-prd-row-focus').forEach((node) => {
        node.removeAttribute('data-edit-selected');
        node.classList.remove('is-revision-selected');
        node.classList.remove('is-prd-focus');
        node.classList.remove('is-prd-row-focus');
        node.style.removeProperty('--proto-prd-preview-scale');
      });
      clone.querySelectorAll('#revision-popover').forEach((node) => node.classList.add('hidden'));
      clone.querySelectorAll('#edit-delete-popover').forEach((node) => node.classList.add('hidden'));
      clone.querySelectorAll('#revision-panel, #edit-panel').forEach((node) => node.classList.add('hidden'));
      clone.querySelectorAll('#prd-drawer').forEach((node) => node.classList.remove('is-open'));
      clone.querySelectorAll('#proto-step-spotlight').forEach((node) => {
        node.classList.add('hidden');
      });
      clone.querySelectorAll('#proto-spotlight-mount').forEach((node) => node.replaceChildren());
      clone.querySelectorAll('#proto-prd-proto-rail-wrap').forEach((node) => node.setAttribute('aria-hidden', 'true'));
      clone.querySelector('body')?.classList.remove('proto-spotlight-open');
    }

    function serializeEditedHtml() {
      const clone = document.documentElement.cloneNode(true);
      sanitizeEditedDocument(clone);
      return '<!doctype html>\n' + clone.outerHTML;
    }

    function findByProtoId(root, protoId) {
      return Array.from(root.querySelectorAll('[data-proto-id]')).filter((element) => element.dataset.protoId === protoId);
    }

    function cleanPatchText(value) {
      return String(value || '').replace(/\s+/g, ' ').trim();
    }

    function buildContentPatch() {
      const area = getMainGeneratedArea();
      const parser = new DOMParser();
      const originalDoc = parser.parseFromString(`<div id="proto-patch-root">${editSessionSnapshot || ''}</div>`, 'text/html');
      const originalRoot = originalDoc.getElementById('proto-patch-root');
      const operations = [];
      const seen = new Set();

      if (area && originalRoot) {
        area.querySelectorAll('[data-editable-text="true"][data-proto-id]').forEach((element) => {
          if (element.dataset.protoAuto) return;
          if (element.querySelector('[data-editable-text="true"]')) return;
          const protoId = element.dataset.protoId;
          const originalMatches = findByProtoId(originalRoot, protoId);
          if (originalMatches.length !== 1) return;
          const before = cleanPatchText(originalMatches[0].textContent);
          const after = cleanPatchText(element.textContent);
          if (before === after) return;
          if (seen.has(`replace_text:${protoId}`)) return;
          seen.add(`replace_text:${protoId}`);
          operations.push({
            op: 'replace_text',
            step_id: element.closest('.journey-step')?.dataset?.protoId || '',
            data_proto_id: protoId,
            label: element.dataset.protoLabel || protoId,
            original_text: before,
            text: after
          });
        });
      }

      return {
        schema_version: 1,
        kind: 'protopilot-content-edit-patch',
        created_at: new Date().toISOString(),
        operations
      };
    }

    function serializeContentPatch() {
      return JSON.stringify(buildContentPatch(), null, 2);
    }

    function hasTextEditChanges() {
      return buildContentPatch().operations.length > 0;
    }

    async function copyFullHtmlCode() {
      const html = serializeEditedHtml();
      try {
        if (!navigator.clipboard) throw new Error('Clipboard API unavailable');
        await navigator.clipboard.writeText(html);
        editSessionOutput = true;
        showToast('已复制代码');
      } catch (error) {
        window.prompt('复制以下 HTML 代码，然后粘贴覆盖目标文件。', html);
        editSessionOutput = true;
      }
    }

    async function copyContentPatch() {
      const patch = serializeContentPatch();
      try {
        if (!navigator.clipboard) throw new Error('Clipboard API unavailable');
        await navigator.clipboard.writeText(patch);
        editSessionOutput = true;
        showToast('已复制文字补丁');
      } catch (error) {
        window.prompt('复制以下文字补丁 JSON，然后用 apply-edit-patch 应用到本地内容包。', patch);
        editSessionOutput = true;
      }
    }

    async function getPreviewSaveContext() {
      const response = await fetch('/.protopilot-preview-health', { cache: 'no-store' });
      if (!response.ok) throw new Error(`preview health HTTP ${response.status}`);
      const health = await response.json();
      if (!health || !health.ok || !health.token) throw new Error('当前页面不是 ProtoPilot preview 服务。');
      return health;
    }

    async function saveTextEdits() {
      if (!document.body.classList.contains('proto-edit-mode')) return;
      if (window.location.protocol === 'file:') {
        window.alert('请先用 preview 打开本需求目录，再保存文字修改。直接 file:// 打开时浏览器不能写回源文件。');
        return;
      }
      let saveContext = null;
      try {
        saveContext = await getPreviewSaveContext();
      } catch (error) {
        window.alert(`保存失败：${error && error.message ? error.message : error}`);
        return;
      }
      if (saveContext.text_save_supported === false) {
        window.alert('当前原型没有 content package，无法保存文字修改。请先迁移到 prototype-content/screens/*.html 后再使用改文字保存。');
        return;
      }
      const patch = buildContentPatch();
      if (!patch.operations.length) {
        if (editSessionDirty) {
          window.alert('当前修改的文字没有稳定 data-proto-id，无法保存。请为该文本补充稳定 data-proto-id / data-proto-label 后再保存。');
        } else {
          editSessionDirty = false;
          showToast('没有需要保存的文字修改');
        }
        updateChromeModeButtons();
        return;
      }
      editSessionSaving = true;
      updateChromeModeButtons();
      try {
        const response = await fetch(textPatchSavePath, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-ProtoPilot-Preview-Token': saveContext.token
          },
          body: JSON.stringify(patch)
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok || !result.ok) {
          const failures = Array.isArray(result.failures) ? result.failures.join('\n') : '';
          throw new Error(failures || result.failure || `保存失败：HTTP ${response.status}`);
        }
        editSessionOutput = true;
        editSessionDirty = false;
        showToast('已保存文字修改，正在刷新');
        window.setTimeout(() => window.location.reload(), 420);
      } catch (error) {
        editSessionSaving = false;
        updateChromeModeButtons();
        window.alert(`保存失败：${error && error.message ? error.message : error}`);
      }
    }

    document.addEventListener(
      'click',
      (event) => {
        if (!document.body.classList.contains('proto-edit-mode')) return;
        const area = getMainGeneratedArea();
        if (!area || !area.contains(event.target)) return;
        const target = findSmallEditTarget(event.target, area);
        if (target) selectEditTarget(target);
        event.stopPropagation();
      },
      true
    );

    document.addEventListener(
      'input',
      (event) => {
        if (!document.body.classList.contains('proto-edit-mode')) return;
        const target = event.target?.closest?.('[data-editable-text]');
        if (!target || !getMainGeneratedArea()?.contains(target)) return;
        editSessionDirty = true;
        updateChromeModeButtons();
      },
      true
    );

    window.addEventListener('scroll', () => {
      if (document.body.classList.contains('proto-edit-mode')) updateEditDeletePopover();
    }, { passive: true });

    window.addEventListener('resize', () => {
      if (document.body.classList.contains('proto-edit-mode')) updateEditDeletePopover();
      if (document.body.classList.contains('proto-prd-mode')) fitPrdFocusStep();
      const sp = document.getElementById('proto-step-spotlight');
      if (sp && !sp.classList.contains('hidden')) fitSpotlightMount();
      scheduleAnnotationLayout();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') return;
      const spotlight = document.getElementById('proto-step-spotlight');
      if (spotlight && !spotlight.classList.contains('hidden')) {
        event.preventDefault();
        toggleProtoStepSpotlight(false);
      }
    });

    function buildRevisionPrompt() {
      const instruction = [
        '# ProtoPilot HTML 大改请求',
        '',
        '请你作为 ProtoPilot HTML 原型维护 agent，根据下面的大改备注修改当前需求目录。',
        '',
        '要求：',
        '- 只改业务原型事实源：prototype-content/screens/*.html 与 prototype-content/content.css。',
        '- 不要改宣讲台壳层、PRD Viewer、目录、spotlight、preview 或改文字保存能力，除非备注明确要求。',
        '- 按 data-proto-id / data-proto-label 定位目标；找不到时先说明。',
        '- 完成后运行 package-check --strict、build-content、inject --strict、final-check --require-content --require-complete、quality-check --strict。',
        ''
      ];
      if (!revisionNotes.length) return [...instruction, '## 大改备注', '', '暂无大改备注。'].join('\n');

      return [
        ...instruction,
        '## 大改备注',
        '',
        ...revisionNotes.flatMap((item, index) => [`## ${index + 1}. ${item.label}`, '', `- 目标 ID：\`${item.id}\``, `- 修订备注：${item.note}`, ''])
      ].join('\n');
    }

    async function copyRevisionNotes() {
      const text = buildRevisionPrompt();
      try {
        if (!navigator.clipboard) throw new Error('Clipboard API unavailable');
        await navigator.clipboard.writeText(text);
        showToast('已复制给 AI');
      } catch (error) {
        window.prompt('复制以下内容给 AI', text);
      }
    }

    function clearRevisionNotes() {
      revisionNotes.length = 0;
      renderRevisionNotes();
      closeRevisionPopover();
      selectRevisionTarget(null);
    }

    function escapeHtml(value) {
      return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    document.addEventListener(
      'click',
      (event) => {
        if (!document.body.classList.contains('proto-edit-mode')) return;
        const area = getMainGeneratedArea();
        if (!area || !area.contains(event.target)) return;
        const target = findSmallEditTarget(event.target, area);
        if (target) selectEditTarget(target);
      },
      true
    );

    function getPrdViewerElements() {
      const viewer = document.querySelector('#prd-drawer .proto-prd-viewer');
      if (!viewer) return null;
      let status = document.getElementById('prd-viewer-status');
      let fallback = document.getElementById('prd-viewer-fallback');
      let message = document.getElementById('prd-viewer-fallback-message');
      let output = document.getElementById('prd-markdown-output');
      let sourceNote = document.getElementById('prd-viewer-source-note');
      let fileInput = document.getElementById('prd-file-input');

      if (!status) {
        status = document.createElement('div');
        status.className = 'proto-prd-status';
        status.id = 'prd-viewer-status';
        status.setAttribute('role', 'status');
        status.textContent = '正在加载 PRD…';
        viewer.prepend(status);
      }

      if (!fallback) {
        fallback = document.createElement('section');
        fallback.className = 'proto-prd-fallback hidden';
        fallback.id = 'prd-viewer-fallback';
        fallback.setAttribute('aria-live', 'polite');
        fallback.innerHTML = `
          <h3>PRD 暂时没有加载出来</h3>
          <p id="prd-viewer-fallback-message"></p>
          <ul>
            <li>请确认正在通过本地 HTTP 打开，而不是直接打开 file:// 文件。</li>
            <li>请确认 PRD 文件与 index.html 的相对路径正确。</li>
            <li>如果 Marked CDN 或浏览器本地读取被拦截，可以临时手动选择同目录 Markdown 文件。</li>
          </ul>
          <div class="proto-prd-fallback-actions">
            <button type="button" class="secondary-btn" onclick="choosePrdMarkdownFile()"><i data-lucide="folder-open" class="button-icon"></i>选择同目录 PRD 文件</button>
          </div>
        `;
        viewer.appendChild(fallback);
        message = document.getElementById('prd-viewer-fallback-message');
      }

      if (!sourceNote) {
        sourceNote = document.createElement('p');
        sourceNote.className = 'proto-prd-source-note hidden';
        sourceNote.id = 'prd-viewer-source-note';
        viewer.insertBefore(sourceNote, fallback);
      }

      if (!output) {
        output = document.createElement('div');
        output.className = 'proto-prd-markdown typora-preview hidden';
        output.id = 'prd-markdown-output';
        output.setAttribute('aria-live', 'polite');
        viewer.insertBefore(output, fallback);
      }

      if (!fileInput) {
        fileInput = document.createElement('input');
        fileInput.className = 'proto-prd-file-input';
        fileInput.id = 'prd-file-input';
        fileInput.type = 'file';
        fileInput.accept = '.md,.markdown,text/markdown,text/plain';
        viewer.appendChild(fileInput);
      }

      return {
        viewer,
        status,
        fallback,
        message,
        output,
        sourceNote,
        fileInput,
      };
    }

    function getPrdViewerSource(elements) {
      if (!elements) return '';
      return (elements.viewer.dataset.prdSrc || '').trim();
    }

    function getMarkedParser() {
      const api = window.marked;
      if (!api) return null;
      if (typeof api.parse === 'function') return api.parse.bind(api);
      if (typeof api.marked === 'function') return api.marked.bind(api);
      if (typeof api === 'function') return api;
      return null;
    }

    function enhancePrdMarkdownOutput(output) {
      if (!output) return;
      output.querySelectorAll('table').forEach((table) => {
        if (table.parentElement?.classList.contains('proto-prd-table-wrap')) return;
        const wrapper = document.createElement('div');
        wrapper.className = 'proto-prd-table-wrap';
        table.parentNode?.insertBefore(wrapper, table);
        wrapper.appendChild(table);
      });
      output.querySelectorAll('a[href]').forEach((link) => {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noreferrer noopener');
      });
    }

    function renderPrdMarkdown(markdown, sourceLabel) {
      const elements = getPrdViewerElements();
      if (!elements) return false;
      const parseMarkdown = getMarkedParser();
      if (!parseMarkdown) {
        showPrdViewerFailure(
          getPrdViewerSource(elements),
          'Markdown 渲染器加载失败：Marked CDN 没有加载完成或被浏览器阻止。'
        );
        return false;
      }
      const text = String(markdown || '').replace(/^[\u200B\u200C\u200D\u200E\u200F\uFEFF]/, '');
      try {
        elements.output.innerHTML = parseMarkdown(text);
      } catch (error) {
        showPrdViewerFailure(
          getPrdViewerSource(elements),
          `Markdown 渲染失败：${error && error.message ? error.message : error}`
        );
        return false;
      }
      enhancePrdMarkdownOutput(elements.output);
      setPrdViewerReady(sourceLabel);
      return true;
    }

    function setPrdViewerReady(sourceLabel) {
      const elements = getPrdViewerElements();
      if (!elements) return;
      elements.viewer.classList.remove('is-fallback-active');
      elements.viewer.classList.remove('is-loading');
      elements.status?.classList.add('hidden');
      elements.fallback?.classList.add('hidden');
      elements.output?.classList.remove('hidden');
      if (elements.sourceNote) {
        elements.sourceNote.textContent = sourceLabel || '';
        elements.sourceNote.classList.toggle('hidden', !sourceLabel);
      }
    }

    function showPrdViewerLoading(source) {
      const elements = getPrdViewerElements();
      if (!elements) return;
      elements.viewer.classList.remove('is-fallback-active');
      elements.viewer.classList.add('is-loading');
      elements.fallback?.classList.add('hidden');
      elements.output?.classList.add('hidden');
      elements.sourceNote?.classList.add('hidden');
      if (elements.status) {
        elements.status.classList.remove('hidden');
        elements.status.textContent = `正在加载 PRD：${source || '未绑定路径'}…`;
      }
    }

    function showPrdViewerFailure(source, reason) {
      const elements = getPrdViewerElements();
      if (!elements) return;
      elements.viewer.classList.add('is-fallback-active');
      elements.viewer.classList.remove('is-loading');
      elements.status?.classList.add('hidden');
      elements.fallback?.classList.remove('hidden');
      elements.output?.classList.add('hidden');
      if (elements.message) {
        elements.message.innerHTML = `当前绑定的 PRD 路径是：<code>${escapeHtml(source || '未绑定')}</code>。${escapeHtml(
          reason || '自动读取失败。'
        )}`;
      }
      if (elements.sourceNote) {
        elements.sourceNote.textContent =
          '可以点击“选择同目录 PRD 文件”临时查看 Markdown；这不会修改 index.html，也不会改变绑定路径。';
        elements.sourceNote.classList.remove('hidden');
      }
      if (window.lucide) window.lucide.createIcons();
    }

    async function renderPrdSource(source) {
      if (!source) {
        showPrdViewerFailure('', '没有找到绑定的 PRD 路径。');
        return false;
      }
      if (!getMarkedParser()) {
        showPrdViewerFailure(source, 'Markdown 渲染器加载失败：Marked CDN 没有加载完成或被浏览器阻止。');
        return false;
      }
      if (/^[A-Za-z]:[\\/]/.test(source) || source.startsWith('file://') || source.includes('\\')) {
        showPrdViewerFailure(source, 'PRD 路径需要是浏览器可读取的相对路径，例如 ../需求.md。请重新构建原型。');
        return false;
      }
      try {
        const response = await fetch(source, { cache: 'no-store' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const markdown = await response.text();
        return renderPrdMarkdown(markdown, `直接读取源 PRD：${source}`);
      } catch (error) {
        const protocol = window.location?.protocol || '';
        const fileHint = protocol === 'file:' ? '当前页面看起来是 file:// 打开，浏览器通常会阻止读取同目录 Markdown。' : '';
        showPrdViewerFailure(source, `${fileHint}自动读取失败：${error && error.message ? error.message : error}`);
        return false;
      }
    }

    let prdViewerBound = false;
    let prdViewerLoadStarted = false;

    function bindPrdViewerControls() {
      if (prdViewerBound) return;
      const elements = getPrdViewerElements();
      if (!elements) return;
      prdViewerBound = true;
      elements.fileInput?.addEventListener('change', () => {
        const file = elements.fileInput.files && elements.fileInput.files[0];
        if (!file) return;
        const lowerName = file.name.toLowerCase();
        if (!lowerName.endsWith('.md') && !lowerName.endsWith('.markdown')) {
          showPrdViewerFailure(getPrdViewerSource(elements), '请选择 .md 或 .markdown 文件。');
          elements.fileInput.value = '';
          return;
        }
        const reader = new FileReader();
        reader.onload = () => {
          renderPrdMarkdown(String(reader.result || ''), `临时查看：${file.name}（未修改绑定 PRD）`);
          elements.fileInput.value = '';
        };
        reader.onerror = () => {
          showPrdViewerFailure(getPrdViewerSource(elements), '手动读取文件失败，请重新选择。');
          elements.fileInput.value = '';
        };
        reader.readAsText(file, 'utf-8');
      });
    }

    function initPrdViewer(force) {
      const elements = getPrdViewerElements();
      if (!elements) return;
      bindPrdViewerControls();

      const source = getPrdViewerSource(elements);

      if (!force && prdViewerLoadStarted) return;
      prdViewerLoadStarted = true;
      showPrdViewerLoading(source);
      renderPrdSource(source);
    }

    function choosePrdMarkdownFile() {
      const elements = getPrdViewerElements();
      elements?.fileInput?.click();
    }

    function getProtoLightActionTargets(trigger, root) {
      const selector = (trigger.dataset.protoTarget || '').trim();
      if (!selector) return [trigger];
      try {
        return [...root.querySelectorAll(selector)];
      } catch (_error) {
        return [];
      }
    }

    function handleProtoLightInteraction(event) {
      if (
        document.body.classList.contains('proto-edit-mode') ||
        document.body.classList.contains('proto-revision-mode')
      )
        return;
      const trigger = event.target.closest('[data-proto-action]');
      if (!trigger || !getMainGeneratedArea()?.contains(trigger)) return;
      const action = (trigger.dataset.protoAction || '').trim().toLowerCase();
      const allowed = new Set(['toggle', 'show', 'hide', 'toggle-class', 'add-class', 'remove-class', 'activate', 'toast']);
      if (!allowed.has(action)) return;
      const root =
        trigger.closest('.proto-content-screen') ||
        trigger.closest('.app-screen') ||
        trigger.closest('.web-surface') ||
        trigger.closest('.journey-step');
      if (!root) return;
      const targets = getProtoLightActionTargets(trigger, root);
      const className = (trigger.dataset.protoClass || 'is-active').trim();
      if (trigger.matches('a[href], button')) event.preventDefault();
      if (action === 'toast') {
        showToast(trigger.dataset.protoMessage || trigger.textContent || '已更新');
        return;
      }
      if (action === 'activate') {
        const groupSelector = (trigger.dataset.protoGroup || '').trim();
        if (groupSelector) {
          try {
            root.querySelectorAll(groupSelector).forEach((node) => node.classList.remove(className));
          } catch (_error) {
            return;
          }
        }
        targets.forEach((node) => node.classList.add(className));
        trigger.classList.add(className);
      } else if (action === 'show') {
        targets.forEach((node) => node.classList.remove('hidden'));
      } else if (action === 'hide') {
        targets.forEach((node) => node.classList.add('hidden'));
      } else if (action === 'toggle') {
        targets.forEach((node) => node.classList.toggle('hidden'));
      } else if (action === 'add-class') {
        targets.forEach((node) => node.classList.add(className));
      } else if (action === 'remove-class') {
        targets.forEach((node) => node.classList.remove(className));
      } else if (action === 'toggle-class') {
        targets.forEach((node) => node.classList.toggle(className));
      }
      scheduleAnnotationLayout();
      if (document.body.classList.contains('proto-spotlight-open')) refreshProtoStepSpotlightMountIfOpen();
    }

    document.addEventListener('click', handleProtoLightInteraction);
    document.getElementById('proto-spotlight-stage')?.addEventListener('wheel', handleSpotlightWheel, { passive: false });

    document.addEventListener(
      'click',
      (event) => {
        if (!document.body.classList.contains('proto-revision-mode')) return;
        const target = event.target.closest('[data-proto-id]');
        if (!target) return;
        event.preventDefault();
        event.stopPropagation();
        openRevisionPopover(target, event.clientX, event.clientY);
      },
      true
    );

    /** 画布模式：点击某一步内的界面视为选中该步，目录同步高亮（非 PRD / 非作者模式） */
    getMainGeneratedArea()?.addEventListener('click', (event) => {
      if (document.body.classList.contains('proto-prd-mode')) return;
      if (
        document.body.classList.contains('proto-edit-mode') ||
        document.body.classList.contains('proto-revision-mode')
      )
        return;
      if (document.body.classList.contains('proto-spotlight-open')) return;
      const step = event.target.closest('.journey-step[id]');
      const area = getMainGeneratedArea();
      if (!area || !step || !area.contains(step)) return;
      if (!step.id) return;
      if (event.target.closest('button, a[href], input, textarea, select, [contenteditable="true"], label'))
        return;
      activateStep(step.id);
    });

    getMainGeneratedArea()?.addEventListener('dblclick', (event) => {
      if (
        document.body.classList.contains('proto-prd-mode') ||
        document.body.classList.contains('proto-edit-mode') ||
        document.body.classList.contains('proto-revision-mode') ||
        document.body.classList.contains('proto-excalidraw-edit-mode') ||
        document.body.classList.contains('proto-spotlight-open')
      )
        return;
      if (event.target.closest('button, a[href], input, textarea, select, [contenteditable="true"], label, .excalidraw-editor-modal'))
        return;
      const step = event.target.closest('.journey-step[id]');
      const area = getMainGeneratedArea();
      if (!area || !step || !area.contains(step) || !step.id) return;
      event.preventDefault();
      activateStep(step.id, { suppressScroll: true });
      toggleProtoStepSpotlight(true, { allowCanvas: true });
    });

    function resetProtoShellModes() {
      togglePresentationLaser(false);
      toggleProtoStepSpotlight(false);
      if (document.body.classList.contains('proto-prd-mode')) togglePrdViewer(false, { suppressResumeScroll: true });
      if (document.body.classList.contains('proto-edit-mode')) toggleEditMode(false);
      if (document.body.classList.contains('proto-revision-mode')) toggleRevisionMode(false);
      if (document.body.classList.contains('proto-excalidraw-edit-mode')) {
        window.ProtoPilotExcalidraw?.toggleEditMode?.(false);
      }
      updateChromeModeButtons();
      syncPresenterChromeAria();
    }

    function refreshProtoShell(options) {
      const opts = options && typeof options === 'object' ? options : {};
      const preserveActiveId = opts.preserveActiveId !== false ? pickVisibleJourneyStepId() : null;
      if (opts.forcePrdReload) initPrdViewer(true);
      if (opts.applyStoredUiState) applyUiState();
      buildProtoOutlineNav();
      wireProtoNavDockAria();
      if (preserveActiveId && document.getElementById(preserveActiveId)) {
        activateStep(preserveActiveId, { forceScroll: false, suppressScroll: true });
      } else {
        syncProtoNavActiveWithViewport();
      }
      if (document.body.classList.contains('proto-prd-mode')) setPrdFocusStep();
      if (document.body.classList.contains('proto-spotlight-open')) refreshProtoStepSpotlightMountIfOpen();
      scheduleAnnotationLayout();
      updateChromeModeButtons();
      syncPresenterChromeAria();
      if (window.lucide) window.lucide.createIcons();
    }

    function serializeCleanPrototypeHtml() {
      const clone = document.documentElement.cloneNode(true);
      sanitizeEditedDocument(clone);
      return '<!doctype html>\n' + clone.outerHTML;
    }

    initPrdViewer(false);
    wireProtoNavDockAria();
    applyUiState();
    refreshProtoShell({ preserveActiveId: false });

    window.ProtoPilotShell = Object.assign(window.ProtoPilotShell || {}, {
      refresh: refreshProtoShell,
      resetModes: resetProtoShellModes,
      reset: resetProtoShellModes,
      serializeCleanHtml: serializeCleanPrototypeHtml,
      buildContentPatch,
      serializeContentPatch,
      saveTextEdits,
      serialize: serializeCleanPrototypeHtml
    });

    window.protoPilotShellInit = function protoPilotShellInit() {
      window.ProtoPilotShell.refresh({ forcePrdReload: true });
    };
