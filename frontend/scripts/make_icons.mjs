// Phase 17 — generate PWA install icons from the KaushalPath mark.
//
// We deliberately avoid a heavy rasteriser (sharp/resvg) to keep the toolchain
// lean: the favicon is a simple geometric mark, so we draw it directly into an
// RGBA buffer and hand-encode a valid PNG (zlib + CRC). This produces real,
// installable icons — 192x192, 512x512 and a 512 maskable (safe-zone) variant —
// with zero third-party dependencies.
//
//   node scripts/make_icons.mjs
import { deflateSync } from 'node:zlib';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'public');
mkdirSync(OUT, { recursive: true });

// --- palette (matches favicon.svg) ---
const DARK = [10, 10, 10, 255];
const ORANGE = [255, 79, 0, 255];
const TRANSPARENT = [0, 0, 0, 0];

// --- minimal PNG encoder (RGBA, no filtering) ---
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(bytes) {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const typeBuf = Buffer.from(type, 'ascii');
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])));
  return Buffer.concat([len, typeBuf, data, crcBuf]);
}
function encodePng(size, rgba) {
  const sig = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // color type RGBA
  const raw = Buffer.alloc(size * (size * 4 + 1));
  for (let y = 0; y < size; y++) {
    raw[y * (size * 4 + 1)] = 0; // filter: none
    rgba.copy(raw, y * (size * 4 + 1) + 1, y * size * 4, (y + 1) * size * 4);
  }
  return Buffer.concat([
    sig,
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

// --- draw the mark ---
// inset: 0 => face fills the tile; 0.12 => safe-zone for a maskable icon.
function drawIcon(size, inset) {
  const buf = Buffer.alloc(size * size * 4);
  const corner = size * 0.16; // rounded outer corners
  const cx = size / 2;
  const faceR = (size * (1 - 2 * inset)) / 2 * 0.55;
  const faceCy = size * (0.5 - inset * 0.5);
  const eyeR = faceR * 0.17;
  const eyeDx = faceR * 0.35;
  const eyeCy = faceCy - faceR * 0.18;
  const smileCy = faceCy + faceR * 0.15;
  const smileR = faceR * 0.55;
  const smileT = faceR * 0.12;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      let c = DARK;

      // transparent rounded corners -> square alpha 0 outside
      const inX = x < corner ? corner - x : x > size - corner ? x - (size - corner) : 0;
      const inY = y < corner ? corner - y : y > size - corner ? y - (size - corner) : 0;
      if (inX > 0 && inY > 0 && Math.hypot(inX, inY) > corner) c = TRANSPARENT;

      const dFace = Math.hypot(x - cx, y - faceCy);
      if (c !== TRANSPARENT && dFace <= faceR) {
        c = ORANGE;
        // eyes
        if (Math.hypot(x - (cx - eyeDx), y - eyeCy) <= eyeR ||
            Math.hypot(x - (cx + eyeDx), y - eyeCy) <= eyeR) {
          c = DARK;
        }
        // smile (bottom half of a ring)
        const dSmile = Math.hypot(x - cx, y - smileCy);
        if (y > smileCy && Math.abs(dSmile - smileR) <= smileT) c = DARK;
      }

      buf[i] = c[0];
      buf[i + 1] = c[1];
      buf[i + 2] = c[2];
      buf[i + 3] = c[3];
    }
  }
  return encodePng(size, buf);
}

const jobs = [
  ['pwa-192x192.png', 192, 0],
  ['pwa-512x512.png', 512, 0],
  ['pwa-maskable-512.png', 512, 0.14],
];
for (const [name, size, inset] of jobs) {
  writeFileSync(join(OUT, name), drawIcon(size, inset));
  console.log(`wrote public/${name} (${size}x${size})`);
}
