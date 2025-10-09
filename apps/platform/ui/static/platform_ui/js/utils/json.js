(function (global) {
  const platformUI = (global.platformUI = global.platformUI || {});

  function isPlainObject(value) {
    return (
      value !== null &&
      typeof value === 'object' &&
      Object.prototype.toString.call(value) === '[object Object]'
    );
  }

  function sortKeysDeep(value) {
    if (Array.isArray(value)) {
      return value.map(sortKeysDeep);
    }
    if (isPlainObject(value)) {
      const out = {};
      Object.keys(value)
        .sort()
        .forEach((k) => {
          out[k] = sortKeysDeep(value[k]);
        });
      return out;
    }
    return value;
  }

  function parse(text, fallback = null) {
    try {
      if (typeof text !== 'string') return fallback;
      const trimmed = text.trim();
      if (!trimmed) return fallback;
      return JSON.parse(trimmed);
    } catch (_) {
      return fallback;
    }
  }

  function stringify(value, pretty = false) {
    try {
      return JSON.stringify(value, null, pretty ? 2 : undefined);
    } catch (_) {
      return pretty ? 'null' : 'null';
    }
  }

  function stringifyStable(value, pretty = false) {
    try {
      const normalized = sortKeysDeep(value);
      return JSON.stringify(normalized, null, pretty ? 2 : undefined);
    } catch (_) {
      return pretty ? 'null' : 'null';
    }
  }

  const jsonUtils = { parse, stringify, stringifyStable };
  platformUI.json = platformUI.json || {};
  // Do not clobber existing implementations; fill missing ones.
  if (typeof platformUI.json.parse !== 'function') platformUI.json.parse = parse;
  if (typeof platformUI.json.stringify !== 'function') platformUI.json.stringify = stringify;
  if (typeof platformUI.json.stringifyStable !== 'function') platformUI.json.stringifyStable = stringifyStable;
})(window);

