/**
 * Phase 17 — low-literacy / low-vision display preferences.
 *
 * Font size and high-contrast are persisted in localStorage and applied to the
 * document root, so a low-literacy or low-vision user can set them once (from
 * /settings or the onboarding flow) and have every screen honour them. Kept as
 * plain functions so both React and the pre-hydration index inline script can
 * use them without importing React.
 */
export const FONT_SIZES = ['sm', 'md', 'lg'] as const;
export type FontSize = (typeof FONT_SIZES)[number];

const FONT_KEY = 'kp-font-size';
const CONTRAST_KEY = 'kp-high-contrast';

const FONT_CLASS: Record<FontSize, string> = {
  sm: 'kp-font-sm',
  md: '',
  lg: 'kp-font-lg',
};

export function getFontSize(): FontSize {
  if (typeof localStorage === 'undefined') return 'md';
  const v = localStorage.getItem(FONT_KEY);
  return v === 'sm' || v === 'lg' ? v : 'md';
}

export function getHighContrast(): boolean {
  if (typeof localStorage === 'undefined') return false;
  return localStorage.getItem(CONTRAST_KEY) === '1';
}

export function setFontSize(size: FontSize): void {
  if (typeof localStorage !== 'undefined') localStorage.setItem(FONT_KEY, size);
  applyDisplayPrefs();
}

export function setHighContrast(on: boolean): void {
  if (typeof localStorage !== 'undefined') localStorage.setItem(CONTRAST_KEY, on ? '1' : '0');
  applyDisplayPrefs();
}

/** Re-apply the stored prefs to <html>. Idempotent; call on boot and on change. */
export function applyDisplayPrefs(): void {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  // Only remove real class tokens: the 'md' size maps to '' (default) and
  // DOMTokenList.remove('') throws a DOMException, so skip empty tokens.
  FONT_SIZES.forEach((s) => {
    const token = FONT_CLASS[s];
    if (token) root.classList.remove(token);
  });
  const cls = FONT_CLASS[getFontSize()];
  if (cls) root.classList.add(cls);
  root.classList.toggle('kp-high-contrast', getHighContrast());
}
