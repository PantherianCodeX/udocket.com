(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});
  const caseDetail = (platformUI.caseDetail = platformUI.caseDetail || {});
  if (caseDetail.helpers) {
    return;
  }

  function formatDuration(value) {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds < 0) return null;
    if (seconds >= 600) return `${Math.round(seconds)} s`;
    if (seconds >= 60) return `${seconds.toFixed(1)} s`;
    if (seconds >= 10) return `${seconds.toFixed(1)} s`;
    return `${seconds.toFixed(2)} s`;
  }

  function formatFileSize(bytes) {
    const size = Number(bytes);
    if (!Number.isFinite(size) || size < 0) return null;
    const units = ["bytes", "KB", "MB", "GB", "TB"];
    let value = size;
    let idx = 0;
    while (value >= 1024 && idx < units.length - 1) {
      value /= 1024;
      idx += 1;
    }
    const formatted = idx === 0 ? Math.round(value).toString() : value >= 10 ? value.toFixed(0) : value.toFixed(1);
    if (idx === 0) {
      return `${formatted} ${Number(formatted) === 1 ? "byte" : "bytes"}`;
    }
    return `${formatted} ${units[idx]}`;
  }

  function truncateMiddle(input, head = 28, tail = 16) {
    if (typeof input !== "string") return input;
    if (input.length <= head + tail + 3) return input;
    return `${input.slice(0, head)}…${input.slice(-tail)}`;
  }

  function ensureElementVisible(el, align = "nearest") {
    if (!el || !el.getBoundingClientRect) return;
    const rect = el.getBoundingClientRect();
    const viewHeight = global.innerHeight || global.document.documentElement.clientHeight;
    const padding = Math.min(120, Math.max(48, viewHeight * 0.15));
    const topLimit = padding;
    const bottomLimit = viewHeight - padding;
    const fullyVisible = rect.top >= topLimit && rect.bottom <= bottomLimit;
    if (fullyVisible) {
      return;
    }
    const overTop = rect.top - topLimit;
    const overBottom = rect.bottom - bottomLimit;
    let delta = 0;
    if (overTop < 0) {
      delta = overTop;
    } else if (overBottom > 0) {
      delta = overBottom;
    }
    if (delta && typeof global.scrollBy === "function") {
      global.scrollBy({ top: delta, behavior: "smooth" });
    } else if (el.scrollIntoView) {
      el.scrollIntoView({ behavior: "smooth", block: align, inline: "nearest" });
    }
  }

  function getCSRFToken() {
    const match = global.document.cookie.match(/csrftoken=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
    const meta = global.document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") || "" : "";
  }

  function updateAudioPanel(panel, payload) {
    if (!panel || !payload) return;
    const sizeBytes = payload.size_bytes_local ?? payload.size_bytes_remote ?? payload.audio_size_bytes ?? null;
    const hashValue = payload.sha256 || payload.remote_sha256 || payload.audio_sha256 || null;
    const values = {
      original_name: payload.original_name || payload.audio_file || null,
      duration: formatDuration(payload.duration_s ?? payload.audio_duration_s),
      channels:
        payload.channels != null
          ? String(payload.channels)
          : payload.audio_channels != null
            ? String(payload.audio_channels)
            : null,
      sample_rate:
        payload.sample_rate_hz != null
          ? `${payload.sample_rate_hz} Hz`
          : payload.audio_sample_rate_hz != null
            ? `${payload.audio_sample_rate_hz} Hz`
            : null,
      bitrate:
        payload.bitrate_kbps != null
          ? `${payload.bitrate_kbps} kbps`
          : payload.audio_bitrate_kbps != null
            ? `${payload.audio_bitrate_kbps} kbps`
            : null,
      codec: payload.codec || payload.audio_codec || null,
      layout: payload.channel_layout || payload.audio_channel_layout || null,
      mime: payload.mime || payload.audio_mime || null,
      path: payload.path || payload.audio_path || null,
      size: sizeBytes != null ? formatFileSize(sizeBytes) : null,
      hash: hashValue,
    };

    Object.entries(values).forEach(([key, rawValue]) => {
      const field = panel.querySelector(`[data-audio-field="${key}"]`);
      if (!field) return;

      if (key === "path") {
        if (rawValue) {
          field.textContent = truncateMiddle(String(rawValue));
          field.setAttribute("data-copy-text", String(rawValue));
          field.setAttribute("title", String(rawValue));
          field.classList.add("clip-inline", "font-mono", "text-[11px]", "text-primary-100");
          field.classList.remove("text-slate-500");
        } else {
          field.textContent = "—";
          field.removeAttribute("data-copy-text");
          field.removeAttribute("title");
          field.classList.remove("clip-inline", "font-mono", "text-[11px]", "text-primary-100");
          field.classList.add("text-slate-500");
        }
        return;
      }

      if (key === "hash") {
        if (rawValue) {
          const hashText = String(rawValue);
          const display = hashText.length >= 12 ? `${hashText.slice(0, 8)}…${hashText.slice(-4)}` : hashText;
          field.textContent = display;
          field.setAttribute("data-copy-text", hashText);
          field.setAttribute("title", hashText);
          field.classList.add("font-mono", "text-[11px]", "text-primary-100");
          field.classList.remove("text-slate-500");
        } else {
          field.textContent = "Not recorded";
          field.removeAttribute("data-copy-text");
          field.removeAttribute("title");
          field.classList.remove("font-mono", "text-[11px]", "text-primary-100");
          field.classList.add("text-slate-500");
        }
        return;
      }

      field.textContent = rawValue || "—";
    });
  }

  caseDetail.helpers = {
    formatDuration,
    formatFileSize,
    truncateMiddle,
    ensureElementVisible,
    getCSRFToken,
    updateAudioPanel,
  };
})(window);
