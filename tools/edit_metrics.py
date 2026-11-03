#!/usr/bin/env python3
"""按 issue #1 追加的 E 节硬性指标统计文章正文。

用法：python3 tools/edit_metrics.py content/posts/xxx.md [...]

统计口径（对齐 E 节）：
- 排除 frontmatter、代码块、公式块、脚注定义、参考文献、容器标记行
- 普通正文段落 = markdown 中由空行分隔的非列表、非表格、非标题块
- 列表/表格信息块 = 列表项与表格数据行（不含表头分隔线）
- 可见字符 = 去掉 markdown 标记后的字符数（含中英文数字标点）
"""
import os
import re
import sys

META_KEYS = {"title", "date", "order", "summary", "tags"}
META_WORDS = re.compile(
    r'值得注意的是|真正的问题是|这才是关键|更重要的是|归根结底|这句话值得|'
    r'需要注意的是|值得一提的是|说到底|本质上|核心在于')
CONTRAST = re.compile(r'不是[^。；\n]{0,20}?而是')
H2 = re.compile(r'^##\s+(.+)$')
H3 = re.compile(r'^###\s+(.+)$')
LIST_ITEM = re.compile(r'^\s*(?:[-*+]\s+|\d+[.)]\s+)')
TABLE_ROW = re.compile(r'^\s*\|')
CONTAINER = re.compile(r'^:::')
FN_DEF = re.compile(r'^\[\^[^\]]+\]:')
HEADING = re.compile(r'^#{1,6}\s')


def clean_marks(s):
    """去掉 markdown 行内标记，保留可见字符。"""
    s = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', s)      # 图片
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)        # 链接
    s = re.sub(r'\[\^[^\]]+\]', '', s)                    # 脚注引用
    s = re.sub(r'`[^`]*`', 'x', s)                        # 行内代码按 1 字计
    s = re.sub(r'\*\*|__|\*|~~', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    return s.strip()


def visible_len(s):
    return len(clean_marks(s))


def analyze(path):
    raw = open(path, encoding='utf-8').read()
    # 去 frontmatter
    m = re.match(r'^---\r?\n.*?\r?\n---\r?\n', raw, re.S)
    body = raw[m.end():] if m else raw

    lines = body.split('\n')
    paras, lists, tables, h2s, h3s = [], 0, 0, [], []
    buf = []
    in_code = in_math = in_refs = False

    def flush():
        nonlocal buf
        if buf:
            text = ' '.join(buf).strip()
            if text:
                paras.append(text)
            buf = []

    for ln in lines:
        s = ln.rstrip()
        if s.strip().startswith('```'):
            in_code = not in_code
            flush(); continue
        if in_code:
            continue
        if s.strip() == '$$' or s.strip().startswith('$$'):
            in_math = not in_math if s.strip() == '$$' else in_math
            flush(); continue
        if in_math:
            continue
        if re.match(r'^##\s*(参考|参考文献|References|引用)', s):
            in_refs = True
        if in_refs and HEADING.match(s) and not s.startswith('##'):
            in_refs = False
        if in_refs:
            continue
        if FN_DEF.match(s.strip()):
            flush(); continue
        if CONTAINER.match(s.strip()):
            flush(); continue
        if H2.match(s):
            flush(); h2s.append(H2.match(s).group(1).strip()); continue
        if H3.match(s):
            flush(); h3s.append(H3.match(s).group(1).strip()); continue
        if HEADING.match(s):
            flush(); continue
        if TABLE_ROW.match(s):
            flush()
            if not re.match(r'^\s*\|[\s:|-]+\|\s*$', s):
                tables += 1
            continue
        if LIST_ITEM.match(s):
            flush(); lists += 1; continue
        if not s.strip():
            flush(); continue
        buf.append(s)
    flush()

    para_lens = [visible_len(p) for p in paras if visible_len(p) > 0]
    total = sum(para_lens)
    n = len(para_lens)
    info_blocks = n + lists + tables

    # 短句段：单句且用于强调（启发式：<=40 可见字符且只有一个句末标点）
    def is_short_single(p):
        c = clean_marks(p)
        ends = len(re.findall(r'[。！？]', c))
        return visible_len(c) <= 45 and ends <= 1 and not re.search(r'[，；：]', c)

    short_single = sum(1 for p in paras if is_short_single(p))
    consec = 0
    run = 0
    for p in paras:
        if is_short_single(p):
            run += 1
            consec = max(consec, run)
        else:
            run = 0

    full = clean_marks(body)
    meta_hits = [(w, len(re.findall(w, full))) for w in set(META_WORDS.findall(full))]

    # 引言前 15%：取正文前 15% 字符，看是否提出主问题
    intro_len = int(total * 0.15)
    intro = ''
    acc = 0
    for p in paras:
        intro += clean_marks(p) + '\n'
        acc += visible_len(p)
        if acc >= intro_len:
            break

    return {
        'file': os.path.basename(path),
        'chars': total,
        'paras': n,
        'h2': len(h2s), 'h2_titles': h2s,
        'h3': len(h3s),
        'in_60280': sum(1 for L in para_lens if 60 <= L <= 280),
        'lt50': sum(1 for L in para_lens if L < 50),
        'gt400': sum(1 for L in para_lens if L > 400),
        'max_para': max(para_lens) if para_lens else 0,
        'median': sorted(para_lens)[n // 2] if n else 0,
        'short_single': short_single,
        'short_consec_max': consec,
        'lists': lists, 'tables': tables, 'info_blocks': info_blocks,
        'meta': sum(c for _, c in meta_hits),
        'meta_detail': meta_hits,
        'contrast': len(CONTRAST.findall(full)),
        'intro_preview': intro[:220].replace('\n', ' '),
        'intro_has_problem': bool(re.search(r'问题|能否|是否|本文|这篇|取决于', intro)),
    }


def pct(a, b):
    return f"{a / b * 100:.0f}%" if b else "n/a"


def main(paths):
    for p in paths:
        r = analyze(p)
        n = r['paras']
        print(f"══════ {r['file']} ══════")
        print(f"  正文字符 {r['chars']}（target 2500-6500）  普通段落 {n}  中位 {r['median']}  最长 {r['max_para']}")
        print(f"  H2 {r['h2']}（target 3-7，max 8）  H3 {r['h3']}")
        print(f"  段落 60-280 字符: {r['in_60280']}/{n} = {pct(r['in_60280'], n)}  (需 ≥70%)")
        print(f"  段落 <50 字符:   {r['lt50']}/{n} = {pct(r['lt50'], n)}  (需 ≤15%)")
        print(f"  段落 >400 字符:  {r['gt400']}/{n} = {pct(r['gt400'], n)}  (需 ≤10%)")
        print(f"  独立短句段:      {r['short_single']}/{n} = {pct(r['short_single'], n)}  (需 ≤10%)  连续最多 {r['short_consec_max']}（需 ≤1）")
        print(f"  列表项 {r['lists']}  表格行 {r['tables']}  信息块占比 {pct(r['lists'] + r['tables'], r['info_blocks'])}  (需 ≤25%)")
        print(f"  元叙述 {r['meta']} 次（需 ≤{max(3, round(r['chars'] / 1000))} 每 3000 字 3 次）{r['meta_detail'] if r['meta_detail'] else ''}")
        print(f"  不是X而是Y: {r['contrast']} 次（需 ≤2）")
        print(f"  引言前 15% 提问题: {'是' if r['intro_has_problem'] else '否'}")
        print(f"  H2 清单: {' | '.join(r['h2_titles'])}")
        print()


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'posts')
        args = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith('.md')]
    main(args)
