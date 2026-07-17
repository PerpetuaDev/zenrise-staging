/**
 * Zenrise — on-brand date picker.
 *
 * Progressively enhances any <input type="date"> on the page: hides the
 * native control and renders a custom calendar popup styled to match the
 * brand (cream surface, sharp corners, mono day labels, display dates).
 *
 * The underlying input still holds the canonical ISO value and dispatches
 * a `change` event when a date is selected, so existing form state logic
 * keeps working untouched.
 *
 * Bilingual: month and day-of-week labels follow window.ZenriseI18n.get().
 * Re-renders on language change.
 */
(function () {
  var MONTHS = {
    en: ['January','February','March','April','May','June','July','August','September','October','November','December'],
    ja: ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
  };
  var DOW = {
    en: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
    ja: ['月','火','水','木','金','土','日']
  };
  var PLACEHOLDER = {
    en: 'Choose a date',
    ja: '日付を選ぶ'
  };
  var MONTHS_SHORT = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var RANGE_PLACEHOLDER = {
    en: 'Choose your dates',
    ja: '日程を選ぶ'
  };

  function lang() {
    return (window.ZenriseI18n && window.ZenriseI18n.get()) || 'en';
  }

  function pad(n) { return n < 10 ? '0' + n : '' + n; }

  function parseISO(s) {
    if (!s) return null;
    var p = s.split('-');
    if (p.length !== 3) return null;
    return { y: +p[0], m: +p[1] - 1, d: +p[2] };
  }
  function toISO(c) {
    return c.y + '-' + pad(c.m + 1) + '-' + pad(c.d);
  }

  function formatLong(c) {
    var l = lang();
    if (!c) return PLACEHOLDER[l];
    if (l === 'ja') {
      return c.y + '年' + (c.m + 1) + '月' + c.d + '日';
    }
    return MONTHS.en[c.m] + ' ' + c.d + ', ' + c.y;
  }

  function monthLabel(y, m) {
    return lang() === 'ja' ? (y + '年 ' + MONTHS.ja[m]) : (MONTHS.en[m] + ' ' + y);
  }

  // ────────────────────────────────────────────────────────────
  // Styles
  // ────────────────────────────────────────────────────────────
  function injectStyles() {
    if (document.getElementById('zenrise-dp-style')) return;
    var s = document.createElement('style');
    s.id = 'zenrise-dp-style';
    s.textContent = [
      '.zp { position: relative; }',
      // hide the native input but keep it focusable for accessibility / form state
      '.zp input[type="date"] { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; pointer-events: none; }',

      // trigger — looks like the existing form inputs (underline + display type)
      '.zp-trigger { width: 100%; background: transparent; border: none; border-bottom: 1px solid rgba(41,65,56,0.28); padding: 10px 0 14px; font-family: "Optima Nova LT Pro","Optima",serif; font-size: 28px; color: #294138; text-align: left; cursor: pointer; display: flex; justify-content: space-between; align-items: baseline; transition: border-color 180ms ease; font-weight: 400; }',
      '.zp-trigger:hover { border-bottom-color: #294138; }',
      '.zp.open .zp-trigger { border-bottom-color: #294138; }',
      '.zp-trigger .zp-icon { font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 11px; letter-spacing: 0.2em; color: rgba(41,65,56,0.5); text-transform: uppercase; align-self: center; padding-bottom: 4px; }',
      '.zp-trigger.empty { color: rgba(41,65,56,0.35); }',

      // popup — cream surface, sharp corners
      '.zp-pop { position: absolute; left: 0; top: calc(100% + 12px); width: 380px; max-width: calc(100vw - 40px); box-sizing: border-box; background: #F7F4EA; border: 1px solid rgba(41,65,56,0.14); box-shadow: 0 32px 64px -12px rgba(41,65,56,0.22), 0 4px 12px rgba(41,65,56,0.04); padding: 28px 28px 24px; z-index: 100; opacity: 0; transform: translateY(-6px); pointer-events: none; transition: opacity 200ms cubic-bezier(.2,.6,.2,1), transform 200ms cubic-bezier(.2,.6,.2,1); border-radius: 0; }',
      '.zp.open .zp-pop { opacity: 1; transform: none; pointer-events: auto; }',

      // header — month label between prev/next nav
      '.zp-head { display: grid; grid-template-columns: 36px 1fr 36px; align-items: center; margin-bottom: 22px; }',
      '.zp-month { font-family: "Optima Nova LT Pro","Optima",serif; font-size: 22px; color: #294138; text-align: center; letter-spacing: -0.005em; }',
      '.zp-nav { width: 36px; height: 36px; background: transparent; border: 1px solid transparent; color: #294138; font-size: 14px; cursor: pointer; display: grid; place-items: center; transition: background 160ms ease, border-color 160ms ease; padding: 0; border-radius: 0; }',
      '.zp-nav:hover { background: rgba(41,65,56,0.06); border-color: rgba(41,65,56,0.18); }',
      '.zp-nav:focus-visible { outline: none; border-color: #294138; }',

      // day-of-week row
      '.zp-dow { display: grid; grid-template-columns: repeat(7, 1fr); font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(41,65,56,0.5); margin-bottom: 6px; border-bottom: 1px solid rgba(41,65,56,0.08); padding-bottom: 8px; }',
      '.zp-dow span { text-align: center; }',

      // days grid
      '.zp-days { display: grid; grid-template-columns: repeat(7, 1fr); margin-top: 6px; }',
      '.zp-day { background: transparent; border: none; font-family: "Optima Nova LT Pro","Optima",serif; font-size: 18px; color: #294138; height: 42px; cursor: pointer; transition: background 140ms ease, color 140ms ease; padding: 0; border-radius: 0; position: relative; }',
      '.zp-day:hover:not(.other):not(.on) { background: rgba(41,65,56,0.06); }',
      '.zp-day.other { color: rgba(41,65,56,0.2); cursor: pointer; }',
      '.zp-day.other:hover { background: rgba(41,65,56,0.03); }',
      '.zp-day.on { background: #294138; color: #F7F4EA; }',
      '.zp-day.in-range { background: rgba(41,65,56,0.10); }',
      '.zp-day.in-range:hover { background: rgba(41,65,56,0.16); }',
      '.zp-day.today::after { content: ""; position: absolute; left: 50%; bottom: 6px; transform: translateX(-50%); width: 3px; height: 3px; background: currentColor; border-radius: 50%; opacity: 0.55; }',
      '.zp-day.on.today::after { background: #F7F4EA; opacity: 0.75; }',

      // footer — clear button
      '.zp-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 18px; padding-top: 16px; border-top: 1px solid rgba(41,65,56,0.08); }',
      '.zp-today, .zp-clear { background: transparent; border: none; font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 10px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(41,65,56,0.6); cursor: pointer; padding: 4px 0; transition: color 140ms ease; }',
      '.zp-today:hover, .zp-clear:hover { color: #294138; }',

      // range-mode confirm — filled ink, unmissable next to the quiet Clear
      '.zp-confirm { background: #294138; color: #F7F4EA; border: none; font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 10px; letter-spacing: 0.24em; text-transform: uppercase; padding: 12px 22px; cursor: pointer; border-radius: 0; transition: background 160ms ease; }',
      '.zp-confirm:hover { background: #1f3328; }',

      // range trigger labels run long ("Sep 24 – Oct 2, 2026") — step the
      // display size down on phones so they hold one line
      '@media (max-width: 599px) { .zp-trigger { font-size: 22px; } }'
    ].join('\n');
    document.head.appendChild(s);
  }

  // ────────────────────────────────────────────────────────────
  // Per-input enhancement
  // ────────────────────────────────────────────────────────────
  function enhance(input) {
    if (input.dataset.zpReady) return;
    input.dataset.zpReady = '1';

    // wrap
    var wrap = document.createElement('div');
    wrap.className = 'zp';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    // trigger
    var trig = document.createElement('button');
    trig.type = 'button';
    trig.className = 'zp-trigger empty';
    trig.innerHTML = '<span class="zp-value">— — —</span><span class="zp-icon">' + (lang() === 'ja' ? '日付' : 'Date') + '</span>';
    wrap.appendChild(trig);

    // popup
    var pop = document.createElement('div');
    pop.className = 'zp-pop';
    pop.innerHTML =
      '<div class="zp-head">' +
        '<button class="zp-nav" data-zp-prev type="button" aria-label="Previous month">←</button>' +
        '<span class="zp-month"></span>' +
        '<button class="zp-nav" data-zp-next type="button" aria-label="Next month">→</button>' +
      '</div>' +
      '<div class="zp-dow"></div>' +
      '<div class="zp-days"></div>' +
      '<div class="zp-foot">' +
        '<button class="zp-today" type="button" data-zp-today></button>' +
        '<button class="zp-clear" type="button" data-zp-clear></button>' +
      '</div>';
    wrap.appendChild(pop);

    // ────── state ──────
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var todayISO = toISO({ y: today.getFullYear(), m: today.getMonth(), d: today.getDate() });

    var view = { y: today.getFullYear(), m: today.getMonth() };

    function selected() { return parseISO(input.value); }

    // ────── render ──────
    function render() {
      // month label
      pop.querySelector('.zp-month').textContent = monthLabel(view.y, view.m);

      // day-of-week labels
      var dowLabels = DOW[lang()];
      pop.querySelector('.zp-dow').innerHTML = dowLabels.map(function (d) {
        return '<span>' + d + '</span>';
      }).join('');

      // foot buttons
      pop.querySelector('[data-zp-today]').textContent = lang() === 'ja' ? '今日' : 'Today';
      pop.querySelector('[data-zp-clear]').textContent = lang() === 'ja' ? 'クリア' : 'Clear';

      // grid
      var firstDay = new Date(view.y, view.m, 1);
      var lastDay = new Date(view.y, view.m + 1, 0);
      // Monday-first: shift Sunday(0)..Saturday(6) → Mon(0)..Sun(6)
      var startDow = (firstDay.getDay() + 6) % 7;
      var daysInMonth = lastDay.getDate();
      var prevLast = new Date(view.y, view.m, 0).getDate();

      var sel = selected();

      var cells = [];
      // leading days from prev month
      for (var i = 0; i < startDow; i++) {
        var d = prevLast - startDow + 1 + i;
        cells.push({ d: d, y: view.m === 0 ? view.y - 1 : view.y, m: view.m === 0 ? 11 : view.m - 1, other: true });
      }
      // current month
      for (var dd = 1; dd <= daysInMonth; dd++) {
        cells.push({ d: dd, y: view.y, m: view.m, other: false });
      }
      // trailing
      var nextD = 1;
      while (cells.length < 42) {
        cells.push({ d: nextD++, y: view.m === 11 ? view.y + 1 : view.y, m: view.m === 11 ? 0 : view.m + 1, other: true });
      }

      var html = cells.map(function (c) {
        var iso = toISO(c);
        var classes = ['zp-day'];
        if (c.other) classes.push('other');
        if (sel && sel.y === c.y && sel.m === c.m && sel.d === c.d) classes.push('on');
        if (iso === todayISO) classes.push('today');
        return '<button type="button" class="' + classes.join(' ') + '" data-zp-pick="' + iso + '">' + c.d + '</button>';
      }).join('');

      pop.querySelector('.zp-days').innerHTML = html;

      // trigger display
      var v = trig.querySelector('.zp-value');
      if (sel) {
        trig.classList.remove('empty');
        v.textContent = formatLong(sel);
      } else {
        trig.classList.add('empty');
        v.textContent = PLACEHOLDER[lang()];
      }
      // icon label
      var ic = trig.querySelector('.zp-icon');
      if (ic) ic.textContent = lang() === 'ja' ? '日付' : 'Date';
    }

    // ────── events ──────
    function closeAllOthers() {
      document.querySelectorAll('.zp.open').forEach(function (z) {
        if (z !== wrap) z.classList.remove('open');
      });
    }

    trig.addEventListener('click', function (e) {
      e.stopPropagation();
      closeAllOthers();
      var open = wrap.classList.toggle('open');
      if (open) {
        // jump view to the selected month, or today
        var s = selected();
        if (s) { view.y = s.y; view.m = s.m; }
        else   { view.y = today.getFullYear(); view.m = today.getMonth(); }
        render();
      }
    });

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) wrap.classList.remove('open');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') wrap.classList.remove('open');
    });

    pop.querySelector('[data-zp-prev]').addEventListener('click', function (e) {
      e.stopPropagation();
      if (view.m === 0) { view.m = 11; view.y--; } else { view.m--; }
      render();
    });
    pop.querySelector('[data-zp-next]').addEventListener('click', function (e) {
      e.stopPropagation();
      if (view.m === 11) { view.m = 0; view.y++; } else { view.m++; }
      render();
    });
    pop.querySelector('[data-zp-today]').addEventListener('click', function (e) {
      e.stopPropagation();
      var t = { y: today.getFullYear(), m: today.getMonth(), d: today.getDate() };
      input.value = toISO(t);
      input.dispatchEvent(new Event('change', { bubbles: true }));
      view.y = t.y; view.m = t.m;
      render();
      wrap.classList.remove('open');
    });
    pop.querySelector('[data-zp-clear]').addEventListener('click', function (e) {
      e.stopPropagation();
      input.value = '';
      input.dispatchEvent(new Event('change', { bubbles: true }));
      render();
    });

    // delegated day-click
    pop.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-zp-pick]');
      if (!btn) return;
      e.stopPropagation();
      input.value = btn.dataset.zpPick;
      input.dispatchEvent(new Event('change', { bubbles: true }));
      var s = selected();
      if (s) { view.y = s.y; view.m = s.m; }
      render();
      wrap.classList.remove('open');
    });

    // also re-render if the input is set programmatically (e.g. on language toggle)
    input.addEventListener('change', function () { render(); });

    // language change → re-render labels
    if (window.ZenriseI18n) {
      window.ZenriseI18n.onChange(function () { render(); });
    }

    render();
  }

  // ────────────────────────────────────────────────────────────
  // Range enhancement — one trigger + one calendar driving TWO date
  // inputs (from/to) inside a [data-zp-range] container. First pick
  // sets the start, second the end (an earlier pick swaps), and both
  // inputs get `change` events so existing form state logic is
  // untouched.
  // ────────────────────────────────────────────────────────────
  function enhanceRange(container) {
    if (container.dataset.zpReady) return;
    var inputs = container.querySelectorAll('input[type="date"]');
    if (inputs.length < 2) return;
    container.dataset.zpReady = '1';
    var from = inputs[0], to = inputs[1];
    from.dataset.zpReady = '1';
    to.dataset.zpReady = '1';

    var wrap = document.createElement('div');
    wrap.className = 'zp';
    from.parentNode.insertBefore(wrap, from);
    wrap.appendChild(from);
    wrap.appendChild(to);

    var trig = document.createElement('button');
    trig.type = 'button';
    trig.className = 'zp-trigger empty';
    // no .zp-icon here — the field's own "Dates" label already says it
    trig.innerHTML = '<span class="zp-value"></span>';
    wrap.appendChild(trig);

    var pop = document.createElement('div');
    pop.className = 'zp-pop';
    pop.innerHTML =
      '<div class="zp-head">' +
        '<button class="zp-nav" data-zp-prev type="button" aria-label="Previous month">←</button>' +
        '<span class="zp-month"></span>' +
        '<button class="zp-nav" data-zp-next type="button" aria-label="Next month">→</button>' +
      '</div>' +
      '<div class="zp-dow"></div>' +
      '<div class="zp-days"></div>' +
      '<div class="zp-foot">' +
        '<button class="zp-clear" type="button" data-zp-clear></button>' +
        '<button class="zp-confirm" type="button" data-zp-confirm></button>' +
      '</div>';
    wrap.appendChild(pop);

    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var todayISO = toISO({ y: today.getFullYear(), m: today.getMonth(), d: today.getDate() });
    var view = { y: today.getFullYear(), m: today.getMonth() };

    function sel() { return { a: parseISO(from.value), b: parseISO(to.value) }; }
    function cmp(c1, c2) { return (c1.y - c2.y) || (c1.m - c2.m) || (c1.d - c2.d); }
    function fire(el) { el.dispatchEvent(new Event('change', { bubbles: true })); }

    function label(s) {
      var l = lang();
      if (!s.a) return RANGE_PLACEHOLDER[l];
      if (!s.b) return l === 'ja' ? formatLong(s.a) + ' 〜' : formatLong(s.a) + ' – …';
      if (l === 'ja') {
        if (s.a.y === s.b.y) {
          if (s.a.m === s.b.m) return s.a.y + '年' + (s.a.m + 1) + '月' + s.a.d + '日〜' + s.b.d + '日';
          return s.a.y + '年' + (s.a.m + 1) + '月' + s.a.d + '日〜' + (s.b.m + 1) + '月' + s.b.d + '日';
        }
        return formatLong(s.a) + '〜' + formatLong(s.b);
      }
      var A = MONTHS_SHORT[s.a.m], B = MONTHS_SHORT[s.b.m];
      if (s.a.y === s.b.y) {
        if (s.a.m === s.b.m) return A + ' ' + s.a.d + ' – ' + s.b.d + ', ' + s.a.y;
        return A + ' ' + s.a.d + ' – ' + B + ' ' + s.b.d + ', ' + s.a.y;
      }
      return A + ' ' + s.a.d + ', ' + s.a.y + ' – ' + B + ' ' + s.b.d + ', ' + s.b.y;
    }

    function render() {
      pop.querySelector('.zp-month').textContent = monthLabel(view.y, view.m);
      pop.querySelector('.zp-dow').innerHTML = DOW[lang()].map(function (d) {
        return '<span>' + d + '</span>';
      }).join('');
      pop.querySelector('[data-zp-clear]').textContent = lang() === 'ja' ? 'クリア' : 'Clear';
      pop.querySelector('[data-zp-confirm]').textContent = lang() === 'ja' ? '確定' : 'Confirm';

      var firstDay = new Date(view.y, view.m, 1);
      var lastDay = new Date(view.y, view.m + 1, 0);
      var startDow = (firstDay.getDay() + 6) % 7;
      var daysInMonth = lastDay.getDate();
      var prevLast = new Date(view.y, view.m, 0).getDate();

      var s = sel();

      var cells = [];
      for (var i = 0; i < startDow; i++) {
        var d = prevLast - startDow + 1 + i;
        cells.push({ d: d, y: view.m === 0 ? view.y - 1 : view.y, m: view.m === 0 ? 11 : view.m - 1, other: true });
      }
      for (var dd = 1; dd <= daysInMonth; dd++) {
        cells.push({ d: dd, y: view.y, m: view.m, other: false });
      }
      var nextD = 1;
      while (cells.length < 42) {
        cells.push({ d: nextD++, y: view.m === 11 ? view.y + 1 : view.y, m: view.m === 11 ? 0 : view.m + 1, other: true });
      }

      pop.querySelector('.zp-days').innerHTML = cells.map(function (c) {
        var iso = toISO(c);
        var classes = ['zp-day'];
        if (c.other) classes.push('other');
        var isA = s.a && cmp(c, s.a) === 0;
        var isB = s.b && cmp(c, s.b) === 0;
        if (isA || isB) classes.push('on');
        else if (s.a && s.b && cmp(c, s.a) > 0 && cmp(c, s.b) < 0) classes.push('in-range');
        if (iso === todayISO) classes.push('today');
        return '<button type="button" class="' + classes.join(' ') + '" data-zp-pick="' + iso + '">' + c.d + '</button>';
      }).join('');

      var v = trig.querySelector('.zp-value');
      trig.classList.toggle('empty', !s.a && !s.b);
      v.textContent = label(s);
    }

    trig.addEventListener('click', function (e) {
      e.stopPropagation();
      document.querySelectorAll('.zp.open').forEach(function (z) {
        if (z !== wrap) z.classList.remove('open');
      });
      var open = wrap.classList.toggle('open');
      if (open) {
        var s = sel();
        if (s.a) { view.y = s.a.y; view.m = s.a.m; }
        else { view.y = today.getFullYear(); view.m = today.getMonth(); }
        render();
      }
    });

    document.addEventListener('click', function (e) {
      if (!wrap.contains(e.target)) wrap.classList.remove('open');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') wrap.classList.remove('open');
    });

    pop.querySelector('[data-zp-prev]').addEventListener('click', function (e) {
      e.stopPropagation();
      if (view.m === 0) { view.m = 11; view.y--; } else { view.m--; }
      render();
    });
    pop.querySelector('[data-zp-next]').addEventListener('click', function (e) {
      e.stopPropagation();
      if (view.m === 11) { view.m = 0; view.y++; } else { view.m++; }
      render();
    });
    pop.querySelector('[data-zp-clear]').addEventListener('click', function (e) {
      e.stopPropagation();
      from.value = '';
      to.value = '';
      fire(from); fire(to);
      render();
    });

    pop.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-zp-pick]');
      if (!btn) return;
      e.stopPropagation();
      var iso = btn.dataset.zpPick;
      var c = parseISO(iso);
      var s = sel();
      if (!s.a || (s.a && s.b)) {
        // start a new range
        from.value = iso;
        to.value = '';
        fire(from); fire(to);
        render();
      } else {
        // complete it — picking before the start swaps the endpoints.
        // Stays open; Confirm closes.
        if (cmp(c, s.a) < 0) {
          to.value = toISO(s.a);
          from.value = iso;
        } else {
          to.value = iso;
        }
        fire(from); fire(to);
        render();
      }
    });

    pop.querySelector('[data-zp-confirm]').addEventListener('click', function (e) {
      e.stopPropagation();
      wrap.classList.remove('open');
    });

    from.addEventListener('change', render);
    to.addEventListener('change', render);
    if (window.ZenriseI18n) {
      window.ZenriseI18n.onChange(function () { render(); });
    }

    render();
  }

  function boot() {
    injectStyles();
    document.querySelectorAll('[data-zp-range]').forEach(enhanceRange);
    document.querySelectorAll('input[type="date"]').forEach(enhance);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
