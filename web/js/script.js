// EP015 narration, verbatim from the approved script (Google Doc).
// Parts are separated by ### exactly like the kit's script.txt.
//
// TIMING NOTE: the real episode times cuts from word-level ASR alignment of the
// eight VO WAVs (kit v2: asr.py -> align.py -> cues.py T(v, "phrase")). Those
// WAVs are not in this repo, so the engine derives SYNTHETIC word timings from
// a speaking rate to make the rig testable. Every timing in the player is
// therefore provisional and will be replaced by real alignment.

export const WPM = 155; // tuned so Part 0 synthetic length ~= the storyboard WAV length (106.44s)

export const PARTS = [
  {
    id: "p0",
    card: "PART 0: THE CRASH THAT MADE SOME MEN RICH",
    text: `October 1929. Wall Street is collapsing. Stock prices are crashing. Investors are panicking. Fortunes that took decades to build are disappearing in days. Imagine waking up, checking your investments, and discovering that your retirement plan has suddenly become a very expensive piece of paper. For millions of Americans, the financial nightmare was only beginning. But while the stock market was collapsing, one man was making an extraordinary amount of money. His name was Jesse Livermore. And unlike everyone desperately praying for stock prices to recover, Livermore had been betting that they would fall. The worse the market performed, the more money he stood to make. And he wasn't alone. Another wealthy businessman named Joseph Kennedy had also positioned himself to survive the disaster. While ordinary investors watched their savings disappear, these men found ways to protect their fortunes and even increase them. So how exactly did they do it? Was it genius? Luck? Inside information? Or did they simply understand something about money that everyone else had forgotten? And here's the strangest part. One of these men would eventually lose nearly everything he had made. Because making a fortune and keeping a fortune are two completely different skills. To understand this story, we need to go back a few years. To a time when America was absolutely convinced that everyone could become rich.`,
  },
];

// Build word timings. Real pipeline replaces this with words.json from align.py.
export function buildWords(part, wpm = WPM) {
  const tokens = part.text.trim().split(/\s+/);
  const secPerWord = 60 / wpm;
  let t = 0;
  return tokens.map((w) => {
    // Long words and sentence ends get a little more time; commas a beat.
    let dur = secPerWord * (0.6 + 0.4 * Math.min(w.length / 5, 1.6));
    if (/[.!?]$/.test(w)) dur += 0.34;
    else if (/[,;:]$/.test(w)) dur += 0.16;
    const word = { w, t0: t, t1: t + dur };
    t += dur + secPerWord * 0.12; // inter-word gap
    return word;
  });
}
