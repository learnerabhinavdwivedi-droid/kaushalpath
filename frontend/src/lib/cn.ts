/** Tiny class-name joiner (no external deps). Filters falsy values. */
export function cn(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(" ");
}
