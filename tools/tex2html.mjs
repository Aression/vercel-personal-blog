// 构建时把 TeX 批量渲染成 KaTeX 静态 HTML。
// 用法：node tools/tex2html.mjs  （stdin 读 JSON，stdout 写 JSON）
//   入：{"items":[{"id":"m1","tex":"E=mc^2","display":false}, ...]}
//   出：{"m1":"<span class=\"katex\">…</span>", ...}
// 出错时该条返回 {"error": "..."}，由 build.py 决定降级方式。
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(__dirname, '..', 'package.json'));

let katex;
try {
  katex = require('katex');
} catch (e) {
  console.error('KATEX_MISSING: ' + e.message);
  process.exit(3);
}

let raw = '';
process.stdin.setEncoding('utf8');
for await (const chunk of process.stdin) raw += chunk;

const out = {};
try {
  const input = JSON.parse(raw || '{}');
  for (const it of (input.items || [])) {
    try {
      out[it.id] = katex.renderToString(it.tex, {
        displayMode: !!it.display,
        throwOnError: false,
        errorColor: '#b91c1c',
        strict: false,
        trust: false,
        output: 'html',
        macros: { '\\RR': '\\mathbb{R}', '\\NN': '\\mathbb{N}', '\\EE': '\\mathbb{E}', '\\PP': '\\mathbb{P}' },
      });
    } catch (e) {
      out[it.id] = { error: String(e && e.message ? e.message : e) };
    }
  }
} catch (e) {
  console.error('BAD_INPUT: ' + e.message);
  process.exit(4);
}
process.stdout.write(JSON.stringify(out));
