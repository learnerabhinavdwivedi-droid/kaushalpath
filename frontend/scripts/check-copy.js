// Phase 17 — low-literacy copy audit.
//
// Walks the en + hi locale files and flags any sentence longer than MAX_WORDS
// words, because long sentences defeat the low-literacy goal of the PS. Run it
// as a warning during dev (`npm run check-copy`). Use `--strict` to fail (exit
// code 1) if any sentence is too long, for CI enforcement.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const MAX_WORDS = 14;
const STRICT = process.argv.includes('--strict');
const LOCALES = ['en', 'hi'];

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');

// Flatten a nested locale object to "a.b.c" -> leaf string pairs.
function leaves(node, prefix = '', out = {}) {
  for (const [k, v] of Object.entries(node)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object') leaves(v, path, out);
    else if (typeof v === 'string') out[path] = v;
  }
  return out;
}

// Split a string into sentences on . ! ? ; and Devanagari danda, then count words.
function sentences(str) {
  return str
    .split(/[.!?;|॥।]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

let warned = 0;
for (const locale of LOCALES) {
  const file = join(root, 'src', 'i18n', 'locales', `${locale}.json`);
  const data = JSON.parse(readFileSync(file, 'utf8'));
  const flat = leaves(data);
  for (const [key, value] of Object.entries(flat)) {
    for (const s of sentences(value)) {
      const words = s.split(/\s+/).filter(Boolean).length;
      if (words > MAX_WORDS) {
        console.warn(`[${locale}] ${key}: ${words} words > ${MAX_WORDS} -> "${s}"`);
        warned++;
      }
    }
  }
}

if (warned === 0) {
  console.log(`check-copy: all sentences within ${MAX_WORDS} words.`);
} else {
  console.log(`check-copy: ${warned} long sentence(s) flagged.`);
  if (STRICT) process.exit(1);
}
