(function () {
  if (typeof window === 'undefined') {
    return;
  }

  var MAX_WIDTH_PX = 1400;
  var MAX_WIDTH_VW = 95;
  var MAX_HEIGHT_VH = 90;
  var MIN_SCALE = 0.1;
  var MAX_SCALE = 6;
  var SCALE_STEP = 0.25;
  var IMAGE_GROWTH_RATIO = 0.6;

  function computeDisplayScale(scale) {
    if (scale <= 1) {
      return Math.max(scale, MIN_SCALE);
    }
    return 1 + (scale - 1) * IMAGE_GROWTH_RATIO;
  }

  function applySizing(img) {
    if (!img) {
      return;
    }
    img.style.width = 'auto';
    img.style.height = 'auto';
    img.style.maxWidth = 'min(' + MAX_WIDTH_VW + 'vw, ' + MAX_WIDTH_PX + 'px)';
    img.style.maxHeight = MAX_HEIGHT_VH + 'vh';
    img.style.transform = '';
  }

  function ensurePanzoom(img) {
    if (!img || typeof Panzoom === 'undefined') {
      return null;
    }

    // Remove width/height attributes copied from inline image so overlay can scale
    try {
      img.removeAttribute('width');
      img.removeAttribute('height');
    } catch (e) {}

    applySizing(img);

    if (img.__panzoomInstance) {
      img.__panzoomInstance.reset({ animate: true });
      return img.__panzoomInstance;
    }

    // Wrap image into a stable stage container so transforms don't fight layout
    var stage = img.parentElement && img.parentElement.classList.contains('pz-stage') ? img.parentElement : null;
    if (!stage) {
      stage = document.createElement('div');
      stage.className = 'pz-stage';
      img.parentElement.insertBefore(stage, img);
      stage.appendChild(img);
    }

    var panzoom = Panzoom(img, {
      cursor: 'grab',
      maxScale: MAX_SCALE,
      minScale: MIN_SCALE,
      step: SCALE_STEP,
      animate: true,
      panOnlyWhenZoomed: true,
      startScale: 1,
      startX: 0,
      startY: 0,
      touchAction: 'none',
      setTransform: function (element, state) {
        var displayScale = computeDisplayScale(state.scale);
        element.style.transform = 'scale(' + displayScale + ') translate(' + state.x + 'px, ' + state.y + 'px)';
        if (state.isSVG) {
          element.setAttribute('transform', 'scale(' + displayScale + ') translate(' + state.x + ',' + state.y + ')');
        }
      }
    });
    img.__panzoomInstance = panzoom;
    stage.__panzoomInstance = panzoom;

    var container = stage.closest('.gslide-image');
    if (container) {
      var root = container.closest('.glightbox-container') || document.body;
      var baseSize = null;

      var applyBaseSize = function () {
        if (!baseSize) {
          return;
        }
        stage.style.width = baseSize.width + 'px';
        stage.style.height = baseSize.height + 'px';
      };

      var updateStageSize = function (scale) {
        if (!baseSize) {
          return;
        }
        var appliedScale = Math.max(1, scale);
        stage.style.width = baseSize.width * appliedScale + 'px';
        stage.style.height = baseSize.height * appliedScale + 'px';
      };

      var sizeToViewport = function (opts) {
        requestAnimationFrame(function () {
          var vw = Math.min(window.innerWidth * (MAX_WIDTH_VW / 100), MAX_WIDTH_PX);
          var vh = window.innerHeight * (MAX_HEIGHT_VH / 100);
          var iw = img.naturalWidth || img.getBoundingClientRect().width || vw;
          var ih = img.naturalHeight || img.getBoundingClientRect().height || vh;
          if (iw <= 0 || ih <= 0) {
            return;
          }
          var scale = Math.min(vw / iw, vh / ih);
          if (!isFinite(scale) || scale <= 0) {
            scale = 1;
          }
          var targetW = Math.min(iw * scale, vw);
          var targetH = Math.min(ih * scale, vh);
          baseSize = { width: targetW, height: targetH };
          applyBaseSize();
          updateStageSize(1);
          img.style.width = '100%';
          img.style.height = '100%';
          if (!opts || opts.reset !== false) {
            root.classList.remove('glb-zoomed');
            panzoom.reset({ animate: false });
          }
        });
      };

      // Run fit only after the overlay image actually loaded to avoid snap-back
      if (img.complete) sizeToViewport();
      else img.addEventListener('load', function onload() { img.removeEventListener('load', onload); sizeToViewport(); });

      var updateZoomed = function () {
        if (!baseSize) {
          return;
        }
        var s = panzoom.getScale();
        if (s > 1.01) {
          root.classList.add('glb-zoomed');
        } else {
          root.classList.remove('glb-zoomed');
        }
        updateStageSize(s);
        if (s <= 1.01) {
          // keep transforms but ensure stage is aligned to base size
          applyBaseSize();
        }
      };
      img.addEventListener('panzoomzoom', updateZoomed);
      img.addEventListener('panzoomreset', updateZoomed);

      stage.addEventListener('wheel', function (event) {
        if (event.ctrlKey) return;
        event.preventDefault();
        event.stopPropagation();
        try {
          panzoom.zoomWithWheel(event, { step: SCALE_STEP, maxScale: MAX_SCALE, minScale: MIN_SCALE, animate: false });
        } catch (e) {
          var rect = img.getBoundingClientRect();
          var scale = panzoom.getScale();
          var dir = event.deltaY < 0 ? 1 : -1;
          var target = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale + dir * SCALE_STEP));
          panzoom.zoom(target, { animate: false, focal: { clientX: event.clientX - rect.left, clientY: event.clientY - rect.top } });
        }
        updateZoomed();
      }, { passive: false });

      var pointerTarget = img;
      pointerTarget.addEventListener('pointerdown', function (e) {
        e.stopPropagation();
        img.classList.add('is-panning');
      });
      window.addEventListener('pointerup', function () {
        img.classList.remove('is-panning');
      });
      window.addEventListener('pointerleave', function () {
        img.classList.remove('is-panning');
      });

      img.addEventListener('dblclick', function (event) {
        event.preventDefault();
        event.stopPropagation();
        panzoom.reset({ animate: true });
        updateStageSize(1);
        applyBaseSize();
        root.classList.remove('glb-zoomed');
        updateZoomed();
      });

      window.addEventListener('resize', function () {
        sizeToViewport({ reset: false });
        updateZoomed();
      });
    }

    return panzoom;
  }

  function enhanceSlide(slide) {
    if (!slide || !slide.slideNode) {
      return;
    }
    var img = slide.slideNode.querySelector('.gslide-image img');
    if (!img) {
      return;
    }

    requestAnimationFrame(function () {
      ensurePanzoom(img);
    });
  }

  function enhanceInstance(instance) {
    if (!instance || instance.__panzoomEnhanced) {
      return;
    }
    instance.__panzoomEnhanced = true;

    instance.on('open', function (data) {
      enhanceSlide(data.current);
    });

    instance.on('slide_changed', function (data) {
      enhanceSlide(data.current);
    });

    instance.on('close', function () {
      var images = document.querySelectorAll('.glightbox-container .gslide-image img');
      images.forEach(function (img) {
        if (img.__panzoomInstance) {
          img.__panzoomInstance.reset({ animate: false });
        }
        img.classList.remove('is-panning');
      });
    });
  }

  var originalGLightbox = window.GLightbox;
  if (typeof originalGLightbox !== 'function') {
    return;
  }

  function wrappedGLightbox() {
    var instance = originalGLightbox.apply(this, arguments);
    enhanceInstance(instance);
    return instance;
  }

  for (var key in originalGLightbox) {
    if (Object.prototype.hasOwnProperty.call(originalGLightbox, key)) {
      wrappedGLightbox[key] = originalGLightbox[key];
    }
  }
  wrappedGLightbox.prototype = originalGLightbox.prototype;
  if (originalGLightbox.default) {
    wrappedGLightbox.default = originalGLightbox.default;
  }

  window.GLightbox = wrappedGLightbox;
})();
