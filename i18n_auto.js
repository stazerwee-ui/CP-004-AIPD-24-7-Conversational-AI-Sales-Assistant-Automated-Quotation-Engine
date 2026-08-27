/* ============================================================
 * i18n_auto.js — automatic translation of JavaScript-rendered content
 * ------------------------------------------------------------
 * THE PROBLEM THIS SOLVES
 *
 * setLanguage() walks [data-i18n] and translates matching elements. That
 * covers static HTML only. Anything a renderer builds after page load --
 * saved draft cards, planner add-on cards, chat quick-reply chips, toasts,
 * empty states -- carries no attribute, so it stays English. This is why the
 * bottom nav and price bar translate but the add-on cards above them do not.
 *
 * The obvious fix is to rewrite every renderer to call t(). That is hundreds
 * of edits across thousands of lines, and every new renderer written later
 * reintroduces the bug.
 *
 * THIS APPROACH INSTEAD
 *
 *   1. Build a reverse map: English string -> dictionary key, once.
 *   2. Walk text nodes. If a node's text exactly matches a known English
 *      string, translate it -- no attribute needed.
 *   3. Cache the ORIGINAL English on the node before replacing it, so
 *      switching zh -> ta -> en still works. Without this, the second switch
 *      would be translating already-translated text and would fail.
 *   4. A MutationObserver re-runs step 2 on any newly inserted subtree, so
 *      content rendered after a language switch is translated as it appears.
 *
 * WHAT THIS IS NOT
 *
 * It is not a replacement for real keys. It matches EXACT strings only --
 * no fuzzy matching, no partial replacement, no machine translation. A string
 * absent from the dictionary is left alone. It is a safety net for content
 * that would otherwise be missed, not a licence to stop adding keys.
 *
 * LOAD ORDER: after app.js, so I18N_TRANSLATIONS and setLanguage exist.
 * ============================================================ */

(function () {
  'use strict';

  // Never touch the director console. It is a staff tool and stays English
  // even when a family has selected Tamil.
  var EXCLUDED_ROOTS = [
    '#staff-dashboard-modal',
    '#admin-login-modal',
    '#staff-chat-modal'
  ];

  // Elements whose text is data, not copy.
  var EXCLUDED_TAGS = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, CODE: 1, PRE: 1, SVG: 1 };

  var reverseMap = null;   // englishString -> key
  var observer = null;
  var applying = false;    // guard: our own writes must not retrigger us

  // app.js declares `const I18N_TRANSLATIONS` and `const state`. A top-level
  // `const` in a classic script creates a global LEXICAL binding, which is NOT
  // a property of window -- so window.I18N_TRANSLATIONS is undefined even
  // though the bare identifier resolves fine. Always go through these.
  function dicts() {
    return (typeof I18N_TRANSLATIONS !== 'undefined') ? I18N_TRANSLATIONS : {};
  }
  function appState() {
    return (typeof state !== 'undefined') ? state : {};
  }

  function buildReverseMap() {
    if (reverseMap) return reverseMap;
    reverseMap = Object.create(null);
    var en = dicts().en || {};
    for (var key in en) {
      var val = en[key];
      if (typeof val !== 'string') continue;
      var trimmed = val.trim();
      // Very short strings match too loosely -- "None", "OK", "ID" would hit
      // unrelated places. Require some substance.
      if (trimmed.length < 4) continue;
      // First key wins; later duplicates are ambiguous so we skip them rather
      // than guess which one the author meant.
      if (!(trimmed in reverseMap)) reverseMap[trimmed] = key;
    }
    return reverseMap;
  }

  function isExcluded(node) {
    var el = node.nodeType === 3 ? node.parentElement : node;
    if (!el) return true;
    if (EXCLUDED_TAGS[el.tagName]) return true;
    for (var i = 0; i < EXCLUDED_ROOTS.length; i++) {
      if (el.closest && el.closest(EXCLUDED_ROOTS[i])) return true;
    }
    // Respect explicit opt-out, e.g. on a family's own typed text.
    if (el.closest && el.closest('[data-i18n-skip]')) return true;
    return false;
  }

  function currentDict() {
    var lang = appState().currentLanguage || 'en';
    var all = dicts();
    return { lang: lang, dict: all[lang] || all.en || {}, en: all.en || {} };
  }

  function translateTextNode(node, ctx, map) {
    var parent = node.parentElement;
    if (!parent) return;

    // Recover the original English. On first pass the node still holds it;
    // afterwards we read what we cached. This is what makes repeated
    // switching work -- we always translate FROM English, never from a
    // previous translation.
    var original = parent.dataset.i18nSrc;
    if (original === undefined) {
      original = node.nodeValue;
      var trimmedFirst = original.trim();
      if (!trimmedFirst || !(trimmedFirst in map)) return;  // unknown: leave alone
      parent.dataset.i18nSrc = original;
    }

    var trimmed = original.trim();
    var key = map[trimmed];
    if (!key) return;

    var translated = ctx.dict[key] || ctx.en[key] || trimmed;
    // Preserve surrounding whitespace so inline layout does not shift.
    var next = original.replace(trimmed, translated);
    if (node.nodeValue !== next) node.nodeValue = next;
  }

  function walk(root) {
    if (!root || applying) return;
    var ctx = currentDict();
    var map = buildReverseMap();
    applying = true;
    try {
      var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode: function (n) {
          if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
          if (isExcluded(n)) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_ACCEPT;
        }
      });
      var pending = [];
      var n;
      while ((n = walker.nextNode())) pending.push(n);
      for (var i = 0; i < pending.length; i++) {
        translateTextNode(pending[i], ctx, map);
      }
    } finally {
      applying = false;
    }
  }

  function startObserver() {
    if (observer || typeof MutationObserver === 'undefined') return;
    observer = new MutationObserver(function (mutations) {
      if (applying) return;
      for (var i = 0; i < mutations.length; i++) {
        var added = mutations[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          var node = added[j];
          if (node.nodeType === 1) {
            // A freshly rendered subtree: its cached originals are stale.
            if (node.dataset) delete node.dataset.i18nSrc;
            walk(node);
          } else if (node.nodeType === 3 && !isExcluded(node)) {
            walk(node.parentElement);
          }
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Wrap setLanguage so a switch also re-walks the live DOM. Chained rather
  // than replaced, so the existing implementation keeps doing its work.
  function hookSetLanguage() {
    // setLanguage is a function DECLARATION, so unlike the consts above it
    // does become a window property, and reassigning it also changes what the
    // bare `setLanguage(...)` calls inside app.js resolve to.
    if (typeof window.setLanguage !== 'function' || window.setLanguage.__i18nAuto) return;
    var original = window.setLanguage;
    var wrapped = function (lang) {
      var result = original.apply(this, arguments);
      // Deliberately do NOT clear data-i18n-src here. That cache holds the
      // original English, and it is the only thing that makes a second switch
      // work: without it the next walk would read already-translated text,
      // fail to find it in the English->key map, and leave the node frozen in
      // whichever language was applied first. Stale caches on re-rendered
      // subtrees are handled by the MutationObserver instead.
      walk(document.body);
      return result;
    };
    wrapped.__i18nAuto = true;
    window.setLanguage = wrapped;
  }

  function init() {
    hookSetLanguage();
    walk(document.body);
    startObserver();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Exposed for debugging: window.__i18nAudit() lists visible English strings
  // that have no dictionary entry, so you can see what still needs a key.
  window.__i18nAudit = function () {
    var map = buildReverseMap();
    var missing = {};
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (isExcluded(n)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var n;
    while ((n = walker.nextNode())) {
      var t = n.nodeValue.trim();
      if (t.length < 4) continue;
      if (!/[A-Za-z]{3}/.test(t)) continue;     // already non-Latin: fine
      if (t in map) continue;                    // has a key
      if (n.parentElement && n.parentElement.dataset.i18nSrc) continue;
      missing[t] = (missing[t] || 0) + 1;
    }
    var list = Object.keys(missing).sort();
    console.log('Untranslated visible strings: ' + list.length);
    list.forEach(function (s) { console.log('  ' + s.slice(0, 90)); });
    return list;
  };
})();
