// Cue matching: locate a storyboard VO excerpt inside a part's word stream.
//
// Lives in its own module so the headless smoke test (tools/smoke_test.mjs)
// exercises the same matcher the live rig does. When this logic lived inside
// engine.js the test had to reimplement it, and the two silently diverged -
// the reimplementation reported 14 unmatched cues where the real one finds 4.

/** Lowercase, strip punctuation and curly quotes. Whitespace is preserved. */
export const normalize = (s) => String(s)
  .replace(/[\u2018\u2019]/g, "'")
  .replace(/[\u201C\u201D]/g, '"')
  .toLowerCase()
  .replace(/[^a-z0-9'\s]/g, "")
  .trim();

/**
 * Index of the first word of `phrase` within `words`, or -1.
 *
 * Storyboard cues are anchoring EXCERPTS, not transcripts: they paraphrase,
 * change tense, and elide across sentences ("... becomes wealthy without ever
 * building a business yourself"). So an exact contiguous match often does not
 * exist. We try the full phrase and then progressively shorter leading runs,
 * never below 3 words because "October 1929." is only two, down to whatever is
 * left if the phrase is shorter than that.
 *
 * Comparison is prefix-based: the narrator's "becoming" should still match a
 * cue written as "become".
 */
export function findPhrase(words, phrase) {
  const toks = words.map((x) => normalize(x.w));
  const want = normalize(phrase).split(/\s+/).filter(Boolean);
  if (!want.length || !toks.length) return -1;
  const floor = Math.min(3, want.length);
  for (let len = want.length; len >= floor; len--) {
    const sub = want.slice(0, len);
    for (let i = 0; i + sub.length <= toks.length; i++) {
      let ok = true;
      for (let j = 0; j < sub.length; j++) {
        if (!toks[i + j].startsWith(sub[j])) { ok = false; break; }
      }
      if (ok) return i;
    }
  }
  return -1;
}
