#!/usr/bin/env python3
"""lvdi-profile 静态站点生成器。

源：content/posts/*.md（文章）+ 本文件内联的简历数据
出：index.html / about.html / projects.html / blog/index.html / blog/<slug>.html
    assets/site.css / assets/site.js

用法：python3 build.py
产物是纯静态 HTML + 同源 CSS/JS，零第三方依赖。
"""

import os
import re
import html
import shutil

try:
    import markdown as mdlib
except ImportError:
    raise SystemExit("需要 markdown 包：python3 -m pip install markdown")

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = {
    "name": "吕迪",
    "name_en": "LYU Di",
    "handle": "@Aression",
    "tagline": "Agentic RL · AI Infra",
    "status": "上海 · 白天写 Agentic RL / AI Infra，晚上折腾小工具",
    "email": "lvdifine@foxmail.com",
    "github": "https://github.com/Aression",
    "researchgate": "https://www.researchgate.net/profile/Di-Lv-6",
    "bilibili": "https://space.bilibili.com/7676105",
    "base": "https://lvdi-profile.vercel.app",
    "desc": "吕迪（LYU Di，@Aression）的个人主页：Agentic RL、AI Infra，以及偶尔写的技术长文。",
}

NAV = [
    ("/", "首页"),
    ("/about.html", "关于"),
    ("/projects.html", "项目"),
    ("/blog/", "文章"),
]

# ────────────────────────────── CSS ──────────────────────────────
CSS = """
:root{
  --bg:#fff;--bg-soft:#f9f9f9;--card:#fff;--card-hi:#f9f9f9;
  --border:#e6e6e6;--border-hi:#d0d0d0;
  --fg:#111;--fg-soft:#3d3d3d;--muted:#5d5d5d;--dim:#8f8f8f;--ink:#0d0d0d;
  --sans:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC','PingFang SC','Microsoft YaHei',system-ui,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,'Courier New',monospace;
  --wrap:1120px;--r:12px;--r-sm:8px;
}
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:88px}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--sans);
  font-size:16px;line-height:1.72;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--fg);text-decoration:none}
a:hover{text-decoration:underline;text-underline-offset:3px;text-decoration-color:var(--border-hi)}
::selection{background:#eaeaea;color:var(--fg)}
:focus-visible{outline:2px solid var(--ink);outline-offset:3px;border-radius:4px}

.wrap{max-width:var(--wrap);margin:0 auto;padding:0 32px}
@media (max-width:640px){ .wrap{padding:0 20px} }

/* ── nav ── */
header.nav{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.86);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
.nav-in{display:flex;align-items:center;justify-content:space-between;height:62px;gap:20px}
.brand{font-size:15.5px;font-weight:600;color:var(--fg);letter-spacing:-.01em}
.nav-in ul{display:flex;gap:2px;list-style:none;margin:0;padding:0}
.nav-in ul a{display:block;padding:7px 12px;border-radius:var(--r-sm);font-size:14.5px;color:var(--muted);
  transition:color .18s,background .18s}
.nav-in ul a:hover{color:var(--fg);background:var(--bg-soft);text-decoration:none}
.nav-in ul a.active{color:var(--fg);background:var(--bg-soft);font-weight:500}
.nav-toggle{display:none;background:none;border:1px solid var(--border-hi);border-radius:var(--r-sm);
  color:var(--fg);font-family:var(--sans);font-size:14px;padding:7px 13px;cursor:pointer}
.nav-toggle:hover{background:var(--bg-soft)}
@media (max-width:760px){
  .nav-toggle{display:block}
  #nav{position:absolute;top:62px;left:0;right:0;background:#fff;
    border-bottom:1px solid var(--border);display:none}
  #nav.open{display:block}
  #nav ul{flex-direction:column;gap:0;padding:10px}
  #nav ul a{padding:11px 12px}
}

/* ── layout ── */
main{padding:0}
section{padding:60px 0;border-bottom:1px solid var(--border)}
section:last-of-type{border-bottom:none}
@media (max-width:640px){ section{padding:44px 0} }
.sec-head{margin:0 0 26px}
.sec-title{font-size:clamp(22px,2.2vw,28px);line-height:1.2;letter-spacing:-.02em;font-weight:600;color:var(--fg);margin:0}
.sec-note{font-size:14.5px;color:var(--muted);margin:8px 0 0}
.sec-more{margin:26px 0 0;font-size:14.5px}
.sec-more a{color:var(--muted)}
.sec-more a:hover{color:var(--fg)}

/* ── page head（子页标题） ── */
.page-head{padding:56px 0 34px;border-bottom:1px solid var(--border)}
.page-head h1{font-size:clamp(30px,4vw,44px);line-height:1.12;letter-spacing:-.03em;margin:0 0 12px;font-weight:600}
.page-head p{margin:0;color:var(--muted);font-size:16px;max-width:62ch}
@media (max-width:640px){ .page-head{padding:40px 0 26px} }

/* ── hero ── */
.hero{padding:80px 0 56px}
.hero h1{font-size:clamp(40px,5.4vw,64px);line-height:1.05;margin:0 0 12px;font-weight:600;letter-spacing:-.035em}
.id-line{font-size:15px;color:var(--muted);margin:0 0 18px}
.tagline{font-size:clamp(17px,1.6vw,20px);color:var(--fg-soft);margin:0 0 14px;line-height:1.5}
.status{display:inline-flex;align-items:center;gap:9px;font-size:14px;color:var(--muted);
  background:var(--bg-soft);border:1px solid var(--border);border-radius:999px;padding:6px 15px;margin:0 0 26px}
.dot{width:6px;height:6px;border-radius:50%;background:var(--ink);flex:none}
.links{display:flex;flex-wrap:wrap;gap:10px;list-style:none;margin:0;padding:0}
.links a{display:inline-block;font-size:14px;color:var(--fg);border:1px solid var(--border-hi);
  border-radius:999px;padding:8px 17px;transition:background .18s,color .18s,border-color .18s}
.links a:hover{background:var(--ink);color:#fff;border-color:var(--ink);text-decoration:none}
@media (max-width:640px){ .hero{padding:52px 0 40px} }

/* ── 文本块 ── */
.prose-sm{max-width:none}
.prose-sm p{margin:0 0 16px;color:var(--fg-soft);font-size:16px}
.prose-sm p:last-child{margin-bottom:0}
.prose-sm strong{color:var(--fg);font-weight:600}
.two-col{display:grid;grid-template-columns:1.5fr 1fr;gap:44px;align-items:start}
@media (max-width:900px){ .two-col{grid-template-columns:1fr;gap:32px} }

/* ── 教育 / 侧栏列表 ── */
.side-list{border-left:2px solid var(--border-hi);padding-left:22px}
.side-item{margin:0 0 20px}
.side-item:last-child{margin-bottom:0}
.side-t{font-weight:600;color:var(--fg);font-size:15px}
.side-s{font-size:13.5px;color:var(--muted);margin-top:2px}
.side-d{font-size:14px;color:var(--fg-soft);margin-top:6px}
.side-d em{color:var(--fg);font-style:normal;font-weight:500}

/* ── 卡片网格 ── */
.card-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
@media (max-width:900px){ .card-grid{grid-template-columns:1fr} }
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:22px;
  display:flex;flex-direction:column;gap:10px;transition:border-color .2s,background .2s}
.card:hover{border-color:var(--border-hi);background:var(--card-hi)}
.card h3{font-size:16.5px;line-height:1.45;margin:0;font-weight:600;letter-spacing:-.01em}
.card h3 a{color:var(--fg)}
.card h3 a:hover{text-decoration:underline;text-underline-offset:3px}
.card ul{margin:0;padding-left:0;list-style:none}
.card ul li{position:relative;padding-left:16px;font-size:14.8px;color:var(--fg-soft);margin-bottom:6px;line-height:1.7}
.card ul li:last-child{margin-bottom:0}
.card ul li::before{content:'';position:absolute;left:0;top:.68em;width:4px;height:4px;border-radius:50%;background:var(--dim)}
.card-top{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.card-role{font-size:12.5px;color:var(--muted);background:#f2f2f2;border-radius:6px;padding:3px 10px;white-space:nowrap}
.stack{display:flex;flex-wrap:wrap;gap:6px;margin-top:auto;padding-top:6px}
.stack span{font-size:12px;color:var(--muted);background:var(--bg-soft);border:1px solid var(--border);
  border-radius:6px;padding:2px 8px}

/* ── 论文紧凑列表 ── */
.pub-list{list-style:none;margin:0;padding:0;border-top:1px solid var(--border)}
.pub-item{padding:18px 0;border-bottom:1px solid var(--border)}
.pub-meta-line{display:flex;flex-wrap:wrap;align-items:center;gap:10px;font-size:13px;color:var(--muted);margin:0 0 6px}
.pub-meta-line .venue{color:var(--fg);font-weight:500}
.pub-meta-line .role{color:var(--dim)}
.pub-t{font-size:15.5px;line-height:1.5;color:var(--fg);margin:0;font-weight:500}
.pub-t a{color:var(--fg)}
.pub-t a:hover{text-decoration:underline;text-underline-offset:3px}
.pub-authors{font-size:13.5px;color:var(--dim);margin:6px 0 0}

/* ── 荣誉 ── */
.honor-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--border);
  border:1px solid var(--border);border-radius:var(--r);overflow:hidden}
.honor{background:#fff;padding:18px 20px;display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.honor-t{font-size:15px;color:var(--fg);font-weight:500}
.honor-t small{display:block;font-size:12.5px;color:var(--dim);font-weight:400;margin-top:2px}
.honor-y{font-size:13.5px;color:var(--muted);white-space:nowrap}
@media (max-width:760px){ .honor-grid{grid-template-columns:1fr} }

/* ── 技能 ── */
.skill-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:26px 44px}
.skill-h{font-size:14px;color:var(--muted);font-weight:500;margin:0 0 10px;letter-spacing:.01em}
.skill-list{display:flex;flex-wrap:wrap;gap:7px}
.skill-list span{font-size:13.5px;color:var(--fg-soft);background:var(--bg-soft);border:1px solid var(--border);
  border-radius:6px;padding:4px 11px}
@media (max-width:760px){ .skill-grid{grid-template-columns:1fr} }

/* ── 文章列表 ── */
.post-list{list-style:none;margin:0;padding:0;border-top:1px solid var(--border)}
.post-item{padding:22px 0;border-bottom:1px solid var(--border);display:grid;grid-template-columns:112px 1fr;gap:22px}
.post-date{font-size:13.5px;color:var(--dim);font-variant-numeric:tabular-nums;padding-top:3px}
.post-h{font-size:19px;line-height:1.42;margin:0 0 8px;font-weight:600;letter-spacing:-.015em}
.post-h a{color:var(--fg)}
.post-h a:hover{text-decoration:underline;text-underline-offset:3px}
.post-sum{margin:0 0 10px;font-size:14.8px;color:var(--muted);line-height:1.7}
.post-tags{display:flex;flex-wrap:wrap;gap:8px;font-size:12.5px;color:var(--dim)}
.post-tags span{background:var(--bg-soft);border:1px solid var(--border);border-radius:6px;padding:2px 9px}
@media (max-width:640px){ .post-item{grid-template-columns:1fr;gap:6px} .post-date{padding-top:0} }

/* ── 分页器 ── */
.pager{display:flex;align-items:center;gap:6px;margin:34px 0 0;flex-wrap:wrap}
.pager[hidden]{display:none}
.pager button{font-family:var(--sans);font-size:14px;color:var(--muted);background:#fff;
  border:1px solid var(--border);border-radius:var(--r-sm);padding:7px 13px;cursor:pointer;
  transition:background .18s,color .18s,border-color .18s}
.pager button:hover:not(:disabled){background:var(--bg-soft);color:var(--fg);border-color:var(--border-hi)}
.pager button[aria-current="page"]{background:var(--ink);color:#fff;border-color:var(--ink)}
.pager button:disabled{opacity:.42;cursor:default}
.pager .pager-info{margin-left:auto;font-size:13.5px;color:var(--dim)}

/* ── 文章页 ── */
.article-wrap{max-width:760px;margin:0 auto;padding:0 32px}
@media (max-width:640px){ .article-wrap{padding:0 20px} }
.article{padding:56px 0 64px}
.art-meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 16px;font-size:12.5px;color:var(--muted)}
.art-meta span{background:#f2f2f2;border-radius:6px;padding:3px 10px}
.art-meta .sep{background:none;padding:0;color:var(--dim)}
.article h1{font-size:clamp(28px,3.8vw,40px);line-height:1.2;letter-spacing:-.025em;margin:0 0 16px;font-weight:600}
.art-sum{margin:0;color:var(--muted);font-size:15.5px;line-height:1.72}
.art-rule{border:none;border-top:1px solid var(--border);margin:28px 0 30px}
.prose{font-size:16.5px;line-height:1.86;color:var(--fg-soft)}
.prose h2{font-size:clamp(21px,2.2vw,25px);line-height:1.32;letter-spacing:-.015em;color:var(--fg);
  margin:50px 0 14px;font-weight:600}
.prose h2:first-child{margin-top:0}
.prose h3{font-size:18px;line-height:1.4;color:var(--fg);margin:32px 0 10px;font-weight:600}
.prose p{margin:0 0 17px}
.prose strong{color:var(--fg);font-weight:600}
.prose em{font-style:italic;color:var(--fg)}
.prose a{color:var(--fg);text-decoration:underline;text-underline-offset:3px;text-decoration-color:var(--border-hi)}
.prose a:hover{text-decoration-color:var(--fg)}
.prose ul,.prose ol{margin:0 0 17px;padding-left:22px}
.prose li{margin:0 0 8px}
.prose li::marker{color:var(--dim)}
.prose blockquote{margin:0 0 22px;padding:14px 19px;background:var(--bg-soft);border-left:2px solid var(--border-hi);
  border-radius:0 var(--r-sm) var(--r-sm) 0;color:var(--muted);font-size:15.5px}
.prose blockquote p{margin:0}
.prose code{font-family:var(--mono);font-size:13.8px;background:#f4f4f4;border:1px solid var(--border);
  border-radius:5px;padding:1px 5px;color:#1f1f1f;overflow-wrap:anywhere}
.prose pre{background:#fafafa;border:1px solid var(--border);border-radius:var(--r-sm);
  padding:15px 17px;overflow-x:auto;margin:0 0 22px}
.prose pre code{background:none;border:none;border-radius:0;padding:0;font-size:13.2px;
  line-height:1.62;color:#242424;white-space:pre;overflow-wrap:normal}
.prose table{display:block;width:100%;overflow-x:auto;border-collapse:collapse;margin:0 0 24px;font-size:14.8px}
.prose th,.prose td{border:1px solid var(--border);padding:9px 13px;text-align:left;vertical-align:top}
.prose th{background:var(--bg-soft);color:var(--fg);font-weight:600;white-space:nowrap}
.prose td code{font-size:12.8px}
.prose hr{border:none;border-top:1px solid var(--border);margin:34px 0}
.art-foot{margin-top:52px;padding-top:20px;border-top:1px solid var(--border);
  display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;font-size:14px}
.art-foot a{color:var(--muted)}
.art-foot a:hover{color:var(--fg)}

/* ── footer（联系方式在此） ── */
footer{border-top:1px solid var(--border);padding:30px 0;margin-top:0}
.foot-in{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap}
.foot-contact{display:flex;flex-wrap:wrap;align-items:center;gap:10px;font-size:14px}
.foot-contact a{color:var(--muted)}
.foot-contact a:hover{color:var(--fg)}
.foot-contact .sep{color:var(--border-hi)}
.foot-meta{margin:0;font-size:13.5px;color:var(--dim)}
@media (max-width:640px){ .foot-in{flex-direction:column;align-items:flex-start;gap:12px} }

/* ── reveal ── */
.reveal{opacity:0;transform:translateY(10px);transition:opacity .45s ease,transform .45s ease}
.reveal.in{opacity:1;transform:none}
@media (prefers-reduced-motion:reduce){
  html{scroll-behavior:auto}
  .reveal{opacity:1;transform:none;transition:none}
  *{transition:none!important}
}
/* ── 无障碍跳转 ── */
.skip{position:absolute;left:-9999px;top:0;z-index:100;font-size:14px;color:#fff;background:var(--ink);
  padding:9px 16px;border-radius:0 0 var(--r-sm) 0}
.skip:focus{left:0}
@media print{
  header.nav,.skip,.pager{display:none!important}
  body{font-size:11.5pt}
  .wrap,.article-wrap{max-width:100%;padding:0}
  a{color:#000}
}
"""

# ────────────────────────────── JS ──────────────────────────────
JS = """
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
"""

# ────────────────────────────── 模板 ──────────────────────────────
FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%23111111'/%3E%3Ctext x='16' y='23' "
    "font-family='-apple-system,Segoe UI,sans-serif' font-size='18' font-weight='600' "
    "fill='%23ffffff' text-anchor='middle'%3Edi%3C/text%3E%3C/svg%3E"
)


def esc(s):
    return html.escape(s, quote=True)


def nav_html(active):
    items = []
    for href, label in NAV:
        cls = ' class="active"' if href == active else ""
        cur = ' aria-current="page"' if href == active else ""
        items.append(f'        <li><a href="{href}"{cls}{cur}>{label}</a></li>')
    return f"""<header class="nav">
  <div class="wrap nav-in">
    <a class="brand" href="/">{SITE['name']}</a>
    <button class="nav-toggle" id="navToggle" aria-label="展开导航" aria-expanded="false">菜单</button>
    <nav id="nav" aria-label="页面导航">
      <ul>
{chr(10).join(items)}
      </ul>
    </nav>
  </div>
</header>"""


def footer_html():
    return f"""<footer>
  <div class="wrap foot-in">
    <div class="foot-contact">
      <a href="mailto:{SITE['email']}">{SITE['email']}</a>
      <span class="sep">·</span>
      <a href="{SITE['github']}" target="_blank" rel="noopener">GitHub</a>
      <span class="sep">·</span>
      <a href="{SITE['researchgate']}" target="_blank" rel="noopener">ResearchGate</a>
      <span class="sep">·</span>
      <a href="{SITE['bilibili']}" target="_blank" rel="noopener">Bilibili</a>
    </div>
    <p class="foot-meta">© <span id="year">2026</span> {SITE['name']} · {SITE['name_en']} · 手写 HTML/CSS/JS</p>
  </div>
</footer>"""


def page(title, desc, path, body, active, og_type="website"):
    canonical = SITE["base"] + path
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#ffffff">
<title>{title}</title>
<meta name="description" content="{esc(desc)}">
<meta name="author" content="Di Lv (吕迪)">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="{FAVICON}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
<a class="skip" href="#main">跳到主要内容</a>

{nav_html(active)}

<main id="main">
{body}
</main>

{footer_html()}
<script src="/assets/site.js" defer></script>
</body>
</html>
"""


# ────────────────────────────── 数据 ──────────────────────────────
PROJECTS = [
    {
        "title": "宫颈细胞病理学半监督目标检测系统",
        "role": "CV 算法 · 2025.12–2026.04",
        "points": [
            "针对临床 TCT 涂片背景复杂、极端长尾与稀疏标注的确认偏差问题，设计区域级半监督框架 <strong>MPG-RSCD</strong>",
            "基线 YOLO-TCT：自适应硬极化自注意力 + 类别平衡质量焦点损失，全局召回提升至 <strong>46.27%</strong>",
            "医学先验引导伪标签提纯：动态门控融合 BiomedCLIP 全局语义与 ResNet50 局部纹理",
            "1338 张真实临床涂片：高风险病变召回 <strong>58.39% → 64.98%</strong>，低误报敏感性 <strong>42.70% → 55.83%</strong>",
        ],
        "stack": ["Python", "PyTorch", "Ultralytics YOLO", "BiomedCLIP", "OpenCV"],
    },
    {
        "title": "RPC 框架：从零实现到性能优化",
        "role": "后端开发 · 2024",
        "points": [
            "从零实现分布式 RPC：Netty Reactor 通信层 + 自定义私有协议解决 TCP 粘包/拆包，延迟反序列化剥离 IO 线程阻塞",
            "Zookeeper 注册发现 + 本地缓存 &amp; Watcher；基于请求参数特征的一致性哈希负载均衡",
            "节点级状态机熔断（半开探测 / 自动愈合）+ 纳秒级时间窗口令牌桶限流",
            "JFR/JMC 全链路剖析：单机回环吞吐 <strong>1 万 → 9.4 万 QPS</strong>，P99 <strong>83ms</strong>，99.9% 可用性",
        ],
        "stack": ["Java", "Netty", "Zookeeper", "Kryo/Protobuf", "SPI", "JFR/JMC"],
    },
    {
        "title": "ref-corrector",
        "role": "开源",
        "points": [
            "基于 <strong>LangGraph</strong> 的 BibTeX 参考文献校验与修正 CLI，解析条目、校验字段格式、识别重复项",
            "多源元数据交叉校验（OpenAlex / Crossref / Semantic Scholar）+ DeepSeek LLM 生成修正建议",
            "输出规范化 <strong>corrected.bib</strong> 与结构化修正报告",
        ],
        "stack": ["Python", "LangGraph", "DeepSeek", "OpenAlex", "Crossref"],
    },
    {
        "title": "GameWorkplace",
        "role": "开源 · 游戏工具",
        "points": [
            "自动从 War Thunder 录像中识别并导出连杀片段，支持连杀时间阈值与最少击杀数配置",
            "自动选择最佳视频源（单视频优先 / 必要时多视频拼接），GPU / CPU 编码自适应切换",
        ],
        "stack": ["Python", "PyQt5", "FFmpeg"],
    },
    {
        "title": "ae2-bus-scanner",
        "role": "开源",
        "points": [
            "扫描 Minecraft 存档中的 AE2 输入/输出总线与接口，定位包含指定过滤物品的设备",
            "可复用扫描引擎 + CLI + tkinter 桌面 GUI，支持多进程并行扫描",
        ],
        "stack": ["Python", "tkinter", "多进程"],
    },
    {
        "title": "CampusAutoLogin",
        "role": "开源",
        "points": [
            "dr.com 校园网自动登录后台服务：网络状态监控、断线自动认证",
            "静默后台运行 + 系统通知，配置界面化",
        ],
        "stack": ["Python", "自动化"],
    },
    {
        "title": "TapTap 数据分析",
        "role": "课程项目",
        "points": ["TapTap 平台数据采集与分析实训项目"],
        "stack": ["Python", "数据分析"],
    },
]

PUBS = [
    {
        "venue": "Pattern Recognition",
        "year": "2024",
        "role": "共同第一作者",
        "title": "Self-Training-Transductive-Learning Broad Learning System (STTL-BLS): A model for effective and efficient image classification",
        "url": "https://doi.org/10.1016/j.patcog.2024.110747",
        "authors": "Lin Yi; Di Lv; Dinghao Liu; Suhuan Li; Ran Liu",
    },
    {
        "venue": "ICASSP 2025",
        "year": "2025",
        "role": "第一作者",
        "title": "YOLO-TCT: An Effective Network For Long-Tailed Cervical Cell Detection",
        "url": "https://doi.org/10.1109/ICASSP49660.2025.10888567",
        "authors": "Di Lv; Lin Yi; Li Liu; Yuze Chen; Xin Chen; Ran Liu",
    },
    {
        "venue": "Electronics",
        "year": "2024",
        "role": "参与作者",
        "title": "Unstructured Document Information Extraction Method with Multi-Faceted Domain Knowledge Graph Assistance for M2M Customs Risk Prevention and Screening",
        "url": "https://doi.org/10.3390/electronics13101941",
        "authors": "Fengchun Tian; Haochen Wang; Zhenlong Wan; Ran Liu; Ruilong Liu; Di Lv; Yingcheng Lin",
    },
    {
        "venue": "IJCNN 2024",
        "year": "2024",
        "role": "参与作者",
        "title": "TSO-DETR: A Network for Small Object Detection of Cervical Cells in TCT Smear",
        "url": "https://doi.org/10.1109/IJCNN60899.2024.10650706",
        "authors": "Xin Chen; Lin Yi; Li Liu; Di Lv; Ziheng Liu; Ran Liu",
    },
]

PATENTS = [
    {"venue": "发明专利", "year": "已授权", "role": "CN116740455A",
     "title": "图像分类宽度学习系统及其训练方法和图像分类方法", "url": "", "authors": ""},
    {"venue": "发明专利", "year": "已受理", "role": "CN119007194A",
     "title": "多层次硬极化特征融合的 TCT 涂片自动检测系统", "url": "", "authors": ""},
]

HONORS = [
    ("研究生国家奖学金", "国家级", "2025"),
    ("重庆大学硕士学业奖学金 一等奖", "校级", "2024–2025"),
    ("美国大学生数学建模竞赛 M 奖", "国际一等奖", "2021"),
    ("研究生电子设计竞赛 省级二等奖", "省级", "2024"),
]

SKILLS = [
    ("编程语言", ["Python", "Java"]),
    ("AI / 大模型", ["Agentic RL", "LLM Agent", "强化学习", "RAG 检索增强", "LoRA 参数高效微调", "vLLM 推理部署", "CLIP 多模态适配"]),
    ("计算机视觉", ["PyTorch", "Ultralytics YOLO", "目标检测", "半监督学习", "注意力机制与损失函数设计"]),
    ("后端 / 分布式", ["Netty", "Spring Boot", "Zookeeper", "分布式 RPC", "一致性哈希", "令牌桶限流", "熔断状态机", "MySQL", "Redis"]),
    ("工程工具", ["Git", "Linux", "JFR/JMC 性能剖析", "pytest"]),
    ("语言能力", ["CET-6 533", "CET-4 502"]),
]

EDU = [
    ("重庆大学（985）", "计算机技术 · 硕士 | 2023.09 – 2026.06", "GPA <em>3.59/4.0</em>；方向计算机视觉，毕业论文做半监督目标检测。"),
    ("重庆大学（985）", "计算机科学与技术 · 本科 | 2019.09 – 2021.06".replace("2021", "2023"), "GPA <em>3.46/4.0</em>；主修计算机组成原理、数据结构、计算机网络、操作系统。"),
    ("生物感知与智能信息处理", "重庆市重点实验室 · 成员", ""),
]


def edu_items(limit=None):
    rows = EDU[:limit] if limit else EDU
    out = []
    for t, s, d in rows:
        d_html = '<div class="side-d">' + d + "</div>" if d else ""
        out.append(
            '<div class="side-item"><div class="side-t">' + t + "</div>"
            '<div class="side-s">' + s + "</div>" + d_html + "</div>"
        )
    return "".join(out)


# ────────────────────────────── 文章 ──────────────────────────────
def load_posts():
    posts = []
    d = os.path.join(ROOT, "content", "posts")
    if not os.path.isdir(d):
        return posts
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md"):
            continue
        raw = open(os.path.join(d, fn), encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        if not m:
            continue
        fm, body = m.group(1), m.group(2)
        meta = {}
        for line in fm.split("\n"):
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
        slug = fn[:-3]
        tags = [t.strip().strip('"') for t in meta.get("tags", "[]").strip("[]").split(",") if t.strip()]
        mdc = mdlib.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
        body_html = mdc.convert(body)
        words = len(re.findall(r"[\u4e00-\u9fff]", body)) + len(re.findall(r"[A-Za-z]+", body))
        posts.append({
            "slug": slug,
            "title": meta.get("title", slug).strip('"'),
            "date": meta.get("date", "").strip('"'),
            "summary": meta.get("summary", "").strip('"'),
            "tags": tags,
            "minutes": max(1, round(len(body) / 900)),
            "html": body_html,
            "words": words,
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def post_card(post):
    tags = "".join(f"<span>{esc(t)}</span>" for t in post["tags"][:3])
    return f"""      <li class="post-item reveal" data-page-item>
        <div class="post-date">{esc(post['date'])}</div>
        <div>
          <h3 class="post-h"><a href="/blog/{post['slug']}.html">{esc(post['title'])}</a></h3>
          <p class="post-sum">{esc(post['summary'])}</p>
          <div class="post-tags">{tags}<span>约 {post['minutes']} 分钟</span></div>
        </div>
      </li>"""


# ────────────────────────────── 页面 ──────────────────────────────
def build_home(posts):
    proj_cards = []
    for p in PROJECTS[:3]:
        pts = "".join(f"<li>{x}</li>" for x in p["points"][:2])
        stack = "".join(f"<span>{esc(s)}</span>" for s in p["stack"][:4])
        proj_cards.append(f"""        <article class="card reveal">
          <div class="card-top"><span class="card-role">{esc(p['role'])}</span></div>
          <h3>{esc(p['title'])}</h3>
          <ul>{pts}</ul>
          <div class="stack">{stack}</div>
        </article>""")

    latest = posts[:2]
    if latest:
        post_block = f"""      <ul class="post-list">
{chr(10).join(post_card(p) for p in latest)}
      </ul>
      <p class="sec-more"><a href="/blog/">全部文章 →</a></p>"""
    else:
        post_block = '      <p class="sec-note">还没写，先空着。</p>'

    body = f"""  <section class="hero">
    <div class="wrap">
      <h1>{SITE['name']}</h1>
      <p class="id-line">{SITE['name_en']} · {SITE['handle']}</p>
      <p class="tagline">{SITE['tagline']}</p>
      <p class="status"><span class="dot" aria-hidden="true"></span> {SITE['status']}</p>
      <ul class="links">
        <li><a href="{SITE['github']}" target="_blank" rel="noopener">GitHub ↗</a></li>
        <li><a href="/blog/">文章</a></li>
        <li><a href="mailto:{SITE['email']}">Email</a></li>
      </ul>
    </div>
  </section>

  <section id="now">
    <div class="wrap">
      <div class="two-col">
        <div class="prose-sm reveal">
          <p>在上海，白天写 <strong>Agentic RL</strong> 和 <strong>AI Infra</strong>——大模型智能体的强化学习训练、推理与基础设施那一摊；晚上大概率在折腾什么小工具。</p>
          <p>重庆大学计算机技术硕士毕业，之前做计算机视觉（长尾识别、半监督检测、医学影像），现在在往 Agent 和系统方向转。发过几篇论文，也有两项发明专利，具体都在<a href="/about.html">关于</a>里。</p>
          <p>工程上是个自动化强迫症：能脚本化的绝不手动，爱折腾本地工具链和性能调优；偶尔为了搞懂原理，会把底层的东西自己实现一遍。</p>
        </div>
        <div class="side-list reveal">
          {edu_items(2)}
        </div>
      </div>
    </div>
  </section>

  <section id="projects-preview">
    <div class="wrap">
      <div class="sec-head reveal">
        <h2 class="sec-title">在折腾的东西</h2>
        <p class="sec-note">挑三个最近的，全部在<a href="/projects.html">项目</a></p>
      </div>
      <div class="card-grid">
{chr(10).join(proj_cards)}
      </div>
      <p class="sec-more"><a href="/projects.html">全部项目 →</a></p>
    </div>
  </section>

  <section id="writing">
    <div class="wrap">
      <div class="sec-head reveal">
        <h2 class="sec-title">最近写的</h2>
        <p class="sec-note">技术长文，不追热点，追把原理讲清楚</p>
      </div>
{post_block}
    </div>
  </section>
"""
    return page(f"{SITE['name']} · {SITE['name_en']} — {SITE['tagline']}", SITE["desc"], "/", body, "/")


def build_about(posts):
    pub_items = []
    for p in PUBS:
        title = (f'<a href="{p["url"]}" target="_blank" rel="noopener">{esc(p["title"])}</a>'
                 if p["url"] else esc(p["title"]))
        authors = f'<p class="pub-authors">{esc(p["authors"])}</p>' if p["authors"] else ""
        pub_items.append(f"""        <li class="pub-item">
          <div class="pub-meta-line">
            <span class="venue">{esc(p['venue'])}</span>
            <span>{esc(p['year'])}</span>
            <span class="role">{esc(p['role'])}</span>
          </div>
          <p class="pub-t">{title}</p>
          {authors}
        </li>""")
    for p in PATENTS:
        pub_items.append(f"""        <li class="pub-item">
          <div class="pub-meta-line">
            <span class="venue">{esc(p['venue'])}</span>
            <span>{esc(p['year'])}</span>
            <span class="role">{esc(p['role'])}</span>
          </div>
          <p class="pub-t">{esc(p['title'])}</p>
        </li>""")

    edu = "".join(
        f'<div class="side-item"><div class="side-t">{t}</div><div class="side-s">{s}</div>'
        + (f'<div class="side-d">{d}</div>' if d else "") + "</div>"
        for t, s, d in EDU
    )
    honors = "".join(
        f'<div class="honor"><div class="honor-t">{esc(t)}<small>{esc(sub)}</small></div>'
        f'<div class="honor-y">{esc(y)}</div></div>'
        for t, sub, y in HONORS
    )
    skills = "".join(
        f'<div><h3 class="skill-h">{esc(h)}</h3><div class="skill-list">'
        + "".join(f"<span>{esc(s)}</span>" for s in items) + "</div></div>"
        for h, items in SKILLS
    )

    body = f"""  <div class="page-head">
    <div class="wrap">
      <h1>关于</h1>
      <p>一个在上海写代码的人。</p>
    </div>
  </div>

  <section id="intro">
    <div class="wrap">
      <div class="two-col">
        <div class="prose-sm reveal">
          <p>在上海，白天写 <strong>Agentic RL</strong> 和 <strong>AI Infra</strong>——大模型智能体的强化学习训练、推理与基础设施那一摊；晚上大概率在折腾什么小工具。</p>
          <p>重庆大学计算机技术硕士（2026 届），本科也在重大。研究生阶段做计算机视觉：长尾识别、半监督目标检测、医学影像，一作发过 ICASSP、共一发过 Pattern Recognition，两项发明专利。现在把重心挪到 Agent 与系统方向。</p>
          <p>工程上是个自动化强迫症：能脚本化的绝不手动，爱折腾本地工具链和性能调优。偶尔为了搞懂原理，会把底层的东西自己实现一遍——RPC 框架、推理后端、甚至这个站点的排版。</p>
        </div>
        <div class="side-list reveal">
          {edu}
        </div>
      </div>
    </div>
  </section>

  <section id="publications">
    <div class="wrap">
      <div class="sec-head reveal">
        <h2 class="sec-title">论文与专利</h2>
        <p class="sec-note">一作 / 共一各一篇，另有两项发明专利</p>
      </div>
      <ul class="pub-list">
{chr(10).join(pub_items)}
      </ul>
    </div>
  </section>

  <section id="skills">
    <div class="wrap">
      <div class="sec-head reveal">
        <h2 class="sec-title">会点啥</h2>
        <p class="sec-note">技能栈</p>
      </div>
      <div class="skill-grid reveal">
        {skills}
      </div>
    </div>
  </section>

  <section id="honors">
    <div class="wrap">
      <div class="sec-head reveal">
        <h2 class="sec-title">顺手拿的几个奖</h2>
        <p class="sec-note">荣誉</p>
      </div>
      <div class="honor-grid reveal">
        {honors}
      </div>
    </div>
  </section>
"""
    return page(f"关于 — {SITE['name']}", "吕迪（LYU Di）的简介、教育经历、论文与专利、技能栈与荣誉。",
                "/about.html", body, "/about.html")


def build_projects(posts):
    cards = []
    for p in PROJECTS:
        pts = "".join(f"<li>{x}</li>" for x in p["points"])
        stack = "".join(f"<span>{esc(s)}</span>" for s in p["stack"])
        cards.append(f"""        <article class="card reveal" data-page-item>
          <div class="card-top"><span class="card-role">{esc(p['role'])}</span></div>
          <h3>{esc(p['title'])}</h3>
          <ul>{pts}</ul>
          <div class="stack">{stack}</div>
        </article>""")
    body = f"""  <div class="page-head">
    <div class="wrap">
      <h1>项目</h1>
      <p>项目、开源和小工具。{len(PROJECTS)} 个里有几个还在维护，剩下的多少都还能跑。</p>
    </div>
  </div>

  <section id="projects">
    <div class="wrap">
      <div class="card-grid" data-paginate data-page-size="6" data-pager-target="#pager-projects">
{chr(10).join(cards)}
      </div>
      <nav class="pager" id="pager-projects" data-pager aria-label="项目分页" hidden></nav>
    </div>
  </section>
"""
    return page(f"项目 — {SITE['name']}", "吕迪的项目与开源工具：半监督检测系统、RPC 框架、ref-corrector、游戏工具等。",
                "/projects.html", body, "/projects.html")


def build_blog_index(posts):
    if posts:
        cards = "\n".join(post_card(p) for p in posts)
        count_note = f"目前 {len(posts)} 篇"
        listing = f"""      <ul class="post-list" data-paginate data-page-size="5" data-pager-target="#pager-posts">
{cards}
      </ul>
      <nav class="pager" id="pager-posts" data-pager aria-label="文章分页" hidden></nav>"""
    else:
        count_note = "还没写"
        listing = '      <p class="sec-note">还没写，先空着。</p>'
    body = f"""  <div class="page-head">
    <div class="wrap">
      <h1>文章</h1>
      <p>技术长文与笔记 · {count_note}。不追热点，追把原理讲清楚。</p>
    </div>
  </div>

  <section id="posts">
    <div class="wrap">
{listing}
    </div>
  </section>
"""
    return page(f"文章 — {SITE['name']}", "吕迪的技术长文与笔记：复杂性理论、Agentic RL、AI Infra、系统与工具链。",
                "/blog/", body, "/blog/")


def build_post(post, posts):
    idx = [p["slug"] for p in posts].index(post["slug"])
    newer = posts[idx - 1] if idx > 0 else None
    older = posts[idx + 1] if idx < len(posts) - 1 else None
    nav_links = []
    if newer:
        nav_links.append(f'<a href="/blog/{newer["slug"]}.html">← {esc(newer["title"][:28])}…</a>')
    else:
        nav_links.append('<a href="/blog/">← 全部文章</a>')
    if older:
        nav_links.append(f'<a href="/blog/{older["slug"]}.html">{esc(older["title"][:28])}… →</a>')
    tags = "".join(f"<span>{esc(t)}</span>" for t in post["tags"])
    body = f"""  <article class="article">
    <div class="article-wrap">
      <div class="art-meta">
        <span>{esc(post['date'])}</span>
        <span class="sep">·</span>
        <span>约 {post['minutes']} 分钟</span>
        {tags}
      </div>
      <h1>{esc(post['title'])}</h1>
      <p class="art-sum">{esc(post['summary'])}</p>
      <hr class="art-rule">
      <div class="prose">
{post['html']}
      </div>
      <div class="art-foot">
        {"".join(nav_links)}
      </div>
    </div>
  </article>
"""
    desc = post["summary"][:150]
    return page(f"{post['title']} — {SITE['name']}", desc,
                f"/blog/{post['slug']}.html", body, "/blog/", og_type="article")


def build_sitemap(posts):
    urls = ["/", "/about.html", "/projects.html", "/blog/"] + [f"/blog/{p['slug']}.html" for p in posts]
    items = "\n".join(f'  <url><loc>{SITE["base"]}{u}</loc></url>' for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + items + "\n</urlset>\n")


def build_robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE['base']}/sitemap.xml\n"


# ────────────────────────────── 主流程 ──────────────────────────────
def main():
    posts = load_posts()
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "blog"), exist_ok=True)

    open(os.path.join(ROOT, "assets", "site.css"), "w", encoding="utf-8").write(CSS.lstrip())
    open(os.path.join(ROOT, "assets", "site.js"), "w", encoding="utf-8").write(JS.lstrip())

    files = {
        "index.html": build_home(posts),
        "about.html": build_about(posts),
        "projects.html": build_projects(posts),
        os.path.join("blog", "index.html"): build_blog_index(posts),
        "sitemap.xml": build_sitemap(posts),
        "robots.txt": build_robots(),
    }
    for post in posts:
        files[os.path.join("blog", f"{post['slug']}.html")] = build_post(post, posts)

    for rel, content in files.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(content)
        print(f"  wrote {rel:52s} {len(content):>7,d} chars")
    print(f"\n{len(files)} pages + assets/site.css ({len(CSS):,d}) + assets/site.js ({len(JS):,d}) · {len(posts)} post(s)")


if __name__ == "__main__":
    main()
