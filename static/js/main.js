/* StayNest - main.js
   Vanilla JavaScript enhancements. Every page still works with normal
   server-rendered forms if this file fails to load. */
(function () {
  'use strict';

  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.prototype.slice.call((ctx || document).querySelectorAll(sel)); };

  /* 1. Mobile navigation ------------------------------------------------- */
  var navToggle = $('[data-nav-toggle]');
  var nav = $('#site-nav');
  function setNav(open) {
    if (!navToggle || !nav) return;
    nav.classList.toggle('is-open', open);
    navToggle.setAttribute('aria-expanded', String(open));
  }
  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      setNav(navToggle.getAttribute('aria-expanded') !== 'true');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && navToggle.getAttribute('aria-expanded') === 'true') {
        setNav(false);
        navToggle.focus();
      }
    });
    document.addEventListener('click', function (e) {
      if (navToggle.getAttribute('aria-expanded') === 'true' &&
          !nav.contains(e.target) && !navToggle.contains(e.target)) {
        setNav(false);
      }
    });
    var wide = window.matchMedia('(min-width: 861px)');
    var onWide = function (m) { if (m.matches) setNav(false); };
    if (wide.addEventListener) wide.addEventListener('change', onWide);
    else if (wide.addListener) wide.addListener(onWide);
  }

  /* 2. Filter panel toggle (property list, mobile) ------------------------- */
  var filterToggle = $('[data-filter-toggle]');
  var filters = $('#filters');
  if (filterToggle && filters) {
    var hasActive = window.location.search.replace(/[?&]page=\d+/, '').length > 1;
    if (hasActive && window.matchMedia('(max-width: 900px)').matches) {
      /* keep panel closed on load, but tell the user filters are applied */
      filterToggle.textContent = 'Filters (applied)';
    }
    filterToggle.addEventListener('click', function () {
      var open = !filters.classList.contains('is-open');
      filters.classList.toggle('is-open', open);
      filterToggle.setAttribute('aria-expanded', String(open));
      if (open) {
        var first = $('input, select', filters);
        if (first) first.focus({ preventScroll: true });
        filters.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  }

  /* 3. Auto-submit sort select -------------------------------------------- */
  $$('[data-autosubmit]').forEach(function (el) {
    el.addEventListener('change', function () {
      if (el.form) el.form.submit();
    });
  });

  /* 4. Dismissible messages ------------------------------------------------ */
  function dismiss(alertEl) {
    alertEl.classList.add('is-hiding');
    window.setTimeout(function () { if (alertEl.parentNode) alertEl.parentNode.removeChild(alertEl); }, 260);
  }
  $$('[data-message]').forEach(function (m) {
    var btn = $('[data-dismiss]', m);
    if (btn) btn.addEventListener('click', function () { dismiss(m); });
    var level = m.getAttribute('data-level');
    if (level === 'success' || level === 'info') {
      window.setTimeout(function () { dismiss(m); }, 8000);
    }
  });

  /* 5. Confirmation dialog + double-submit protection ------------------------ */
  var dialog = $('#confirm-dialog');
  var dialogText = $('#confirm-text');
  var dialogOk = $('#confirm-ok');
  var dialogTitle = $('#confirm-title');

  function lockForm(form) {
    window.setTimeout(function () {
      $$('button[type="submit"], input[type="submit"]', form).forEach(function (b) {
        b.disabled = true;
        b.setAttribute('aria-disabled', 'true');
      });
    }, 0);
  }

  function askConfirm(form, done) {
    var message = form.getAttribute('data-confirm');
    var label = form.getAttribute('data-confirm-label') || 'Confirm';
    var danger = form.hasAttribute('data-confirm-danger');

    if (dialog && typeof dialog.showModal === 'function') {
      dialogTitle.textContent = label;
      dialogText.textContent = message;
      dialogOk.textContent = label;
      dialogOk.classList.toggle('btn--danger', danger);
      dialogOk.classList.toggle('btn--primary', !danger);
      dialog.returnValue = '';
      dialog.addEventListener('close', function onClose() {
        dialog.removeEventListener('close', onClose);
        done(dialog.returnValue === 'ok');
      });
      dialog.showModal();
      dialogOk.focus();
    } else {
      done(window.confirm(message));
    }
  }

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || form.tagName !== 'FORM' || form === (dialog && dialog.querySelector('form'))) return;

    if (form.hasAttribute('data-confirm') && form.getAttribute('data-confirmed') !== 'true') {
      e.preventDefault();
      askConfirm(form, function (ok) {
        if (ok) {
          form.setAttribute('data-confirmed', 'true');
          lockForm(form);
          form.submit();
        }
      });
      return;
    }
    if (!e.defaultPrevented) lockForm(form);
  });

  /* Re-enable buttons when the page is restored from the back/forward cache. */
  window.addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    $$('form').forEach(function (f) {
      f.removeAttribute('data-confirmed');
      $$('button[type="submit"]', f).forEach(function (b) { b.disabled = false; b.removeAttribute('aria-disabled'); });
    });
  });

  /* 6. Property gallery ------------------------------------------------------ */
  $$('[data-gallery]').forEach(function (gallery) {
    var main = $('[data-gallery-main]', gallery);
    var thumbs = $$('[data-gallery-thumb]', gallery);
    if (!main || !thumbs.length) return;

    function select(thumb) {
      main.src = thumb.getAttribute('data-full');
      main.alt = thumb.getAttribute('data-alt') || main.alt;
      thumbs.forEach(function (t) { t.setAttribute('aria-current', t === thumb ? 'true' : 'false'); });
    }
    thumbs.forEach(function (thumb, i) {
      thumb.addEventListener('click', function () { select(thumb); });
      thumb.addEventListener('keydown', function (e) {
        var next = null;
        if (e.key === 'ArrowRight') next = thumbs[(i + 1) % thumbs.length];
        if (e.key === 'ArrowLeft') next = thumbs[(i - 1 + thumbs.length) % thumbs.length];
        if (next) { e.preventDefault(); next.focus(); select(next); }
      });
    });
  });

  /* 7. Image upload preview with remove ----------------------------------------- */
  function formatSize(bytes) {
    if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  $$('[data-upload]').forEach(function (box) {
    var input = $('[data-image-input]', box);
    var list = $('[data-preview-list]', box);
    if (!input || !list) return;
    var maxMb = parseFloat(box.getAttribute('data-max-mb')) || 5;
    var canEditList = typeof window.DataTransfer === 'function';
    var files = [];
    var urls = [];

    function sync() {
      if (!canEditList) return;
      try {
        var dt = new DataTransfer();
        files.forEach(function (f) { dt.items.add(f); });
        input.files = dt.files;
      } catch (err) { canEditList = false; }
    }

    function render() {
      urls.forEach(function (u) { URL.revokeObjectURL(u); });
      urls = [];
      list.textContent = '';
      files.forEach(function (file, index) {
        var li = document.createElement('li');
        li.className = 'preview';

        var img = document.createElement('img');
        var url = URL.createObjectURL(file);
        urls.push(url);
        img.src = url;
        img.alt = 'Preview of ' + file.name;
        li.appendChild(img);

        if (index === 0) {
          var chip = document.createElement('span');
          chip.className = 'chip chip--solid';
          chip.textContent = 'Cover';
          li.appendChild(chip);
        }

        if (canEditList) {
          var rm = document.createElement('button');
          rm.type = 'button';
          rm.className = 'preview__remove';
          rm.setAttribute('aria-label', 'Remove ' + file.name);
          rm.innerHTML = '&times;';
          rm.addEventListener('click', function () {
            files.splice(index, 1);
            sync();
            render();
            input.focus();
          });
          li.appendChild(rm);
        }

        var meta = document.createElement('div');
        meta.className = 'preview__meta';
        var name = document.createElement('span');
        name.className = 'preview__name';
        name.textContent = file.name;
        var size = document.createElement('span');
        size.textContent = formatSize(file.size);
        meta.appendChild(name);
        meta.appendChild(size);
        if (file.size > maxMb * 1024 * 1024) {
          var warn = document.createElement('span');
          warn.className = 'preview__warn';
          warn.textContent = 'Larger than ' + maxMb + ' MB. The server may reject it.';
          meta.appendChild(warn);
        }
        li.appendChild(meta);
        list.appendChild(li);
      });
    }

    input.addEventListener('change', function () {
      var incoming = Array.prototype.slice.call(input.files);
      if (canEditList) {
        incoming.forEach(function (f) {
          if (f.type.indexOf('image/') !== 0) return;
          var dup = files.some(function (x) { return x.name === f.name && x.size === f.size && x.lastModified === f.lastModified; });
          if (!dup) files.push(f);
        });
        sync();
      } else {
        files = incoming.filter(function (f) { return f.type.indexOf('image/') === 0; });
      }
      render();
    });
  });

  /* 8. Rent range check (min must not exceed max) ----------------------------------- */
  $$('[data-rent-form]').forEach(function (form) {
    var min = $('[data-min-rent]', form);
    var max = $('[data-max-rent]', form);
    if (!min || !max) return;
    function check() {
      var a = parseFloat(min.value), b = parseFloat(max.value);
      if (!isNaN(a) && !isNaN(b) && a > b) {
        max.setCustomValidity('Maximum rent must be higher than minimum rent.');
      } else {
        max.setCustomValidity('');
      }
    }
    min.addEventListener('input', check);
    max.addEventListener('input', check);
    check();
  });

  /* 9. Character counter -------------------------------------------------------------- */
  $$('textarea[data-count]').forEach(function (ta) {
    var out = document.getElementById(ta.getAttribute('data-count'));
    var limit = parseInt(ta.getAttribute('maxlength'), 10);
    if (!out || !limit) return;
    function update() { out.textContent = String(Math.max(0, limit - ta.value.length)); }
    ta.addEventListener('input', update);
    update();
  });

  /* 10. Mark invalid fields for assistive tech, focus first error ------------------------ */
  var invalid = $$('.field--error input, .field--error select, .field--error textarea');
  invalid.forEach(function (el) { el.setAttribute('aria-invalid', 'true'); });
  if (invalid.length && document.body.classList.contains('page-auth') === false) {
    invalid[0].focus({ preventScroll: false });
  } else if (invalid.length) {
    invalid[0].focus();
  }
  /* 7. Demo notice ------------------------------------------------------------
     Shown once per browser session. Uses sessionStorage only to remember that it
     was dismissed; if storage is blocked, the notice simply shows on each page. */
  var demoNotice = $('#demo-notice');
  var demoOk = $('#demo-notice-ok');
  if (demoNotice && demoOk && typeof demoNotice.showModal === 'function') {
    var seen = false;
    try { seen = sessionStorage.getItem('staynestDemoNoticeSeen') === '1'; } catch (err) { seen = false; }
    if (!seen) {
      demoNotice.showModal();
      demoOk.focus();
    }
    demoNotice.addEventListener('close', function () {
      try { sessionStorage.setItem('staynestDemoNoticeSeen', '1'); } catch (err) { /* ignore */ }
    });
    demoOk.addEventListener('click', function () { demoNotice.close(); });
  }

})();
