import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const LOCALES_DIR = path.join(__dirname, '../src/i18n/locales');
const EN_PATH = path.join(LOCALES_DIR, 'en.json');
const HI_PATH = path.join(LOCALES_DIR, 'hi.json');

const en = JSON.parse(fs.readFileSync(EN_PATH, 'utf-8'));
const hi = JSON.parse(fs.readFileSync(HI_PATH, 'utf-8'));

let hasMissing = false;

function checkKeys(obj1, obj2, prefix = '') {
  for (const key in obj1) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (!(key in obj2)) {
      console.error(`Missing key in hi.json: ${fullKey}`);
      hasMissing = true;
    } else if (typeof obj1[key] === 'object' && obj1[key] !== null) {
      checkKeys(obj1[key], obj2[key], fullKey);
    }
  }
}

function checkReverseKeys(obj1, obj2, prefix = '') {
    for (const key in obj2) {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      if (!(key in obj1)) {
        console.error(`Missing key in en.json: ${fullKey}`);
        hasMissing = true;
      } else if (typeof obj2[key] === 'object' && obj2[key] !== null) {
        checkReverseKeys(obj1[key], obj2[key], fullKey);
      }
    }
  }

console.log("Checking i18n keys...");
checkKeys(en, hi);
checkReverseKeys(en, hi);

if (hasMissing) {
  console.error("i18n check failed. Missing keys found.");
  process.exit(1);
} else {
  console.log("All keys present in both locales!");
}
