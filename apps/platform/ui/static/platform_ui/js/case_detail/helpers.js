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

  function updateNotes(container, notesPayload, options = {}) {
    if (!container || typeof notesPayload !== 'object' || notesPayload === null) return;
    const entries = Array.isArray(notesPayload.entries) ? notesPayload.entries : [];
    const listEl = container.querySelector('[data-job-notes-list]');
    if (listEl) {
      listEl.innerHTML = '';
      if (entries.length) {
        entries.forEach((entry, index) => {
          if (!entry || typeof entry !== 'object') return;
          const article = global.document.createElement('article');
          article.className = 'rounded border border-white/10 bg-slate-950/40 p-3';
          article.dataset.jobNote = entry.id || `note-${index}`;

          const header = global.document.createElement('div');
          header.className = 'flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400';

          const author = global.document.createElement('span');
          author.className = 'font-semibold text-slate-200';
          author.textContent = entry.created_by_label || entry.created_by || 'User';
          header.appendChild(author);

          if (entry.created_at) {
            const timeEl = global.document.createElement('time');
            timeEl.setAttribute('data-ts', entry.created_at);
            timeEl.setAttribute('data-ts-format', 'datetime');
            timeEl.textContent = entry.created_at;
            header.appendChild(timeEl);
          }

          article.appendChild(header);

          const body = global.document.createElement('p');
          body.className = 'mt-2 whitespace-pre-wrap text-sm text-slate-100';
          body.textContent = entry.text || '';
          article.appendChild(body);

          listEl.appendChild(article);
        });
      } else {
        const placeholder = global.document.createElement('p');
        placeholder.dataset.jobNotesEmpty = '1';
        placeholder.className = 'rounded border border-dashed border-white/10 bg-slate-950/20 px-3 py-2 text-sm text-slate-500';
        placeholder.textContent = 'No notes yet. Add the first note for your team.';
        listEl.appendChild(placeholder);
      }
    }

    const metaEl = container.querySelector('[data-job-notes-meta]');
    const updatedAt = notesPayload.updated_at || (entries[0] && entries[0].created_at) || '';
    const updatedBy = notesPayload.updated_by_label || notesPayload.updated_by || (entries[0] && (entries[0].created_by_label || entries[0].created_by)) || '';
    if (metaEl) {
      if (updatedAt) {
        metaEl.innerHTML = `Updated <time data-ts="${updatedAt}" data-ts-format="datetime">${updatedAt}</time>${updatedBy ? ` · <span class="font-semibold text-slate-200">${updatedBy}</span>` : ''}`;
      } else if (updatedBy) {
        metaEl.textContent = `Updated by ${updatedBy}`;
      } else {
        metaEl.textContent = entries.length ? 'Updated just now' : 'No notes yet.';
      }
    }

    const textarea = container.querySelector('[data-job-notes-input]');
    if (textarea && !options.preserveInput) {
      textarea.value = '';
    }

    if (typeof global.renderLocalTimes === 'function') {
      global.renderLocalTimes();
    }
  }

  caseDetail.helpers = {
    formatDuration,
    formatFileSize,
    truncateMiddle,
    ensureElementVisible,
    getCSRFToken,
    updateAudioPanel,
    updateNotes,
  };
})(window);
