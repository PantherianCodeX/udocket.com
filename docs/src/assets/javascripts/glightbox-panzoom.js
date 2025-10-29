(function () {
  if (typeof window === 'undefined') {
    return;
  }

  var MAX_WIDTH_PX = 1400;
  var MAX_WIDTH_VW = 95;
  var MAX_HEIGHT_VH = 90;
  var MIN_SCALE = 1;
  var MAX_SCALE = 6;
  var SCALE_STEP = 0.25;

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

    var panzoom = Panzoom(img, {
      cursor: 'grab',
      contain: 'outside',
      maxScale: MAX_SCALE,
      minScale: MIN_SCALE,
      step: SCALE_STEP,
      animate: true,
      panOnlyWhenZoomed: false,
      startScale: 1,
      startX: 0,
      startY: 0,
      touchAction: 'none'
    });
    img.__panzoomInstance = panzoom;

    var container = img.closest('.gslide-image');
    if (container) {
      var sizeToViewport = function () {
        requestAnimationFrame(function () {
          var vw = window.innerWidth * 0.95;
          var vh = window.innerHeight * 0.90;
          var iw = img.naturalWidth || img.getBoundingClientRect().width || vw;
          var ih = img.naturalHeight || img.getBoundingClientRect().height || vh;
          if (iw <= 0 || ih <= 0) return;
          var ar = iw / ih;
          var targetW = vw;
          var targetH = vw / ar;
          if (targetH > vh) {
            targetH = vh;
            targetW = vh * ar;
          }
          img.style.width = targetW + 'px';
          img.style.height = targetH + 'px';
          // Reset any transforms; container flex will center
          panzoom.reset({ animate: false });
        });
      };

      // Run fit only after the overlay image actually loaded to avoid snap-back
      if (img.complete) sizeToViewport();
      else img.addEventListener('load', function onload() { img.removeEventListener('load', onload); sizeToViewport(); });

      var root = container.closest('.glightbox-container') || document.body;
      var updateZoomed = function () {
        var s = panzoom.getScale();
        if (s > 1.01) root.classList.add('glb-zoomed'); else root.classList.remove('glb-zoomed');
      };

      container.addEventListener('wheel', function (event) {
        if (event.ctrlKey) return;
        event.preventDefault();
        try {
          panzoom.zoomWithWheel(event, { step: SCALE_STEP, maxScale: MAX_SCALE, minScale: MIN_SCALE, animate: false });
        } catch (e) {
          var scale = panzoom.getScale();
          var dir = event.deltaY < 0 ? 1 : -1;
          var target = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale + dir * SCALE_STEP));
          panzoom.zoom(target, { animate: false, focal: { clientX: event.clientX, clientY: event.clientY } });
        }
        updateZoomed();
      }, { passive: false });

      container.addEventListener('pointerdown', function () {
        img.classList.add('is-panning');
      });
      window.addEventListener('pointerup', function () {
        img.classList.remove('is-panning');
      });
      window.addEventListener('pointerleave', function () {
        img.classList.remove('is-panning');
      });

      container.addEventListener('dblclick', function (event) {
        event.preventDefault();
        var scale = panzoom.getScale();
        var targetScale = scale > 1 ? 1 : Math.min(MAX_SCALE, 2);
        panzoom.zoom(targetScale, {
          animate: true,
          focal: { clientX: event.clientX, clientY: event.clientY }
        });
        if (targetScale === 1) sizeToViewport();
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
