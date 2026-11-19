/* ==========================================================================
   lvdi-profile · 全面重构交互引擎 (v4 — Bento OS + Terminal Telemetry)
   零依赖、全 GPU 合成高性能动效、无障碍与 prefers-reduced-motion 友好
   ========================================================================== */
(() => {
  'use strict';

  const doc = document;
  const root = doc.documentElement;
  const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const finePointer = window.matchMedia?.('(pointer: fine)').matches;

  /* — Toast 工具 — */
  let toastEl = doc.getElementById('toast');
  if (!toastEl) {
    toastEl = doc.createElement('div');
    toastEl.id = 'toast';
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'status');
    toastEl.setAttribute('aria-live', 'polite');
    doc.body.appendChild(toastEl);
  }
  let toastTimer = 0;
  function showToast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2200);
  }

  /* — 复制工具 — */
  function copyText(text, label) {
    const done = () => showToast(label || '已复制到剪贴板');
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(done, done);
    } else {
      const ta = doc.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;opacity:0';
      doc.body.appendChild(ta);
      ta.select();
      try { doc.execCommand('copy'); } catch (_) {}
      doc.body.removeChild(ta);
      done();
    }
  }

  /* — 年份与上海实时时钟 (UTC+8) — */
  const yearEl = doc.getElementById('year');
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  const clockEl = doc.getElementById('shClock');
  if (clockEl) {
    const tick = () => {
      try {
        const s = new Intl.DateTimeFormat('zh-CN', {
          timeZone: 'Asia/Shanghai',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        }).format(new Date());
        clockEl.textContent = `SHA ${s}`;
      } catch (_) {
        clockEl.textContent = 'UTC+8';
      }
    };
    tick();
    setInterval(tick, 1000);
  }

  /* — 主题切换（View Transitions 圆形扩散 + 持久化） — */
  const THEME_KEY = 'lvdi-theme';
  function getTheme() {
    try {
      const saved = localStorage.getItem(THEME_KEY);
      if (saved === 'dark' || saved === 'light') return saved;
    } catch (_) {}
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function applyTheme(theme, persist = false) {
    root.setAttribute('data-theme', theme);
    const meta = doc.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#05070c' : '#f6f8fb');
    if (persist) {
      try { localStorage.setItem(THEME_KEY, theme); } catch (_) {}
    }
    const btn = doc.getElementById('themeToggle');
    if (btn) {
      const lbl = theme === 'dark' ? '切换浅色模式' : '切换暗色模式';
      btn.setAttribute('aria-label', lbl);
      btn.setAttribute('title', `${lbl} (T)`);
    }
  }
  function toggleTheme(ev) {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    if (reduceMotion || !doc.startViewTransition) {
      applyTheme(next, true);
      showToast(next === 'dark' ? '已切换至黑曜石暗色模式' : '已切换至极简浅色模式');
      return;
    }
    const x = ev && typeof ev.clientX === 'number' ? ev.clientX : window.innerWidth - 60;
    const y = ev && typeof ev.clientY === 'number' ? ev.clientY : 40;
    const endR = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));
    const tr = doc.startViewTransition(() => applyTheme(next, true));
    tr.ready.then(() => {
      root.animate(
        { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${endR}px at ${x}px ${y}px)`] },
        { duration: 460, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', pseudoElement: '::view-transition-new(root)' }
      );
    }, () => {});
  }
  applyTheme(root.getAttribute('data-theme') || getTheme(), false);

  const themeBtn = doc.getElementById('themeToggle');
  if (themeBtn) themeBtn.addEventListener('click', (e) => toggleTheme(e));

  /* — 移动端悬浮菜单 — */
  const menuBtn = doc.getElementById('dockMenuBtn');
  const dockNav = doc.getElementById('dockNav');
  if (menuBtn && dockNav) {
    menuBtn.addEventListener('click', () => {
      const open = dockNav.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    dockNav.addEventListener('click', (e) => {
      if (e.target.tagName === 'A') {
        dockNav.classList.remove('open');
        menuBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* — Hero 神经网络点阵 Canvas（可见性感知 + 低开销 rAF） — */
  const canvas = doc.getElementById('heroCanvas');
  if (canvas && !reduceMotion) {
    const ctx = canvas.getContext('2d');
    let w = 0, h = 0, rafId = 0, visible = true;
    const mouse = { x: -999, y: -999 };
    const nodes = [];
    const COUNT = 38;

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const rect = canvas.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!nodes.length) {
        for (let i = 0; i < COUNT; i++) {
          nodes.push({
            x: Math.random() * w,
            y: Math.random() * h,
            vx: (Math.random() - 0.5) * 0.36,
            vy: (Math.random() - 0.5) * 0.36,
            r: 1.4 + Math.random() * 1.4
          });
        }
      }
    }

    function draw() {
      if (!visible || doc.hidden) { rafId = 0; return; }
      ctx.clearRect(0, 0, w, h);
      const dark = root.getAttribute('data-theme') === 'dark';
      const dotColor = dark ? 'rgba(0, 229, 160, 0.55)' : 'rgba(5, 150, 105, 0.45)';
      const lineBase = dark ? [56, 189, 248] : [2, 132, 199];

      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        a.x += a.vx;
        a.y += a.vy;
        if (a.x < 0 || a.x > w) a.vx *= -1;
        if (a.y < 0 || a.y > h) a.vy *= -1;

        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 135) {
            const alpha = (1 - dist / 135) * (dark ? 0.22 : 0.16);
            ctx.strokeStyle = `rgba(${lineBase[0]},${lineBase[1]},${lineBase[2]},${alpha.toFixed(3)})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
        const md = Math.hypot(a.x - mouse.x, a.y - mouse.y);
        if (md < 160) {
          ctx.strokeStyle = dark ? `rgba(0,229,160,${((1 - md / 160) * 0.36).toFixed(3)})` : `rgba(5,150,105,${((1 - md / 160) * 0.28).toFixed(3)})`;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(mouse.x, mouse.y);
          ctx.stroke();
        }
        ctx.fillStyle = dotColor;
        ctx.beginPath();
        ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2);
        ctx.fill();
      }
      rafId = requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener('resize', resize, { passive: true });
    if (finePointer) {
      canvas.parentElement.addEventListener('pointermove', (e) => {
        const r = canvas.getBoundingClientRect();
        mouse.x = e.clientX - r.left;
        mouse.y = e.clientY - r.top;
      }, { passive: true });
      canvas.parentElement.addEventListener('pointerleave', () => { mouse.x = -999; mouse.y = -999; });
    }
    if ('IntersectionObserver' in window) {
      new IntersectionObserver((es) => {
        visible = es[0].isIntersecting;
        if (visible && !rafId) rafId = requestAnimationFrame(draw);
      }, { threshold: 0.01 }).observe(canvas);
    }
    doc.addEventListener('visibilitychange', () => {
      if (!doc.hidden && visible && !rafId) rafId = requestAnimationFrame(draw);
    });
    rafId = requestAnimationFrame(draw);
  }

  /* — Hero Tagline 终端字符解码 — */
  const tagline = doc.getElementById('heroTagline');
  if (tagline && !reduceMotion) {
    const finalText = tagline.textContent || '';
    const glyphs = '01_/<>[]#=+*';
    let step = 0;
    const iv = setInterval(() => {
      let out = '';
      for (let i = 0; i < finalText.length; i++) {
        out += (i < step || finalText[i] === ' ' || finalText[i] === '·')
          ? finalText[i]
          : glyphs[(i + step * 3) % glyphs.length];
      }
      tagline.textContent = out;
      step += 2;
      if (step > finalText.length) {
        tagline.textContent = finalText;
        clearInterval(iv);
      }
    }, 26);
  }

  /* — 交互式极客终端 (di@shanghai:~$) — */
  const termOut = doc.getElementById('termOut');
  const termInput = doc.getElementById('termInput');
  if (termOut && termInput) {
    const CMDS = {
      help: [
        '<span class="t-acc">可用命令</span>:',
        '  <span class="t-sky">whoami</span>    查看作者档案与研究方向',
        '  <span class="t-sky">stack</span>     查看 Agentic RL / AI Infra 核心栈',
        '  <span class="t-sky">projects</span>  列出近期代表开源项目',
        '  <span class="t-sky">neofetch</span>  打印站点系统遥测信息',
        '  <span class="t-sky">theme</span>     立即切换明暗主题',
        '  <span class="t-sky">clear</span>     清空终端输出'
      ],
      whoami: [
        '<span class="t-acc">LYU Di (吕迪)</span> · @Aression · Shanghai, CN',
        'Focus: Agentic RL / Context & Memory / Local Inference Stack',
        'Edu  : Chongqing Univ (985) M.Eng (GPA 3.59) & B.Eng (GPA 3.46)',
        'Pubs : ICASSP (1st) · Pattern Recognition (Co-1st) · 2 Patents'
      ],
      stack: [
        '<span class="t-sky">[AI Infra]</span>  llama.cpp · Vulkan/CUDA · DeepSeek Harness · SQLite',
        '<span class="t-sky">[Agentic]</span>   Evidence Graph · Finding Ledger · RL Training Infra',
        '<span class="t-sky">[Systems]</span>   Python · TypeScript · Node.js · Zero-Framework Web'
      ],
      projects: [
        '1. <span class="t-acc">Human\'s Last Dashboard</span>  — 版本化证据图 + L0–L7 AGI 进展看板',
        '2. <span class="t-acc">Finding Ledger</span>          — 长程排障证据化记忆账本 (DSH 插件)',
        '3. <span class="t-acc">Agentic RL Atlas</span>        — 知识图谱 + HuggingFace Papers 雷达'
      ],
      neofetch: [
        '<span class="t-acc">di@lvdi-profile</span>',
        '----------------',
        '<span class="t-sky">Engine</span> : Zero-Framework Static HTML/CSS/JS',
        '<span class="t-sky">Math</span>   : Build-time KaTeX (0KB runtime JS)',
        '<span class="t-sky">Motion</span> : GPU Composited + View Transitions',
        '<span class="t-sky">Theme</span>  : Obsidian Dark / Lab Paper Light'
      ]
    };

    function appendLines(cmd, lines) {
      const cmdLine = doc.createElement('div');
      cmdLine.className = 'term-line';
      cmdLine.innerHTML = `<span class="t-acc">di@shanghai:~$</span> ${cmd.replace(/</g, '&lt;')}`;
      termOut.appendChild(cmdLine);
      lines.forEach((html) => {
        const div = doc.createElement('div');
        div.className = 'term-line';
        div.innerHTML = html;
        termOut.appendChild(div);
      });
      termOut.scrollTop = termOut.scrollHeight;
    }

    function execCmd(raw) {
      const c = raw.trim().toLowerCase();
      if (!c) return;
      if (c === 'clear') { termOut.innerHTML = ''; return; }
      if (c === 'theme') {
        toggleTheme();
        appendLines(c, ['<span class="t-acc">OK</span> 主题已切换。']);
        return;
      }
      if (CMDS[c]) {
        appendLines(c, CMDS[c]);
      } else {
        appendLines(c, [`<span class="t-warn">zsh: command not found: ${c.replace(/</g, '&lt;')}</span> (输入 <span class="t-sky">help</span> 查看可用命令)`]);
      }
    }

    termInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        execCmd(termInput.value);
        termInput.value = '';
      }
    });
    doc.querySelectorAll('.term-chip').forEach((chip) => {
      chip.addEventListener('click', () => execCmd(chip.getAttribute('data-cmd') || ''));
    });
  }

  /* — 交错滚动渐显 + 能力条填充 — */
  const revealEls = doc.querySelectorAll('.reveal');
  if (reduceMotion || !('IntersectionObserver' in window)) {
    revealEls.forEach((el) => el.classList.add('in'));
    doc.querySelectorAll('.tel-fill').forEach((b) => { b.style.width = (b.dataset.w || '0') + '%'; });
  } else {
    const io = new IntersectionObserver((entries) => {
      let i = 0;
      entries.forEach((en) => {
        if (en.isIntersecting) {
          en.target.style.setProperty('--stagger', Math.min(i * 60, 240) + 'ms');
          en.target.classList.add('in');
          en.target.querySelectorAll('.tel-fill').forEach((b) => {
            b.style.width = (b.dataset.w || '0') + '%';
          });
          io.unobserve(en.target);
          i++;
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });
    revealEls.forEach((el) => io.observe(el));
  }

  /* — 3D 轻量倾斜 + 指针光晕（rAF 节流，仅精确指针） — */
  if (finePointer && !reduceMotion) {
    doc.querySelectorAll('.bento-card').forEach((card) => {
      let raf = 0, mx = 0, my = 0, rx = 0, ry = 0;
      card.addEventListener('pointermove', (e) => {
        const r = card.getBoundingClientRect();
        mx = e.clientX - r.left;
        my = e.clientY - r.top;
        rx = ((my / r.height) - 0.5) * -4;
        ry = ((mx / r.width) - 0.5) * 4;
        if (!raf) {
          raf = requestAnimationFrame(() => {
            card.style.setProperty('--mx', `${mx.toFixed(1)}px`);
            card.style.setProperty('--my', `${my.toFixed(1)}px`);
            card.style.transform = `perspective(900px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) translateY(-2px)`;
            raf = 0;
          });
        }
      }, { passive: true });
      card.addEventListener('pointerleave', () => {
        card.style.transform = '';
      });
    });
  }

  /* — 文章标签实时筛选 — */
  const filterBtns = doc.querySelectorAll('.filter-btn');
  const logCards = doc.querySelectorAll('.log-card');
  if (filterBtns.length && logCards.length) {
    filterBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const tag = btn.getAttribute('data-filter');
        filterBtns.forEach((b) => b.classList.toggle('active', b === btn));
        logCards.forEach((card) => {
          const cats = (card.getAttribute('data-cat') || '').split(',');
          card.hidden = tag !== 'all' && !cats.includes(tag);
        });
      });
    });
  }

  /* ══════════════════════════════════════════════════════════════════
     子页兼容层 —— 以下能力原本由旧 site.js 提供，重写版漏掉了，
     会让 blog/index.html 分页、components.html 的标签页/条形图/可排序
     表格、以及文章正文的图片放大全部失效。此处按新代码风格补回。
     ══════════════════════════════════════════════════════════════════ */

  /* — 列表分页：[data-paginate] + 子项 [data-page-item] + 页码区 [data-pager] — */
  doc.querySelectorAll('[data-paginate]').forEach((box) => {
    const per = parseInt(box.getAttribute('data-page-size') || '5', 10);
    const items = Array.from(box.querySelectorAll('[data-page-item]'));
    const pager = doc.querySelector(box.getAttribute('data-pager-target') || '[data-pager]');
    if (items.length <= per) { if (pager) pager.hidden = true; return; }
    if (!pager) return;
    const pages = Math.ceil(items.length / per);
    let cur = 1;
    const go = (p) => {
      cur = Math.min(Math.max(p, 1), pages);
      items.forEach((el, i) => {
        el.style.display = (Math.floor(i / per) + 1 === cur) ? '' : 'none';
      });
      pager.innerHTML = '';
      const mk = (label, disabled, onClick, isCur) => {
        const b = doc.createElement('button');
        b.type = 'button';
        b.textContent = label;
        b.disabled = !!disabled;
        if (isCur) b.setAttribute('aria-current', 'page');
        b.addEventListener('click', onClick);
        pager.appendChild(b);
      };
      mk('上一页', cur === 1, () => go(cur - 1), false);
      for (let i = 1; i <= pages; i++) mk(String(i), false, () => go(i), i === cur);
      mk('下一页', cur === pages, () => go(cur + 1), false);
      const info = doc.createElement('span');
      info.className = 'pager-info';
      info.textContent = `第 ${cur} / ${pages} 页 · 共 ${items.length} 条`;
      pager.appendChild(info);
      pager.hidden = false;
    };
    go(1);
  });

  /* — 标签页：[data-tabs] > .tabs-bar 按钮 + .tab-pane 面板 — */
  doc.querySelectorAll('[data-tabs]').forEach((tabsRoot) => {
    const bar = tabsRoot.querySelector('.tabs-bar');
    const panes = tabsRoot.querySelectorAll('.tab-pane');
    if (!bar || !panes.length) return;
    const btns = bar.querySelectorAll('button');
    const sel = (i) => {
      btns.forEach((b, j) => {
        b.setAttribute('aria-selected', j === i ? 'true' : 'false');
        b.setAttribute('tabindex', j === i ? '0' : '-1');
      });
      panes.forEach((p, j) => { p.hidden = j !== i; });
    };
    btns.forEach((b, i) => {
      b.addEventListener('click', () => sel(i));
      b.addEventListener('keydown', (e) => {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        const next = e.key === 'ArrowRight'
          ? (i + 1) % btns.length
          : (i - 1 + btns.length) % btns.length;
        sel(next);
        btns[next].focus();
      });
    });
    sel(0);
  });

  /* — 条形图进场填充：.bar-f[data-w] — */
  doc.querySelectorAll('.bar-f').forEach((bar) => {
    const w = bar.getAttribute('data-w') || '0';
    if (reduceMotion || !('IntersectionObserver' in window)) {
      bar.style.width = w + '%';
      return;
    }
    const io = new IntersectionObserver((es) => {
      es.forEach((en) => {
        if (en.isIntersecting) { en.target.style.width = w + '%'; io.unobserve(en.target); }
      });
    }, { threshold: 0.4 });
    io.observe(bar);
  });

  /* — 可排序表格：.sortable table 点表头切换升降序 — */
  doc.querySelectorAll('.sortable table').forEach((table) => {
    const tbody = table.tBodies[0];
    if (!tbody) return;
    const ths = table.querySelectorAll('thead th');
    const val = (row, i) => {
      const cell = row.cells[i];
      return cell ? (cell.getAttribute('data-v') || cell.textContent || '').trim() : '';
    };
    const num = (s) => {
      const m = s.replace(/[, ]/g, '').match(/-?\d+(\.\d+)?/);
      return m ? parseFloat(m[0]) : null;
    };
    ths.forEach((th, i) => {
      th.addEventListener('click', () => {
        const dir = th.getAttribute('data-dir') === 'asc' ? 'desc' : 'asc';
        ths.forEach((o) => o.removeAttribute('data-dir'));
        th.setAttribute('data-dir', dir);
        const rows = Array.from(tbody.rows);
        const allNum = rows.every((r) => num(val(r, i)) !== null);
        rows.sort((a, b) => {
          const x = val(a, i);
          const z = val(b, i);
          const c = allNum ? num(x) - num(z) : String(x).localeCompare(String(z), 'zh');
          return dir === 'asc' ? c : -c;
        });
        rows.forEach((r) => tbody.appendChild(r));
      });
    });
  });

  /* — 正文图片放大：.prose img → .lightbox — */
  const zoomables = doc.querySelectorAll('.prose img');
  if (zoomables.length) {
    const lb = doc.createElement('div');
    lb.className = 'lightbox';
    lb.hidden = true;
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-label', '放大查看');
    const lbImg = doc.createElement('img');
    lbImg.alt = '';
    lb.appendChild(lbImg);
    doc.body.appendChild(lb);
    const closeLb = () => { lb.hidden = true; doc.body.style.overflow = ''; };
    zoomables.forEach((img) => {
      img.classList.add('zoomable');
      img.addEventListener('click', () => {
        lbImg.src = img.currentSrc || img.src;
        lbImg.alt = img.alt || '';
        lb.hidden = false;
        doc.body.style.overflow = 'hidden';
      });
    });
    lb.addEventListener('click', closeLb);
    doc.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !lb.hidden) closeLb();
    });
  }

  /* — 邮箱一键复制（读 data-mail，全站 footer 共用） — */
  const copyMailBtn = doc.getElementById('copyMailBtn');
  if (copyMailBtn) {
    copyMailBtn.addEventListener('click', () => {
      const mail = copyMailBtn.getAttribute('data-mail') || '';
      if (!mail) return;
      copyText(mail, `已复制邮箱 ${mail} ✓`);
    });
  }

  /* — 文章页：GPU 阅读进度条 + rAF ScrollSpy + 代码块复制 + 图片放大 — */
  const prog = doc.querySelector('.progress');
  const prose = doc.querySelector('.prose');
  const tocLinks = doc.querySelectorAll('.toc a[href^="#"]');
  if (prog || tocLinks.length) {
    const order = [];
    const byId = {};
    tocLinks.forEach((a) => {
      const id = a.getAttribute('href').slice(1);
      const el = doc.getElementById(id);
      if (!el) return;
      if (!byId[id]) { byId[id] = { el, top: 0, links: [] }; order.push(byId[id]); }
      byId[id].links.push(a);
    });
    let pTop = 0, pH = 0, sRaf = 0;
    const measure = () => {
      order.forEach((h) => { h.top = h.el.offsetTop; });
      if (prose) {
        const r = prose.getBoundingClientRect();
        pTop = r.top + window.scrollY;
        pH = r.height;
      }
    };
    const sync = () => {
      sRaf = 0;
      const sy = window.scrollY;
      if (order.length) {
        let active = order[0];
        for (const h of order) { if (h.top <= sy + 120) active = h; }
        tocLinks.forEach((a) => a.classList.remove('active'));
        active.links.forEach((a) => a.classList.add('active'));
      }
      if (prog && prose) {
        const total = pH - window.innerHeight * 0.6;
        const done = Math.min(Math.max(sy - pTop + 100, 0), Math.max(total, 1));
        prog.style.transform = `scaleX(${(total > 0 ? Math.min(Math.max(done / total, 0), 1) : 0).toFixed(4)})`;
      }
    };
    measure(); sync();
    window.addEventListener('scroll', () => { if (!sRaf) sRaf = requestAnimationFrame(sync); }, { passive: true });
    window.addEventListener('resize', () => { measure(); if (!sRaf) sRaf = requestAnimationFrame(sync); }, { passive: true });
  }

  doc.querySelectorAll('.code-block').forEach((block) => {
    const btn = block.querySelector('.code-copy');
    const code = block.querySelector('pre code') || block.querySelector('pre');
    if (btn && code) btn.addEventListener('click', () => copyText(code.textContent, '代码已复制 ✓'));
  });

  /* — ⌘K 快捷命令面板 — */
  const commands = [
    { label: '切换明暗主题', sub: 'Theme · T', action: () => toggleTheme() },
    { label: '首页 / Bento Index', sub: '/', href: '/' },
    { label: '关于 / About', sub: '/about.html', href: '/about.html' },
    { label: '项目 / Projects', sub: '/projects.html', href: '/projects.html' },
    { label: '技术长文 / Blog', sub: '/blog/', href: '/blog/' },
    { label: '复制联系邮箱', sub: 'lvdifine@foxmail.com', action: () => copyText('lvdifine@foxmail.com', '已复制邮箱 ✓') },
    { label: 'GitHub (@Aression)', sub: 'github.com/Aression', href: 'https://github.com/Aression', external: true },
    { label: 'RSS 订阅源', sub: '/feed.xml', href: '/feed.xml' }
  ];

  const cmdWrap = doc.createElement('div');
  cmdWrap.className = 'cmd-backdrop';
  cmdWrap.hidden = true;
  cmdWrap.innerHTML =
    '<div class="cmd-dialog" role="dialog" aria-modal="true" aria-label="快捷命令面板">' +
      '<div class="cmd-head"><span class="cmd-prompt">&gt;_</span>' +
      '<input type="text" class="cmd-input" id="cmdInput" placeholder="输入命令或页面名 (theme / blog / github)..." autocomplete="off"></div>' +
      '<ul class="cmd-list" id="cmdList" role="listbox"></ul>' +
      '<div class="cmd-foot"><span>↑↓ 选择 · Enter 执行</span><span>Esc 关闭</span></div>' +
    '</div>';
  doc.body.appendChild(cmdWrap);

  const cmdInput = doc.getElementById('cmdInput');
  const cmdList = doc.getElementById('cmdList');
  let cmdSel = 0, cmdFiltered = commands.slice();

  function renderCmd() {
    const q = (cmdInput.value || '').trim().toLowerCase();
    cmdFiltered = commands.filter((c) => !q || c.label.toLowerCase().includes(q) || c.sub.toLowerCase().includes(q));
    if (cmdSel >= cmdFiltered.length) cmdSel = 0;
    cmdList.innerHTML = '';
    cmdFiltered.forEach((c, i) => {
      const li = doc.createElement('li');
      li.className = 'cmd-item';
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', i === cmdSel ? 'true' : 'false');
      li.innerHTML = `<span>${c.label}</span><span class="cmd-item-sub">${c.sub}</span>`;
      li.addEventListener('mouseenter', () => { cmdSel = i; updateSel(); });
      li.addEventListener('click', () => runCmd(c));
      cmdList.appendChild(li);
    });
  }
  function updateSel() {
    Array.from(cmdList.children).forEach((li, i) => li.setAttribute('aria-selected', i === cmdSel ? 'true' : 'false'));
  }
  let cmdLastFocus = null;
  const closeCmd = () => {
    cmdWrap.hidden = true;
    // 关闭后把焦点还给打开它的按钮，避免键盘用户被丢回文档开头
    if (cmdLastFocus && typeof cmdLastFocus.focus === 'function') cmdLastFocus.focus();
    cmdLastFocus = null;
  };
  const openCmd = () => {
    cmdLastFocus = doc.activeElement;
    cmdWrap.hidden = false;
    cmdInput.value = '';
    cmdSel = 0;
    renderCmd();
    setTimeout(() => cmdInput.focus(), 10);
  };
  function runCmd(c) {
    closeCmd();
    if (!c) return;
    if (c.action) c.action();
    else if (c.external) window.open(c.href, '_blank', 'noopener');
    else if (c.href) window.location.href = c.href;
  }

  cmdInput.addEventListener('input', () => { cmdSel = 0; renderCmd(); });
  cmdInput.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); cmdSel = (cmdSel + 1) % Math.max(cmdFiltered.length, 1); updateSel(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); cmdSel = (cmdSel - 1 + Math.max(cmdFiltered.length, 1)) % Math.max(cmdFiltered.length, 1); updateSel(); }
    else if (e.key === 'Enter') { e.preventDefault(); runCmd(cmdFiltered[cmdSel]); }
    else if (e.key === 'Tab') { e.preventDefault(); cmdInput.focus(); }
    else if (e.key === 'Escape') { e.preventDefault(); closeCmd(); }
  });
  cmdWrap.addEventListener('click', (e) => { if (e.target === cmdWrap) closeCmd(); });

  const cmdOpenBtn = doc.getElementById('cmdOpen');
  if (cmdOpenBtn) cmdOpenBtn.addEventListener('click', openCmd);

  doc.addEventListener('keydown', (e) => {
    const tag = e.target?.tagName?.toLowerCase() || '';
    const typing = tag === 'input' || tag === 'textarea' || e.target?.isContentEditable;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      cmdWrap.hidden ? openCmd() : closeCmd();
    } else if (!typing && !e.metaKey && !e.ctrlKey && !e.altKey && e.key.toLowerCase() === 't' && cmdWrap.hidden) {
      toggleTheme();
    } else if (e.key === 'Escape' && !cmdWrap.hidden) {
      closeCmd();
    }
  });
})();
