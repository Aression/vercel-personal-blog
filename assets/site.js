(function () {
  'use strict';
  var doc = document;

  /* 年份 */
  var y = doc.getElementById('year');
  if (y) y.textContent = String(new Date().getFullYear());

  /* 移动端导航 */
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

  /* 滚动渐显 */
  var revealEls = doc.querySelectorAll('.reveal');
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window)) {
    Array.prototype.forEach.call(revealEls, function (el) { el.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    Array.prototype.forEach.call(revealEls, function (el) { io.observe(el); });
  }

  /* 列表分页：容器 [data-paginate]，子项 [data-page-item]，页码区 [data-pager] */
  Array.prototype.forEach.call(doc.querySelectorAll('[data-paginate]'), function (box) {
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

  /* 复制邮箱 */
  var copyBtn = doc.getElementById('copyMail');
  if (copyBtn) {
    copyBtn.addEventListener('click', function () {
      var mail = copyBtn.getAttribute('data-mail') || '';
      var done = function () {
        var old = copyBtn.textContent;
        copyBtn.textContent = '已复制 ✓';
        setTimeout(function () { copyBtn.textContent = old; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(mail).then(done, done);
      } else {
        var ta = doc.createElement('textarea');
        ta.value = mail; doc.body.appendChild(ta); ta.select();
        try { doc.execCommand('copy'); } catch (e) {}
        doc.body.removeChild(ta); done();
      }
    });
  }
})();
