/* ─────────────────────────────────────────────────────────────
   lvdi-profile · 站点脚本
   手写 ES5，零依赖。所有交互都是渐进增强：
   禁用 JS 时页面照常可读（tabs 显示首屏、折叠可展开、表格可滚动）。
   ───────────────────────────────────────────────────────────── */
(function () {
  'use strict';
  var doc = document;
  var each = function (list, fn) { Array.prototype.forEach.call(list, fn); };
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── 年份 ── */
  var y = doc.getElementById('year');
  if (y) y.textContent = String(new Date().getFullYear());

  /* ── 移动端导航 ── */
  var t = doc.getElementById('navToggle'), n = doc.getElementById('nav');
  if (t && n) {
    t.addEventListener('click', function () {
      var open = n.classList.toggle('open');
      t.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    n.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        n.classList.remove('open');
        t.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ── 滚动渐显 ── */
  var revealEls = doc.querySelectorAll('.reveal');
  if (reduceMotion || !('IntersectionObserver' in window)) {
    each(revealEls, function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    each(revealEls, function (el) { io.observe(el); });
  }

  /* ── 列表分页：容器 [data-paginate]，子项 [data-page-item]，页码区 [data-pager] ── */
  each(doc.querySelectorAll('[data-paginate]'), function (box) {
    var per = parseInt(box.getAttribute('data-page-size') || '5', 10);
    var items = Array.prototype.slice.call(box.querySelectorAll('[data-page-item]'));
    var pager = doc.querySelector(box.getAttribute('data-pager-target') || '[data-pager]');
    if (items.length <= per) {
      if (pager) pager.hidden = true;
      return;
    }
    if (!pager) return;
    var pages = Math.ceil(items.length / per);
    var cur = 1;

    function go(p) {
      cur = Math.min(Math.max(p, 1), pages);
      items.forEach(function (el, i) {
        el.style.display = (Math.floor(i / per) + 1 === cur) ? '' : 'none';
      });
      pager.innerHTML = '';
      var prev = doc.createElement('button');
      prev.type = 'button'; prev.textContent = '上一页'; prev.disabled = cur === 1;
      prev.addEventListener('click', function () { go(cur - 1); });
      pager.appendChild(prev);
      for (var i = 1; i <= pages; i++) {
        (function (i) {
          var b = doc.createElement('button');
          b.type = 'button'; b.textContent = String(i);
          if (i === cur) b.setAttribute('aria-current', 'page');
          b.addEventListener('click', function () { go(i); });
          pager.appendChild(b);
        })(i);
      }
      var next = doc.createElement('button');
      next.type = 'button'; next.textContent = '下一页'; next.disabled = cur === pages;
      next.addEventListener('click', function () { go(cur + 1); });
      pager.appendChild(next);
      var info = doc.createElement('span');
      info.className = 'pager-info';
      info.textContent = '第 ' + cur + ' / ' + pages + ' 页 · 共 ' + items.length + ' 条';
      pager.appendChild(info);
      pager.hidden = false;
    }
    go(1);
  });

  /* ── 复制工具 ── */
  function copyText(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, done);
    } else {
      var ta = doc.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed'; ta.style.opacity = '0';
      doc.body.appendChild(ta); ta.select();
      try { doc.execCommand('copy'); } catch (e) {}
      doc.body.removeChild(ta); done();
    }
  }

  /* ── 复制邮箱 ── */
  var copyBtn = doc.getElementById('copyMail');
  if (copyBtn) {
    copyBtn.addEventListener('click', function () {
      copyText(copyBtn.getAttribute('data-mail') || '', function () {
        var old = copyBtn.textContent;
        copyBtn.textContent = '已复制 ✓';
        setTimeout(function () { copyBtn.textContent = old; }, 1600);
      });
    });
  }

  /* ── 代码块复制 ── */
  each(doc.querySelectorAll('.code-block'), function (block) {
    var btn = block.querySelector('.code-copy');
    var code = block.querySelector('pre code') || block.querySelector('pre');
    if (!btn || !code) return;
    btn.addEventListener('click', function () {
      copyText(code.textContent, function () {
        btn.textContent = '已复制';
        btn.classList.add('done');
        setTimeout(function () { btn.textContent = '复制'; btn.classList.remove('done'); }, 1600);
      });
    });
  });

  /* ── 标签页 ── */
  each(doc.querySelectorAll('[data-tabs]'), function (root) {
    var bar = root.querySelector('.tabs-bar');
    var panes = root.querySelectorAll('.tab-pane');
    if (!bar || !panes.length) return;
    var btns = bar.querySelectorAll('button');
    function sel(i) {
      each(btns, function (b, j) {
        b.setAttribute('aria-selected', j === i ? 'true' : 'false');
        b.setAttribute('tabindex', j === i ? '0' : '-1');
      });
      each(panes, function (p, j) { p.hidden = j !== i; });
    }
    each(btns, function (b, i) {
      b.addEventListener('click', function () { sel(i); });
      b.addEventListener('keydown', function (e) {
        var k = e.key;
        if (k === 'ArrowRight' || k === 'ArrowLeft') {
          e.preventDefault();
          var next = k === 'ArrowRight' ? (i + 1) % btns.length : (i - 1 + btns.length) % btns.length;
          sel(next); btns[next].focus();
        }
      });
    });
    sel(0);
  });

  /* ── 条形图：进场时按 data-w 填充 ── */
  each(doc.querySelectorAll('.bar-f'), function (bar) {
    var w = bar.getAttribute('data-w') || '0';
    if (reduceMotion || !('IntersectionObserver' in window)) {
      bar.style.width = w + '%';
    } else {
      var o = new IntersectionObserver(function (es) {
        es.forEach(function (en) {
          if (en.isIntersecting) { en.target.style.width = w + '%'; o.unobserve(en.target); }
        });
      }, { threshold: 0.4 });
      o.observe(bar);
    }
  });

  /* ── 可排序表格 ── */
  each(doc.querySelectorAll('.sortable table'), function (table) {
    var body = table.tBodies[0];
    if (!body) return;
    var ths = table.querySelectorAll('thead th');
    function val(row, i) {
      var cell = row.cells[i];
      if (!cell) return '';
      return (cell.getAttribute('data-v') || cell.textContent || '').trim();
    }
    function num(s) {
      var m = s.replace(/[, ]/g, '').match(/-?\d+(\.\d+)?/);
      return m ? parseFloat(m[0]) : null;
    }
    each(ths, function (th, i) {
      th.addEventListener('click', function () {
        var dir = th.getAttribute('data-dir') === 'asc' ? 'desc' : 'asc';
        each(ths, function (o) { o.removeAttribute('data-dir'); });
        th.setAttribute('data-dir', dir);
        var rows = Array.prototype.slice.call(body.rows);
        var allNum = rows.every(function (r) { return num(val(r, i)) !== null; });
        rows.sort(function (a, b) {
          var x = val(a, i), z = val(b, i), c;
          if (allNum) { c = num(x) - num(z); }
          else { c = String(x).localeCompare(String(z), 'zh'); }
          return dir === 'asc' ? c : -c;
        });
        rows.forEach(function (r) { body.appendChild(r); });
      });
    });
  });

  /* ── 目录跟随高亮 ── */
  var tocLinks = doc.querySelectorAll('.toc a[href^="#"]');
  if (tocLinks.length) {
    /* 同一批标题可能被侧栏目录和窄屏折叠目录各引用一次，
       所以按 id 聚合：一次滚动让两份目录同步高亮。 */
    var order = [];
    var byId = {};
    each(tocLinks, function (a) {
      var id = a.getAttribute('href').slice(1);
      var el = doc.getElementById(id);
      if (!el) return;
      if (!byId[id]) {
        byId[id] = { el: el, links: [] };
        order.push(byId[id]);
      }
      byId[id].links.push(a);
    });
    if (order.length) {
      /* 直接同步算：元素只有十几个，比 rAF 节流更省心，
         也不会因为标签页在后台被冻结而失效。 */
      var syncToc = function () {
        var pos = window.scrollY + 120, active = order[0];
        order.forEach(function (h) { if (h.el.offsetTop <= pos) active = h; });
        each(tocLinks, function (a) { a.classList.remove('active'); });
        active.links.forEach(function (a) { a.classList.add('active'); });
      };
      window.addEventListener('scroll', syncToc, { passive: true });
      window.addEventListener('resize', syncToc, { passive: true });
      syncToc();
    }
  }

  /* ── 阅读进度条 ── */
  var prog = doc.querySelector('.progress');
  var proseEl = doc.querySelector('.prose');
  if (prog && proseEl) {
    var syncProgress = function () {
      var rect = proseEl.getBoundingClientRect();
      var total = rect.height - window.innerHeight * 0.6;
      var done = Math.min(Math.max(-rect.top + 100, 0), Math.max(total, 1));
      prog.style.width = (total > 0 ? (done / total) * 100 : 0) + '%';
    };
    window.addEventListener('scroll', syncProgress, { passive: true });
    window.addEventListener('resize', syncProgress, { passive: true });
    syncProgress();
  }

  /* ── 图片放大 ── */
  var imgs = doc.querySelectorAll('.prose img');
  if (imgs.length) {
    var lb = doc.createElement('div');
    lb.className = 'lightbox';
    lb.hidden = true;
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-label', '放大查看');
    var lbImg = doc.createElement('img');
    lbImg.alt = '';
    lb.appendChild(lbImg);
    doc.body.appendChild(lb);
    var close = function () { lb.hidden = true; doc.body.style.overflow = ''; };
    each(imgs, function (img) {
      img.classList.add('zoomable');
      img.addEventListener('click', function () {
        lbImg.src = img.currentSrc || img.src;
        lbImg.alt = img.alt || '';
        lb.hidden = false;
        doc.body.style.overflow = 'hidden';
      });
    });
    lb.addEventListener('click', close);
    doc.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !lb.hidden) close(); });
  }
})();
