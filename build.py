#!/usr/bin/env python3
"""lvdi-profile 静态站点生成器（v2）

源：content/posts/*.md（文章）  content/pages/*.md（独立页）
出：index.html / about.html / projects.html / blog/index.html / blog/<slug>.html
    /<page>.html / feed.xml / sitemap.xml / robots.txt
    assets/site.css 与 assets/site.js 是真源文件，不再由本脚本生成。

数学：构建时用 KaTeX 渲染成静态 HTML（node + tools/tex2html.mjs），页面零 JS 依赖。
      缺 node/katex 时降级为等宽字体原文，构建不中断。

用法：python3 build.py
"""

import os
import re
import html
import json
import subprocess
from datetime import datetime, timezone, timedelta

try:
    import markdown as mdlib
    from markdown.extensions import Extension
    from markdown.preprocessors import Preprocessor
except ImportError:
    raise SystemExit("需要 markdown 包：python3 -m pip install markdown")

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = {
    "name": "吕迪",
    "name_en": "LYU Di",
    "handle": "@Aression",
    "tagline": "Agentic RL · AI Infra",
    "status": "上海 · 白天写 Agentic RL / AI Infra，晚上折腾本地推理栈",
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

TZ = timezone(timedelta(hours=8))


def esc(s):
    return html.escape(str(s), quote=True)


# ══════════════════════════ 代码高亮 ══════════════════════════
LANG_ALIAS = {
    "py": "python", "python3": "python",
    "js": "javascript", "ts": "javascript", "typescript": "javascript",
    "jsx": "javascript", "tsx": "javascript", "node": "javascript", "jsonc": "json",
    "sh": "bash", "shell": "bash", "zsh": "bash", "console": "bash", "powershell": "bash", "ps1": "bash",
    "yml": "yaml", "c++": "cpp", "cc": "cpp", "h": "cpp", "hpp": "cpp",
    "rs": "rust", "golang": "go", "htm": "html", "xml": "html", "vue": "html", "svg": "html",
    "plain": "text", "plaintext": "text", "": "text", "txt": "text", "log": "text", "diff": "text",
}

HL_LANGS = {
    "python": {
        "kw": "and as assert async await break class continue def del elif else except finally for "
              "from global if import in is lambda nonlocal not or pass raise return try while with yield match case",
        "bi": "print len range enumerate zip map filter sum min max sorted reversed list dict set tuple frozenset "
              "str int float bool bytes bytearray open isinstance issubclass getattr setattr hasattr delattr type "
              "super vars dir round abs any all next iter format repr hash id object Exception ValueError "
              "TypeError KeyError RuntimeError self cls",
        "lc": ["#"], "bc": [], "strs": ['"""', "'''", '"', "'"],
    },
    "javascript": {
        "kw": "async await break case catch class const continue debugger default delete do else export extends "
              "finally for from function get if import in instanceof let new of return set static super switch "
              "this throw try typeof var void while yield enum implements interface type declare namespace readonly public private",
        "bi": "console window document JSON Math Object Array String Number Boolean Promise Map Set WeakMap WeakSet "
              "Symbol Date RegExp Error parseInt parseFloat isNaN require module exports process fetch setTimeout "
              "setInterval clearTimeout clearInterval queueMicrotask structuredClone BigInt",
        "lc": ["//"], "bc": [("/*", "*/")], "strs": ['"', "'", "`"],
    },
    "bash": {
        "kw": "if then else elif fi for while do done case esac function return in select until time coproc "
              "local export readonly declare unset shift source alias eval exec exit trap set break continue",
        "bi": "echo printf cd pwd ls cp mv rm mkdir rmdir touch cat head tail grep sed awk sort uniq wc find xargs "
              "curl wget git npm npx node python3 pip docker sudo chmod chown export tee kill ps top df du "
              "ssh scp tar zip unzip make cmake systemctl journalctl sleep true false test",
        "lc": ["#"], "bc": [], "strs": ['"', "'"],
    },
    "json": {
        "kw": "true false null", "bi": "",
        "lc": [], "bc": [], "strs": ['"'],
    },
    "yaml": {
        "kw": "true false null yes no on off", "bi": "",
        "lc": ["#"], "bc": [], "strs": ['"', "'"],
    },
    "sql": {
        "kw": "select from where group by order having limit offset insert into values update set delete create "
              "table drop alter add index view join inner left right outer full on as and or not null is in "
              "between like exists union all distinct case when then else end primary key foreign references "
              "default unique with recursive explain analyze begin commit rollback transaction",
        "bi": "count sum avg min max coalesce cast substring length now date current_timestamp row_number "
              "over partition rank dense_rank",
        "lc": ["--"], "bc": [("/*", "*/")], "strs": ["'", '"'],
    },
    "java": {
        "kw": "abstract assert boolean break byte case catch char class const continue default do double else enum "
              "extends final finally float for goto if implements import instanceof int interface long native new "
              "package private protected public return short static strictfp super switch synchronized this throw "
              "throws transient try void volatile while var record sealed permits",
        "bi": "String Integer Long Double Boolean Character Object System List Map Set ArrayList HashMap HashSet "
              "Optional Stream Arrays Collections Math Thread Runnable Exception RuntimeException",
        "lc": ["//"], "bc": [("/*", "*/")], "strs": ['"', "'"],
    },
    "cpp": {
        "kw": "alignas alignof auto bool break case catch char class const constexpr continue decltype default "
              "delete do double else enum explicit export extern false float for friend goto if inline int long "
              "mutable namespace new noexcept nullptr operator private protected public register return short "
              "signed sizeof static static_cast struct switch template this throw true try typedef typename union "
              "unsigned using virtual void volatile while include define ifdef ifndef endif pragma",
        "bi": "std printf malloc free size_t uint8_t uint32_t int64_t string vector map unordered_map set unique_ptr "
              "shared_ptr move forward make_unique make_shared",
        "lc": ["//"], "bc": [("/*", "*/")], "strs": ['"', "'"],
    },
    "go": {
        "kw": "break case chan const continue default defer else fallthrough for func go goto if import interface "
              "map package range return select struct switch type var true false nil iota",
        "bi": "make new len cap append copy delete panic recover print println error string int int64 float64 "
              "byte rune bool any context",
        "lc": ["//"], "bc": [("/*", "*/")], "strs": ['"', "'", "`"],
    },
    "rust": {
        "kw": "as async await break const continue crate dyn else enum extern false fn for if impl in let loop "
              "match mod move mut pub ref return self Self static struct super trait true type unsafe use where while",
        "bi": "String Vec Option Result Box Rc Arc HashMap HashSet Iterator Some None Ok Err println format "
              "vec todo unimplemented unreachable assert",
        "lc": ["//"], "bc": [("/*", "*/")], "strs": ['"', "'"],
    },
    "text": {"kw": "", "bi": "", "lc": [], "bc": [], "strs": []},
}


def _tok(cls, text):
    return f'<span class="tok-{cls}">{esc(text)}</span>'


def _highlight_generic(code, spec):
    kw = set(spec["kw"].split())
    bi = set(spec["bi"].split())
    lcs = spec.get("lc") or []
    bcs = spec.get("bc") or []
    strs = sorted(spec.get("strs") or [], key=len, reverse=True)
    lit = {"true", "false", "null", "None", "True", "False", "undefined", "nil"}
    out, i, n = [], 0, len(code)
    while i < n:
        ch = code[i]
        hit = False
        for a, b in bcs:
            if code.startswith(a, i):
                j = code.find(b, i + len(a))
                j = n if j < 0 else j + len(b)
                out.append(_tok("com", code[i:j])); i = j; hit = True; break
        if hit:
            continue
        for p in lcs:
            if code.startswith(p, i):
                j = code.find("\n", i)
                j = n if j < 0 else j
                out.append(_tok("com", code[i:j])); i = j; hit = True; break
        if hit:
            continue
        for q in strs:
            if code.startswith(q, i):
                if len(q) == 3:
                    j = code.find(q, i + 3)
                    j = n if j < 0 else j + 3
                else:
                    j = i + 1
                    while j < n:
                        if code[j] == "\\":
                            j += 2; continue
                        if code[j] == q:
                            j += 1; break
                        if code[j] == "\n":
                            break
                        j += 1
                    j = min(j, n)
                out.append(_tok("str", code[i:j])); i = j; hit = True; break
        if hit:
            continue
        if ch.isdigit() and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] in "_.")):
            m = re.match(r"[0-9][0-9a-zA-Z_.]*", code[i:])
            out.append(_tok("num", m.group(0))); i += m.end(); continue
        if ch.isalpha() or ch in "_$":
            m = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", code[i:])
            if not m:
                out.append(esc(ch)); i += 1; continue
            w = m.group(0); j = i + m.end()
            if w in kw:
                out.append(_tok("kw", w))
            elif w in lit:
                out.append(_tok("num", w))
            elif w in bi:
                out.append(_tok("bi", w))
            elif j < n and code[j] in "(":
                out.append(_tok("fn", w))
            else:
                out.append(esc(w))
            i = j; continue
        out.append(esc(ch)); i += 1
    return "".join(out)


def _highlight_html(code):
    s = esc(code)
    s = re.sub(r'(&lt;/?)([a-zA-Z][\w:-]*)', lambda m: m.group(1) + f'<span class="tok-kw">{m.group(2)}</span>', s)
    s = re.sub(r'(&lt;!?/?[a-zA-Z][\w:-]*)((?:\s+[\w:.-]+(?:=)?)*)', lambda m: m.group(1) + m.group(2), s)
    s = re.sub(r'([\w:.-]+)=(&quot;.*?&quot;|&#x27;.*?&#x27;)',
               lambda m: f'<span class="tok-attr">{m.group(1)}</span>=<span class="tok-str">{m.group(2)}</span>', s)
    s = re.sub(r'&lt;!--.*?--&gt;', lambda m: f'<span class="tok-com">{m.group(0)}</span>', s, flags=re.S)
    return s


def _highlight_css(code):
    s = esc(code)
    s = re.sub(r'(/\*.*?\*/)', lambda m: f'<span class="tok-com">{m.group(0)}</span>', s, flags=re.S)
    s = re.sub(r'(?m)^(\s*)([.#a-zA-Z][^\n{]*?)(\s*\{)',
               lambda m: m.group(1) + f'<span class="tok-fn">{m.group(2)}</span>' + m.group(3), s)
    s = re.sub(r'([\w-]+)(\s*:\s*)([^;\n}]+)',
               lambda m: f'<span class="tok-attr">{m.group(1)}</span>{m.group(2)}<span class="tok-str">{m.group(3)}</span>', s)
    return s


def highlight(code, lang):
    key = (lang or "").strip().lower().lstrip(".")
    key = LANG_ALIAS.get(key, key)
    if key == "html":
        return _highlight_html(code)
    if key == "css":
        return _highlight_css(code)
    spec = HL_LANGS.get(key)
    if not spec or not (spec["kw"] or spec["bi"] or spec["strs"]):
        return esc(code)
    return _highlight_generic(code, spec)


# ══════════════════════════ 占位符仓库 ══════════════════════════
STASH = {}          # key -> html
MATH_JOBS = []      # [(key, tex, display)]
_uid = [0]


def _stash(payload, prefix="BLK"):
    _uid[0] += 1
    key = f"@@{prefix}{_uid[0]}@@"
    STASH[key] = payload
    return key


def finalize(out):
    """把占位符换回真实 HTML；独立成段的先剥掉外层 <p>。"""
    out = re.sub(r'<p>\s*(@@[A-Z]+\d+@@)\s*</p>',
                 lambda m: STASH.get(m.group(1), m.group(1)), out)
    out = re.sub(r'@@[A-Z]+\d+@@',
                 lambda m: STASH.get(m.group(0), m.group(0)), out)
    return out


# ══════════════════════════ 围栏代码块 ══════════════════════════
FENCE_OPEN = re.compile(r'^(\s*)(`{3,}|~{3,})[ \t]*([^\s`]*)[ \t]*(.*)$')
TITLE_KV = re.compile(r'(?:^|\s)title=["\']?([^"\']+)["\']?')


def _fence_html(code, info):
    """```python title=demo.py  /  ```python demo.py  → 带语言标签和复制按钮的代码块"""
    info = (info or "").strip()
    lang = "text"
    title = ""
    if info:
        parts = info.split(None, 1)
        lang = parts[0] if parts else "text"
        rest = parts[1].strip() if len(parts) > 1 else ""
        if rest:
            m = TITLE_KV.search(rest)
            title = (m.group(1) if m else rest).strip()
    shown = LANG_ALIAS.get(lang.lower(), lang.lower())
    body = highlight(code, lang)
    bar = [f'<div class="code-bar">']
    if title:
        bar.append(f'<span class="code-title">{esc(title)}</span>')
    bar.append(f'<span class="code-lang">{esc(shown)}</span>')
    bar.append('<button class="code-copy" type="button" aria-label="复制代码">复制</button></div>')
    return (f'<div class="code-block">{"".join(bar)}'
            f'<pre><code>{body}</code></pre></div>')


class CodeFence(Preprocessor):
    """自己实现围栏解析：支持 `title=`，并在构建时完成语法高亮。"""

    def run(self, lines):
        out, i, n = [], 0, len(lines)
        while i < n:
            m = FENCE_OPEN.match(lines[i])
            if not m:
                out.append(lines[i]); i += 1; continue
            fence = m.group(2)
            info = (m.group(3) or "")
            rest = (m.group(4) or "")
            if rest:
                info = (info + " " + rest).strip()
            body, j = [], i + 1
            while j < n and not lines[j].strip().startswith(fence):
                body.append(lines[j]); j += 1
            code = "\n".join(body)
            key = _stash(_fence_html(code, info))
            out.extend(["", key, ""])
            i = j + 1
        return out


# ══════════════════════════ 数学：KaTeX 构建时预渲染 ══════════════════════════
MATH_PATTERNS = [
    (re.compile(r'\$\$(.+?)\$\$', re.S), True),
    (re.compile(r'\\\[(.+?)\\\]', re.S), True),
    (re.compile(r'(?<![\\$])\\\((.+?)\\\)', re.S), False),
    (re.compile(r'(?<![\\$\d])\$(?!\s)([^$\n]+?)(?<!\s)\$(?![\d$])'), False),
]
FENCE_ANY = re.compile(r'^\s*(`{3,}|~{3,})')


def protect_math_line(line):
    """行内/行间公式 → 占位符。围栏代码由调用方跳过。"""
    for rx, display in MATH_PATTERNS:
        def rep(m):
            tex = m.group(1).strip()
            if not tex:
                return m.group(0)
            _uid[0] += 1
            key = f"@@MATH{_uid[0]}@@"
            MATH_JOBS.append((key, tex, display))
            STASH[key] = f'<code class="math-err">{esc(tex)}</code>'   # 先放降级内容
            return key
        line = rx.sub(rep, line)
    return line


class MathGuard(Preprocessor):
    """在代码块之后运行：围栏已变成占位符，不会误伤代码里的 $。"""

    def run(self, lines):
        return [protect_math_line(l) for l in lines]


def render_math_batch():
    """一次 node 调用渲染全部公式；失败则保留降级内容。"""
    if not MATH_JOBS:
        return 0, 0
    payload = {"items": [{"id": k, "tex": t, "display": d} for k, t, d in MATH_JOBS]}
    script = os.path.join(ROOT, "tools", "tex2html.mjs")
    ok = fail = 0
    data = {}
    try:
        proc = subprocess.run(["node", script], input=json.dumps(payload),
                              capture_output=True, text=True, timeout=180)
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
        else:
            print(f"  ! KaTeX 渲染失败（node 退出码 {proc.returncode}）：{proc.stderr.strip()[:200]}")
    except FileNotFoundError:
        print("  ! 未找到 node，公式降级为等宽原文（装 node + npm i katex 后重建即可）")
    except Exception as e:
        print(f"  ! KaTeX 渲染异常：{e}")
    for key, tex, display in MATH_JOBS:
        v = data.get(key)
        if isinstance(v, str) and v.startswith("<"):
            STASH[key] = v
            ok += 1
        else:
            fail += 1
            if isinstance(v, dict) and v.get("error"):
                print(f"  ! 公式语法错误 {tex[:40]!r}: {v['error'][:120]}")
    return ok, fail


# ══════════════════════════ 组件容器 ::: ══════════════════════════
OPEN_RE = re.compile(r'^:::([a-zA-Z][\w-]*)[ \t]*(.*)$')
CLOSE_RE = re.compile(r'^:::[ \t]*$')

CALLOUTS = {
    "note": ("box-note", "说明"),
    "tip": ("box-tip", "要点"),
    "warn": ("box-warn", "注意"),
    "insight": ("box-insight", "洞见"),
}


class Node:
    __slots__ = ("kind", "text", "name", "title", "kids")

    def __init__(self, kind, text="", name="", title="", kids=None):
        self.kind = kind
        self.text = text
        self.name = name
        self.title = title
        self.kids = kids or []


def parse_containers(lines, i=0):
    nodes = []
    while i < len(lines):
        line = lines[i]
        if CLOSE_RE.match(line):
            return nodes, i + 1
        m = OPEN_RE.match(line)
        if m:
            kids, i = parse_containers(lines, i + 1)
            nodes.append(Node("box", name=m.group(1).lower(), title=(m.group(2) or "").strip(), kids=kids))
        else:
            nodes.append(Node("text", text=line))
            i += 1
    return nodes, i


def _text_of(node):
    return "\n".join(n.text for n in node.kids if n.kind == "text").strip("\n")


def _pairs(text):
    """把「- a | b | c」列表解析成三元组，用于 metrics / bars / dl。"""
    rows = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s[0] in "-*+" and (len(s) == 1 or s[1] == " "):
            s = s[1:].strip()
        elif re.match(r'^\d+[.)]\s', s):
            s = re.sub(r'^\d+[.)]\s*', "", s)
        else:
            continue
        cells = [c.strip() for c in s.split("|")]
        if cells and any(cells):
            rows.append(cells)
    return rows


def _metrics_md(node):
    rows = _pairs(_text_of(node))
    if not rows:
        return '<div class="metrics"></div>'
    cells = []
    for r in rows:
        val = r[0] if len(r) > 0 else ""
        label = r[1] if len(r) > 1 else ""
        note = r[2] if len(r) > 2 else ""
        cls = "metric"
        if val.startswith("+"):
            cls += " metric-up"
        elif val.startswith("-"):
            cls += " metric-down"
        note_html = f'<p class="metric-n">{esc(note)}</p>' if note else ""
        cells.append(f'<div class="{cls}"><p class="metric-v">{esc(val)}</p>'
                     f'<p class="metric-l">{esc(label)}</p>{note_html}</div>')
    return f'<div class="metrics">{"".join(cells)}</div>'


def _bars_md(node):
    rows = _pairs(_text_of(node))
    if not rows:
        return '<div class="bars"></div>'
    nums = []
    for r in rows:
        nums.append([float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', r[1] if len(r) > 1 else "0")] or [0.0])
    top = max([n[0] for n in nums] + [1.0])
    lo = min([0.0] + [n[0] for n in nums])
    span = max(top - lo, 1e-9)
    out = []
    for r, num in zip(rows, nums):
        label = r[0] if r else ""
        shown = r[1] if len(r) > 1 else ""
        note = f' <span class="bar-n">{esc(r[2])}</span>' if len(r) > 2 else ""
        w = (num[0] - lo) / span * 100
        out.append(f'<div class="bar-row"><span class="bar-l" title="{esc(label)}">{esc(label)}</span>'
                   f'<span class="bar-t"><span class="bar-f" data-w="{max(w, 1.5):.1f}"></span></span>'
                   f'<span class="bar-v">{esc(shown)}{note}</span></div>')
    return f'<div class="bars">{"".join(out)}</div>'


def _dl_md(node):
    rows = _pairs(_text_of(node))
    out = []
    for r in rows:
        k = r[0] if r else ""
        v = " | ".join(r[1:]) if len(r) > 1 else ""
        out.append(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>')
    return f'<dl class="dl">{"".join(out)}</dl>'


def render_nodes(nodes):
    """把容器树渲染成「markdown 源 + HTML 混合」文本，再交 md_in_html 统一解析。

    容器输出前后补空行：块级 HTML 必须与相邻的 markdown 段落隔开，
    否则 md_in_html 会把它当行内 HTML 塞进 <p>。
    """
    parts = []
    for n in nodes:
        if n.kind == "text":
            parts.append(n.text)
        else:
            parts.append("\n" + render_container(n) + "\n")
    return "\n".join(parts)


def render_container(n):
    name, title, kids = n.name, n.title, n.kids
    inner = render_nodes(kids)
    if name in CALLOUTS:
        cls, label = CALLOUTS[name]
        head = title or label
        return (f'<div class="box {cls}" markdown="1">\n<p class="box-h">{esc(head)}</p>\n'
                f'<div class="box-b" markdown="1">\n{inner}\n</div>\n</div>')
    if name == "quote":
        src = f'\n<p class="quote-src">— {esc(title)}</p>' if title else ""
        return f'<div class="quote" markdown="1">\n{inner}{src}\n</div>'
    if name == "details":
        head = title or "展开"
        return (f'<details class="fold" markdown="1">\n<summary>{esc(head)}</summary>\n'
                f'<div class="fold-b" markdown="1">\n{inner}\n</div>\n</details>')
    if name == "aside":
        head = f'\n<p class="aside-h">{esc(title)}</p>' if title else ""
        return f'<div class="aside" markdown="1">{head}\n{inner}\n</div>'
    if name == "figure":
        src = f'\n<figcaption>{title}</figcaption>' if title else ""
        return (f'<figure class="fig" markdown="1">\n<div class="fig-b" markdown="1">\n{inner}\n</div>'
                f'{src}\n</figure>')
    if name == "tabs":
        tabs = [k for k in kids if k.kind == "box" and k.name == "tab"]
        if not tabs:
            return inner
        bar = "".join(
            f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}"'
            f'{" tabindex=\"-1\"" if i else ""}>{esc(t.title or f"标签 {i + 1}")}</button>'
            for i, t in enumerate(tabs))
        panes = "\n\n".join(
            f'<div class="tab-pane" role="tabpanel" markdown="1"{" hidden" if i else ""}>\n'
            f'{render_nodes(t.kids)}\n</div>'
            for i, t in enumerate(tabs))
        return (f'<div class="tabs" data-tabs="1" markdown="1">\n\n'
                f'<div class="tabs-bar" markdown="0">{bar}</div>\n\n'
                f'{panes}\n\n</div>')
    if name == "steps":
        steps = [k for k in kids if k.kind == "box" and k.name == "step"]
        if not steps:
            return inner
        items = "\n\n".join(
            f'<div class="step" markdown="1">\n<p class="step-t">{esc(s.title or f"第 {i + 1} 步")}</p>\n\n'
            f'<div class="step-b" markdown="1">\n{render_nodes(s.kids)}\n</div>\n\n</div>'
            for i, s in enumerate(steps))
        return f'<div class="steps" markdown="1">\n\n{items}\n\n</div>'
    if name == "compare":
        cols = [k for k in kids if k.kind == "box" and k.name == "col"]
        if not cols:
            return inner
        items = "\n\n".join(
            f'<div class="cmp-col" markdown="1">\n<p class="cmp-h">{esc(c.title or f"栏 {i + 1}")}</p>\n\n'
            f'{render_nodes(c.kids)}\n</div>'
            for i, c in enumerate(cols))
        return f'<div class="compare" markdown="1">\n\n{items}\n\n</div>'
    if name == "metrics":
        return _metrics_md(n)
    if name == "bars":
        return _bars_md(n)
    if name == "dl":
        return _dl_md(n)
    if name == "table":
        note = f'\n<p class="table-note">{esc(title)}</p>' if title else ""
        return f'<div class="sortable" markdown="1">\n{inner}\n</div>{note}'
    if name == "tab":
        return (f'<div class="tab-pane" role="tabpanel" markdown="1">\n{inner}\n</div>')
    if name == "step":
        return (f'<div class="step" markdown="1">\n<p class="step-t">{esc(title)}</p>\n{inner}\n</div>')
    if name == "col":
        return f'<div class="cmp-col" markdown="1">\n{inner}\n</div>'
    # 未知容器：原样保留内容，并提示
    print(f"  ! 未知组件 :::{name}（已按普通内容输出）")
    return inner


class Containers(Preprocessor):
    def run(self, lines):
        nodes, _ = parse_containers(list(lines))
        return render_nodes(nodes).split("\n")


# ══════════════════════════ markdown 组装 ══════════════════════════
def slugify_zh(value, name=None):
    s = re.sub(r'[^\w\u4e00-\u9fff]+', '-', value.strip().lower()).strip('-')
    return s or "sec"


class SiteExt(Extension):
    """把三个预处理器按顺序挂进 markdown 管线。

    执行顺序（优先级从高到低）：围栏代码 → 数学 → 组件容器。
    代码先变占位符，后面的 $ 与 ::: 就不会误伤代码内容。
    """

    def extendMarkdown(self, md):
        md.preprocessors.register(CodeFence(md), "lv_fence", 50)
        md.preprocessors.register(MathGuard(md), "lv_math", 45)
        md.preprocessors.register(Containers(md), "lv_containers", 40)


MD_EXTS = ["tables", "sane_lists", "footnotes", "toc", "md_in_html", "attr_list", "def_list"]


def make_md():
    md = mdlib.Markdown(extensions=MD_EXTS + [SiteExt()],
                        extension_configs={
                            "toc": {"toc_depth": "2-3", "slugify": slugify_zh, "anchorlink": False},
                            "footnotes": {"BACKLINK_TEXT": "↩", "SUPERSCRIPT_TEXT": "{}",
                                          "UNIQUE_IDS": True},
                        })
    return md


HEAD_RE = re.compile(r'<h([23]) id="([^"]+)">(.*?)</h\1>', re.S)


def add_anchors(out):
    def rep(m):
        lvl, hid, body = m.group(1), m.group(2), m.group(3)
        return (f'<h{lvl} id="{hid}"><a class="anchor" href="#{hid}" aria-hidden="true" tabindex="-1">#</a>'
                f'{body}</h{lvl}>')
    return HEAD_RE.sub(rep, out)


def render_markdown(src):
    """返回 (html 带占位符, toc_tokens)。占位符由 finalize() 统一替换。"""
    md = make_md()
    out = md.convert(src)
    toc = getattr(md, "toc_tokens", []) or []
    return add_anchors(out), toc


def toc_html(tokens, inline=False):
    items = []

    def walk(nodes, depth):
        for t in nodes:
            lvl = t.get("level", 2)
            items.append(f'<li><a class="h{lvl}" href="#{t["id"]}">{t["name"]}</a></li>')
            if t.get("children"):
                walk(t["children"], depth + 1)

    walk(tokens, 0)
    if not items:
        return ""
    head = "" if inline else '<p class="toc-h">本页目录</p>'
    return f'{head}<ul>{"".join(items)}</ul>'


# ══════════════════════════ 模板 ══════════════════════════
FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%23111111'/%3E%3Ctext x='16' y='23' "
    "font-family='-apple-system,Segoe UI,sans-serif' font-size='18' font-weight='600' "
    "fill='%23ffffff' text-anchor='middle'%3Edi%3C/text%3E%3C/svg%3E"
)


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
      <span class="sep">·</span>
      <a href="/feed.xml">RSS</a>
    </div>
    <p class="foot-meta">© <span id="year">2026</span> {SITE['name']} · {SITE['name_en']} · 手写 HTML/CSS/JS</p>
  </div>
</footer>"""


def page(title, desc, path, body, active, og_type="website", og_image=None,
         extra_head="", noindex=False):
    canonical = SITE["base"] + path
    head = [
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="theme-color" content="#ffffff">',
        f'<title>{title}</title>',
        f'<meta name="description" content="{esc(desc)}">',
        '<meta name="author" content="Di Lv (吕迪)">',
        f'<link rel="canonical" href="{canonical}">',
        f'<link rel="icon" href="{FAVICON}">',
        '<link rel="alternate" type="application/atom+xml" title="吕迪 · 文章" href="/feed.xml">',
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{canonical}">',
        '<meta property="og:locale" content="zh_CN">',
        f'<meta property="og:site_name" content="{SITE["name"]} · {SITE["name_en"]}">',
    ]
    if og_image:
        head += [
            f'<meta property="og:image" content="{og_image}">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{esc(title)}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:image" content="{og_image}">',
        ]
    else:
        head.append('<meta name="twitter:card" content="summary">')
    if noindex:
        head.append('<meta name="robots" content="noindex, follow">')
    head.append('<link rel="stylesheet" href="/assets/site.css">')
    if extra_head:
        head.append(extra_head)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
{chr(10).join(head)}
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


# ══════════════════════════ 数据 ══════════════════════════
PROJECT_GROUPS = [
    (
        "Agent / LLM Infra",
        "现在主要在做的方向：agent 的上下文与记忆、本地推理栈、以及把研究过程本身工程化",
        [
            {
                "title": "Human's Last Dashboard",
                "role": "TypeScript · 2026.10 · 进行中",
                "url": "https://github.com/Aression/human-last-dashboard",
                "points": [
                    "证据可追溯的 AGI 进展监控与递归自我改进看板，核心是一张<strong>版本化证据图</strong>：连接来源、主张、证据、能力评估、因果假设与预测",
                    "自建 L0–L7 能力分级（明确声明为项目内工作分类而非行业标准），每一级都必须过证据门与反证据检验",
                    "四条硬约束：证据先于结论、区分事实与推断、反证据是一等公民、<strong>不允许因为新闻头条自动升级阶段</strong>",
                    "输出显式置信度与验证状态，而不是一个误导性的“AGI 百分比”",
                ],
                "stack": ["TypeScript", "证据图", "数据看板"],
            },
            {
                "title": "Finding Ledger · 发现账本",
                "role": "DeepSeek Harness 插件 · 2026.10",
                "url": "https://github.com/Aression/Finding-Ledger",
                "points": [
                    "面向长程故障排查的<strong>证据化发现账本</strong>：上下文压缩、换会话、任务切换之后，只把「仍然相关且适用条件仍然成立」的发现交回模型",
                    "直指三种可复现的失败模式——压缩后遗忘、假设被摘要写成事实、结论在版本/后端变化后仍被套用",
                    "三个正交状态（认知状态 / 生命周期 / 适用性）互不替代：`refuted` 不等于 `superseded`，条件不明一律落到 `unknown` 而不是静默匹配成功",
                    "确定性规则检索 + token 预算注入，持久化在本地 SQLite（`node:sqlite`）",
                ],
                "stack": ["Node.js", "node:sqlite", "DSH 插件"],
            },
            {
                "title": "Agentic RL Atlas",
                "role": "知识库 + 研究导航 · 2026.09",
                "url": "https://agentic-rl-atlas.vercel.app",
                "points": [
                    "可持续维护的 Agentic RL 个人知识库：原子笔记 → SQLite 内容库 → 导出 JSON → 站点",
                    "内置<strong>知识图谱</strong>视图（先修、相关、共享来源、共享概念）与<strong>研究雷达</strong>：抓 HuggingFace Daily Papers，按关键词过滤后交由 DeepSeek 分成 review / archive / skip",
                    "每篇笔记标注 A–D 证据分级；深读档案必须包含主张表、机制、实验设置、证据强度、边界与反例、复现计划",
                ],
                "stack": ["Python", "SQLite", "DeepSeek", "HF Papers"],
            },
            {
                "title": "本地 KVMem 推理栈（llama-inf + 自有补丁）",
                "role": "AI Infra · 2026.09",
                "url": "https://github.com/Aression/llama-inf",
                "points": [
                    "AMD RX 9070 XT（gfx1201）上的 ROCm/HIP + KVMem 推理工作区：OpenAI 兼容单实例网关、共享模型注册表、GGUF 元数据与 KV 缓存显存预检、基准脚本",
                    "给上游打了 4 个自有补丁：HIP 可移植性修复、给 qwen35moe 注入 KV 捕获（修长文检索不生效）、放开 ngram 免 draft 自投机、Quest 式 min/max 上界打分",
                    "沉淀出一批实测约束：`ROCBLAS_USE_HIPBLASLT=0`、PATH 必须前置 ROCm SDK 的 bin 否则静默 0xC0000135、iGPU 不计入显存预算",
                ],
                "stack": ["Python", "ROCm/HIP", "llama.cpp", "KVMem", "GGUF"],
            },
            {
                "title": "dsh-maend",
                "role": "DeepSeek Harness 插件 · 2026.10",
                "url": "https://github.com/Aression/dsh-maend",
                "points": [
                    "把 MaaEnd（终末地小助手）接进 DeepSeek Harness：agent 直接跑日常、看板看进度",
                    "启动静音、成功门控的自动关游戏钩子；基于 MaaFramework v5 + MXU，带 GitHub Actions CI",
                ],
                "stack": ["Node.js", "MaaFramework", "Windows", "GitHub Actions"],
            },
        ],
    ),
    (
        "CV / 论文",
        "研究生阶段的方向，代码和论文配套",
        [
            {
                "title": "宫颈细胞病理学半监督目标检测系统",
                "role": "CV 算法 · 2025.12–2026.04",
                "url": "https://github.com/threedteam/YOLO-TCT",
                "points": [
                    "针对临床 TCT 涂片背景复杂、极端长尾与稀疏标注的确认偏差问题，设计区域级半监督框架 <strong>MPG-RSCD</strong>",
                    "基线 YOLO-TCT：自适应硬极化自注意力 + 类别平衡质量焦点损失，全局召回提升至 <strong>46.27%</strong>",
                    "医学先验引导伪标签提纯：动态门控融合 BiomedCLIP 全局语义与 ResNet50 局部纹理",
                    "1338 张真实临床涂片：高风险病变召回 <strong>58.39% → 64.98%</strong>，低误报敏感性 <strong>42.70% → 55.83%</strong>",
                ],
                "stack": ["Python", "PyTorch", "Ultralytics YOLO", "BiomedCLIP"],
            },
            {
                "title": "STTL-BLS 复现与改进",
                "role": "研究复现 · ICASSP / PR 配套",
                "url": "https://github.com/Aression/STTLBLS_rev",
                "points": [
                    "Self-Training-Transductive-Learning Broad Learning System 的复现实现，针对 GTX 3080 平台做了适配与调优",
                    "宽度学习系统的关键是把自训练与转导学习塞进闭式解框架，省掉反向传播的训练开销",
                ],
                "stack": ["Python", "PyTorch", "宽度学习"],
            },
        ],
    ),
    (
        "后端 / 系统",
        "往系统和基础设施方向转的练习",
        [
            {
                "title": "myRPC · 从零实现到性能优化",
                "role": "后端开发 · Java",
                "url": "https://github.com/Aression/myRPC",
                "points": [
                    "从零实现分布式 RPC：Netty Reactor 通信层 + 自定义私有协议解决 TCP 粘包/拆包，延迟反序列化剥离 IO 线程阻塞",
                    "Zookeeper 注册发现 + 本地缓存 &amp; Watcher；基于请求参数特征的一致性哈希负载均衡",
                    "节点级状态机熔断（半开探测 / 自动愈合）+ 纳秒级时间窗口令牌桶限流",
                    "JFR/JMC 全链路剖析：单机回环吞吐 <strong>1 万 → 9.4 万 QPS</strong>，P99 <strong>83ms</strong>，99.9% 可用性",
                ],
                "stack": ["Java", "Netty", "Zookeeper", "Kryo/Protobuf", "JFR/JMC"],
            },
        ],
    ),
    (
        "小工具 / 自动化",
        "能脚本化的绝不手动，所以顺手写了这些",
        [
            {
                "title": "ref-corrector",
                "role": "开源",
                "url": "https://github.com/Aression/ref-corrector",
                "points": [
                    "基于 <strong>LangGraph</strong> 的 BibTeX 参考文献校验与修正 CLI：解析条目、校验字段、识别重复",
                    "多源元数据交叉校验（OpenAlex / Crossref / Semantic Scholar）+ LLM 生成修正建议，输出规范化 corrected.bib 与修正报告",
                ],
                "stack": ["Python", "LangGraph", "DeepSeek"],
            },
            {
                "title": "GameWorkplace",
                "role": "开源 · 游戏工具",
                "url": "https://github.com/Aression/GameWorkplace",
                "points": [
                    "自动从 War Thunder 录像中识别并导出连杀片段，支持连杀时间阈值与最少击杀数配置",
                    "自动选择最佳视频源（单视频优先 / 必要时多视频拼接），GPU / CPU 编码自适应切换",
                ],
                "stack": ["Python", "PyQt5", "FFmpeg"],
            },
            {
                "title": "ae2-bus-scanner",
                "role": "开源",
                "url": "https://github.com/Aression/ae2-bus-scanner",
                "points": [
                    "扫描 Minecraft 存档中的 AE2 输入/输出总线与接口，定位包含指定过滤物品的设备",
                    "可复用扫描引擎 + CLI + tkinter 桌面 GUI，支持多进程并行扫描",
                ],
                "stack": ["Python", "tkinter", "多进程"],
            },
            {
                "title": "CampusAutoLogin",
                "role": "开源",
                "url": "https://github.com/Aression/CampusAutoLogin",
                "points": [
                    "dr.com 校园网自动登录后台服务：网络状态监控、断线自动认证",
                    "静默后台运行 + 系统通知，配置界面化",
                ],
                "stack": ["Python", "自动化"],
            },
            {
                "title": "TapTap 数据分析",
                "role": "课程项目 · ★7",
                "url": "https://github.com/Aression/TapTap-Big-Data-Analysis-Project",
                "points": ["TapTap 平台数据采集与分析实训项目，目前是仓库里星数最多的一个"],
                "stack": ["Python", "数据分析"],
            },
        ],
    ),
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
     "title": "图像分类宽度学习系统及其训练方法和图像分类方法"},
    {"venue": "发明专利", "year": "已受理", "role": "CN119007194A",
     "title": "多层次硬极化特征融合的 TCT 涂片自动检测系统"},
]

HONORS = [
    ("研究生国家奖学金", "国家级", "2025"),
    ("重庆大学硕士学业奖学金 一等奖", "校级", "2024–2025"),
    ("美国大学生数学建模竞赛 M 奖", "国际一等奖", "2021"),
    ("研究生电子设计竞赛 省级二等奖", "省级", "2024"),
]

SKILLS = [
    ("编程语言", ["Python", "TypeScript / Node", "Java"]),
    ("Agent / 大模型", ["Agentic RL", "LLM Agent", "强化学习", "上下文压缩与记忆", "DeepSeek Harness 插件", "RAG 检索增强", "LoRA 参数高效微调"]),
    ("推理 / AI Infra", ["vLLM 推理部署", "llama.cpp / GGUF", "KV cache 调优", "ROCm / HIP", "OpenAI 兼容网关"]),
    ("计算机视觉", ["PyTorch", "Ultralytics YOLO", "目标检测", "半监督学习", "注意力机制与损失函数设计"]),
    ("后端 / 分布式", ["Netty", "Spring Boot", "Zookeeper", "分布式 RPC", "一致性哈希", "令牌桶限流", "熔断状态机", "MySQL", "Redis"]),
    ("工程工具", ["Git", "Linux", "ROCm / HIP 工具链", "JFR/JMC 性能剖析", "SQLite", "pytest"]),
    ("英语", ["CET-6", "CET-4"]),
]
EDU = [
    ("重庆大学（985）", "计算机技术 · 硕士 | 2023.09 – 2026.06", "GPA <em>3.59/4.0</em>；方向计算机视觉，毕业论文做半监督目标检测。"),
    ("重庆大学（985）", "计算机科学与技术 · 本科 | 2019.09 – 2023.06", "GPA <em>3.46/4.0</em>；主修计算机组成原理、数据结构、计算机网络、操作系统。"),
    ("生物感知与智能信息处理", "重庆市重点实验室 · 成员", ""),
]


def card_link(p):
    if not p.get("url"):
        return ""
    label = "GitHub ↗" if "github.com" in p["url"] else "访问 ↗"
    return f'<div class="card-links"><a href="{p["url"]}" target="_blank" rel="noopener">{label}</a></div>'


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


# ══════════════════════════ 文章装载 ══════════════════════════
def parse_front_matter(raw):
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", raw, re.S)
    if not m:
        return {}, raw
    meta = {}
    for line in m.group(1).split("\n"):
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, m.group(2)


def list_md(folder):
    d = os.path.join(ROOT, folder)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith(".md") and not f.startswith("_"))


def count_minutes(body):
    zh = len(re.findall(r"[\u4e00-\u9fff]", body))
    en = len(re.findall(r"[A-Za-z]+", body))
    return max(1, round(zh / 380 + en / 200))


def parse_tags(raw):
    return [t.strip().strip('"').strip("'") for t in raw.strip().strip("[]").split(",") if t.strip()]


def load_posts():
    posts = []
    for fn in list_md(os.path.join("content", "posts")):
        raw = open(os.path.join(ROOT, "content", "posts", fn), encoding="utf-8").read()
        meta, body = parse_front_matter(raw)
        slug = fn[:-3]
        posts.append({
            "slug": slug,
            "order": int((meta.get("order", "0") or "0").strip() or 0),
            "title": meta.get("title", slug).strip('"'),
            "date": meta.get("date", "").strip('"'),
            "summary": meta.get("summary", "").strip('"'),
            "tags": parse_tags(meta.get("tags", "[]")),
            "minutes": count_minutes(body),
            "body": body,
        })
    posts.sort(key=lambda p: (p["date"], p["order"]), reverse=True)
    return posts


def load_pages():
    pages = []
    for fn in list_md(os.path.join("content", "pages")):
        raw = open(os.path.join(ROOT, "content", "pages", fn), encoding="utf-8").read()
        meta, body = parse_front_matter(raw)
        pages.append({
            "slug": meta.get("slug", fn[:-3]).strip('"'),
            "title": meta.get("title", fn[:-3]).strip('"'),
            "desc": meta.get("desc", "").strip('"'),
            "body": body,
        })
    return pages


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


# ══════════════════════════ 页面 ══════════════════════════
def build_home(posts):
    proj_cards = []
    for p in PROJECT_GROUPS[0][2][:3]:
        pts = "".join(f"<li>{x}</li>" for x in p["points"][:2])
        stack = "".join(f"<span>{esc(s)}</span>" for s in p["stack"][:4])
        link = card_link(p)
        proj_cards.append(f"""        <article class="card reveal">
          <div class="card-top"><span class="card-role">{esc(p['role'])}</span></div>
          <h3>{esc(p['title'])}</h3>
          <ul>{pts}</ul>
          <div class="stack">{stack}</div>
          {link}
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
          <p>在上海，白天写 <strong>Agentic RL</strong> 和 <strong>AI Infra</strong>——agent 的上下文与记忆、本地推理栈、RL 训练与推理基础设施那一摊；晚上大概率在折腾什么小工具。</p>
          <p>重庆大学计算机技术硕士毕业。研究生阶段做计算机视觉（长尾识别、半监督检测、医学影像），一作发过 ICASSP、共一发过 Pattern Recognition，两项发明专利，细节都在<a href="/about.html">关于</a>里；现在重心已经整个挪到 Agent 和系统方向，<a href="/projects.html">项目</a>里大半是这半年新写的。</p>
          <p>工程上是个自动化强迫症：能脚本化的绝不手动，爱折腾本地工具链和性能调优；偶尔为了搞懂原理，会把底层的东西自己实现一遍——RPC 框架、推理后端、甚至这个站点的排版。</p>
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
    og = SITE["base"] + "/assets/og/home.png" if os.path.exists(os.path.join(ROOT, "assets", "og", "home.png")) else None
    return page(f"{SITE['name']} · {SITE['name_en']} — {SITE['tagline']}", SITE["desc"], "/", body, "/", og_image=og)


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
          <p>在上海，白天写 <strong>Agentic RL</strong> 和 <strong>AI Infra</strong>——agent 的上下文与记忆、本地推理栈、RL 训练与推理基础设施那一摊；晚上大概率在折腾什么小工具。</p>
          <p>重庆大学计算机技术硕士（2026 届），本科也在重大。研究生阶段做计算机视觉：长尾识别、半监督目标检测、医学影像，一作发过 ICASSP、共一发过 Pattern Recognition，两项发明专利。现在把重心挪到 Agent 与系统方向。</p>
          <p>最近折腾的四件事：给 agent 做证据化的长期记忆（压缩之后只交回仍然成立的发现）、给 AGI 进展做一张不许被新闻头条带跑的证据看板、在 AMD 卡上搭一整套 ROCm/HIP + KVMem 的本地推理栈并给上游打了几个补丁、以及把「读论文」这件事本身工程化成一座 Agentic RL 知识库。<a href="/projects.html">项目</a>页有全部。</p>
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
    return page(f"关于 — {SITE['name']}",
                "吕迪（LYU Di）的简介、教育经历、正在做的方向、论文与专利、技能栈与荣誉。",
                "/about.html", body, "/about.html")


def build_projects(posts):
    blocks = []
    total = sum(len(g[2]) for g in PROJECT_GROUPS)
    for gname, gdesc, items in PROJECT_GROUPS:
        cards = []
        for p in items:
            pts = "".join(f"<li>{x}</li>" for x in p["points"])
            stack = "".join(f"<span>{esc(s)}</span>" for s in p["stack"])
            link = card_link(p)
            cards.append(f"""        <article class="card reveal">
          <div class="card-top"><span class="card-role">{esc(p['role'])}</span></div>
          <h3>{esc(p['title'])}</h3>
          <ul>{pts}</ul>
          <div class="stack">{stack}</div>
          {link}
        </article>""")
        blocks.append(f"""  <section class="grp">
    <div class="wrap">
      <div class="sec-head reveal">
        <h2 class="sec-title">{esc(gname)}</h2>
        <p class="sec-note">{esc(gdesc)}</p>
      </div>
      <div class="card-grid">
{chr(10).join(cards)}
      </div>
    </div>
  </section>""")

    body = f"""  <div class="page-head">
    <div class="wrap">
      <h1>项目</h1>
      <p>按方向分组，共 {total} 个。代码大多在 <a href="{SITE['github']}" target="_blank" rel="noopener">GitHub</a> 上，有几个还能跑。</p>
    </div>
  </div>

{chr(10).join(blocks)}
"""
    return page(f"项目 — {SITE['name']}",
                "吕迪的项目：Agent / LLM Infra（证据化发现账本、AGI 进展看板、本地推理栈、Agentic RL 知识库）、CV 算法、后端 RPC 与自动化小工具。",
                "/projects.html", body, "/projects.html")


def build_blog_index(posts):
    if posts:
        cards = "\n".join(post_card(p) for p in posts)
        count_note = f"目前 {len(posts)} 篇"
        listing = f"""      <ul class="post-list" data-paginate data-page-size="5" data-pager-target="#pager-posts">
{cards}
      </ul>
      <nav class="pager" id="pager-posts" data-pager aria-label="文章分页" hidden></nav>
      <p class="sec-more"><a href="/feed.xml">订阅 RSS →</a></p>"""
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
    return page(f"文章 — {SITE['name']}",
                "吕迪的技术长文与笔记：复杂性理论、Agentic RL、AI Infra、系统与工具链。",
                "/blog/", body, "/blog/")


KATEX_CSS = '<link rel="stylesheet" href="/assets/vendor/katex.min.css">'


def doc_layout(inner_head, inner_body, toc_tokens):
    """文章与独立页共用的两栏骨架：左侧目录（有目录时才占位）。"""
    toc = toc_html(toc_tokens or [])
    if toc:
        side = f'<aside class="toc-side" aria-label="目录"><nav class="toc">{toc}</nav></aside>'
        inline = (f'<details class="toc-inline"><summary>本页目录（{len(toc_tokens)} 节）</summary>'
                  f'<div class="toc-box"><nav class="toc">{toc_html(toc_tokens, inline=True)}</nav>'
                  f'</div></details>')
        layout = "art-layout"
    else:
        side, inline, layout = "", "", "art-layout no-toc"
    return f"""    <div class="{layout}">
{side}
      <div class="art-main">
{inner_head}
{inline}
        <hr class="art-rule">
        <div class="prose">
{inner_body}
        </div>
      </div>
    </div>"""


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
    head = f"""        <div class="article-head">
          <div class="art-meta">
            <span>{esc(post['date'])}</span>
            <span class="sep">·</span>
            <span>约 {post['minutes']} 分钟</span>
            {tags}
          </div>
          <h1>{esc(post['title'])}</h1>
          <p class="art-sum">{esc(post['summary'])}</p>
        </div>"""
    foot = f"""
        <div class="art-foot">
          {"".join(nav_links)}
        </div>"""
    body = (f'  <div class="progress" aria-hidden="true"></div>\n'
            f'  <article class="article">\n'
            + doc_layout(head, post["html"], post.get("toc"))
            + foot + "\n  </article>\n")
    og_png = os.path.join(ROOT, "assets", "og", f"{post['slug']}.png")
    og_image = f"{SITE['base']}/assets/og/{post['slug']}.png" if os.path.exists(og_png) else None
    extra = KATEX_CSS if post.get("has_math") else ""
    return page(f"{post['title']} — {SITE['name']}", post["summary"][:150],
                f"/blog/{post['slug']}.html", body, "/blog/", og_type="article",
                og_image=og_image, extra_head=extra)


def build_doc_page(pg):
    head = f"""        <div class="article-head">
          <h1>{esc(pg['title'])}</h1>
          <p class="art-sum">{esc(pg['desc'])}</p>
        </div>"""
    body = ('  <article class="article">\n'
            + doc_layout(head, pg["html"], pg.get("toc"))
            + "\n  </article>\n")
    extra = KATEX_CSS if pg.get("has_math") else ""
    return page(f"{pg['title']} — {SITE['name']}", pg["desc"], f"/{pg['slug']}.html",
                body, "", noindex=True, extra_head=extra)


# ══════════════════════════ feed / sitemap ══════════════════════════
def iso_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=TZ).isoformat()
    except Exception:
        return datetime.now(TZ).isoformat()


def build_feed(posts):
    entries = []
    for p in posts:
        url = f"{SITE['base']}/blog/{p['slug']}.html"
        entries.append(f"""  <entry>
    <title>{esc(p['title'])}</title>
    <link href="{url}"/>
    <id>{url}</id>
    <updated>{iso_date(p['date'])}</updated>
    <summary>{esc(p['summary'])}</summary>
  </entry>""")
    updated = iso_date(posts[0]["date"]) if posts else datetime.now(TZ).isoformat()
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{SITE['name']} · {SITE['name_en']} 的文章</title>
  <subtitle>{SITE['desc']}</subtitle>
  <link href="{SITE['base']}/feed.xml" rel="self"/>
  <link href="{SITE['base']}/blog/"/>
  <updated>{updated}</updated>
  <id>{SITE['base']}/feed.xml</id>
  <author><name>{SITE['name_en']}</name><email>{SITE['email']}</email></author>
{chr(10).join(entries)}
</feed>
"""


def build_sitemap(posts):
    urls = ["/", "/about.html", "/projects.html", "/blog/"] + [f"/blog/{p['slug']}.html" for p in posts]
    items = "\n".join(f'  <url><loc>{SITE["base"]}{u}</loc></url>' for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + items + "\n</urlset>\n")


def build_robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE['base']}/sitemap.xml\n"


# ══════════════════════════ 主流程 ══════════════════════════
def render_all(items):
    """第一阶段：渲染出带占位符的 HTML + 目录；数学占位符稍后统一填充。"""
    for it in items:
        src = it["body"]
        it["html"], it["toc"] = render_markdown(src)
        it["has_math"] = bool(re.search(r'@@MATH\d+@@', it["html"]))


def main():
    posts = load_posts()
    pages = load_pages()

    render_all(posts)
    render_all(pages)

    ok, fail = render_math_batch()
    if MATH_JOBS:
        print(f"  数学公式：{ok} 条已用 KaTeX 静态渲染" + (f"，{fail} 条降级" if fail else ""))

    for it in posts + pages:
        it["html"] = finalize(it["html"])

    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "blog"), exist_ok=True)

    files = {
        "index.html": build_home(posts),
        "about.html": build_about(posts),
        "projects.html": build_projects(posts),
        os.path.join("blog", "index.html"): build_blog_index(posts),
        "feed.xml": build_feed(posts),
        "sitemap.xml": build_sitemap(posts),
        "robots.txt": build_robots(),
    }
    for post in posts:
        files[os.path.join("blog", f"{post['slug']}.html")] = build_post(post, posts)
    for pg in pages:
        files[f"{pg['slug']}.html"] = build_doc_page(pg)

    for rel, content in files.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path) or ROOT, exist_ok=True)
        open(path, "w", encoding="utf-8").write(content)
        print(f"  wrote {rel:52s} {len(content):>7,d} chars")
    print(f"\n{len(files)} 个产物 · {len(posts)} 篇文章 · {len(pages)} 个独立页")


if __name__ == "__main__":
    main()
