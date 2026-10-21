// EP015 Part 0 shot list, transcribed from docs/EP015_storyboard_brief.txt.
//
// Shot boundaries are NOT hardcoded times. Each shot declares the `cue` phrase
// it belongs to, and the engine locates that phrase in the word stream to get
// its start time - the same idea as kit v2's cues.py T(v, "phrase"). The
// storyboard's evenly-allocated windows are explicit placeholders ("MUST re-time
// based on word-aligned VO cues"), so we ignore them entirely.
//
// When real words.json lands from asr.py/align.py, the same cues produce real
// timings with no changes here.

export const SHOTS = [
  {
    id: "S01", cue: "October 1929.",
    scene: "skyline",
    plate: "assets/scenes/s01_skyline.jpg", caption: "OCTOBER 1929",
    camera: { type: "snapZoom", from: 1.22, settle: 0.34, then: 1.08 },
    elly: [
      { t: 0.00, pose: "think",   x: 1460, y: 1020, h: 500 },
      { t: 0.55, pose: "worried", x: 1460, y: 1020, h: 500 },
    ],
    beat: "Elly looks curious -> concerned",
  },
  {
    id: "S02", cue: "Wall Street is collapsing.",
    scene: "exchange",
    plate: "assets/scenes/s02_exchange.jpg", caption: "WALL STREET COLLAPSES",
    camera: { type: "pushIn", to: 1.2 },
    shake: { amp: 16, from: 0.52, to: 0.78 },
    elly: [
      { t: 0.00, pose: "point_side", x: 1500, y: 1020, h: 520 },
      { t: 0.5,  pose: "shocked",    x: 1500, y: 1020, h: 520 },
    ],
    beat: "Elly pointing -> startled eyes",
  },
  {
    id: "S03", cue: "Investors are panicking.",
    scene: "coins",
    plate: "assets/scenes/s03_coins.jpg", caption: "FORTUNES DISAPPEAR",
    camera: { type: "pan", dx: -240, then: 0.94 },
    elly: [
      { t: 0.00, pose: "worried",   x: 1500, y: 1020, h: 500 },
      { t: 0.5,  pose: "open_arms", x: 1500, y: 1020, h: 500 },
    ],
    beat: "Elly worried -> palms raised",
  },
  {
    id: "S04", cue: "Imagine waking up,",
    scene: "breakfast",
    plate: "assets/scenes/s04_breakfast.jpg", caption: "A VERY EXPENSIVE PIECE OF PAPER",
    camera: { type: "pushIn", to: 1.24 },
    elly: [
      { t: 0.00, pose: "point_side", x: 1520, y: 1020, h: 480 },
      { t: 0.55, pose: "peek_side",  x: 1520, y: 1020, h: 480 },
    ],
    beat: "Elly gestures to paper -> incredulous half-smile",
  },
  {
    id: "S05", cue: "For millions of Americans,",
    scene: "breadline",
    plate: "assets/scenes/s05_breadline.jpg", caption: "THE NIGHTMARE BEGINS",
    camera: { type: "pan", dx: -300 },
    elly: [
      { t: 0.00, pose: "empathetic",    x: 1480, y: 1030, h: 560 },
      { t: 0.55, pose: "solemn_direct", x: 1480, y: 1030, h: 560 },
    ],
    beat: "Elly expression softens, lowers paw",
  },
  {
    id: "S06", cue: "But while the stock market was collapsing,",
    scene: "split",
    plate: "assets/scenes/s06_split.jpg", caption: "ONE MAN WAS MAKING MONEY",
    camera: { type: "pullOut", from: 1.18, to: 0.98, then: 1.1 },
    elly: [
      { t: 0.00, pose: "point_side", x: 1470, y: 1020, h: 500, flip: true },
      { t: 0.5,  pose: "think",      x: 1470, y: 1020, h: 500 },
    ],
    beat: "Elly turns her head from left to right",
  },
  {
    id: "S07", cue: "His name was Jesse Livermore.",
    scene: "hero",
    plate: "assets/scenes/s07_hero.jpg", caption: "JESSE LIVERMORE",
    camera: { type: "pushIn", to: 1.16 },
    elly: [
      { t: 0.00, pose: "open_arms", x: 1500, y: 1020, h: 520 },
      { t: 0.55, pose: "calm_nod",  x: 1500, y: 1020, h: 520 },
    ],
    beat: "Elly presentation pose -> approving nod",
  },
  {
    id: "S08", cue: "And unlike everyone desperately",
    scene: "crowd",
    plate: "assets/scenes/s08_crowd.jpg", caption: "HE BET ON THE FALL",
    camera: { type: "pan", dx: -330, zoom: 1.14 },
    elly: [
      { t: 0.00, pose: "confused", x: 1500, y: 1020, h: 500 },
      { t: 0.5,  pose: "think",    x: 1500, y: 1020, h: 500 },
    ],
    beat: "Elly puzzled -> understanding",
  },
  {
    id: "S09", cue: "The worse the market performed,",
    scene: "chips",
    plate: "assets/scenes/s09_chips.jpg", caption: "MARKET DOWN / HIS TRADE UP",
    camera: { type: "pulse", n: 2, amount: 0.1 },
    elly: [
      { t: 0.00, pose: "count_paws", x: 1490, y: 1020, h: 500 },
      { t: 0.55, pose: "shocked",    x: 1490, y: 1020, h: 500 },
    ],
    beat: "Elly counting motion -> surprised",
  },
  {
    id: "S10", cue: "And he wasn't alone.",
    scene: "doorway",
    plate: "assets/scenes/s10_doorway.jpg", caption: "JOSEPH P. KENNEDY",
    camera: { type: "pullOut", from: 1.22, to: 1.0 },
    elly: [
      { t: 0.00, pose: "point_side", x: 1460, y: 1020, h: 500 },
    ],
    beat: "Elly points toward new arrival",
  },
  {
    id: "S11", cue: "While ordinary investors watched",
    scene: "triptych", caption: "THREE DIFFERENT OUTCOMES",
    camera: { type: "parallax", dx: 90 },
    elly: [
      { t: 0.00, pose: "wince",     x: 1490, y: 1020, h: 480 },
      { t: 0.55, pose: "magnifier", x: 1490, y: 1020, h: 480 },
    ],
    beat: "Elly shifts from distressed -> investigative pose",
  },
  {
    id: "S12", cue: "So how exactly did they do it?",
    scene: "icons", caption: "GENIUS? LUCK?",
    camera: { type: "pulse", n: 3, amount: 0.07 },
    elly: [
      { t: 0.00, pose: "point_side", x: 1500, y: 1020, h: 500 },
      { t: 0.5,  pose: "think",      x: 1500, y: 1020, h: 500 },
    ],
    beat: "Elly switches pointing -> thinking",
  },
  {
    id: "S13", cue: "Inside information?",
    scene: "mystery", caption: "WHAT DID THEY UNDERSTAND?",
    camera: { type: "pushIn", to: 1.2 },
    elly: [
      { t: 0.00, pose: "skeptical_brow", x: 1480, y: 1020, h: 520 },
    ],
    beat: "Elly skeptical raised brow",
  },
  {
    id: "S14", cue: "And here's the strangest part.",
    scene: "vanish", caption: "HE LOST NEARLY EVERYTHING",
    camera: { type: "dollyInOut", inn: 1.26, out: 0.94, at: 0.62 },
    elly: [
      { t: 0.00, pose: "solemn_direct", x: 1490, y: 1020, h: 540 },
    ],
    beat: "Elly concerned, not comic",
  },
  {
    id: "S15", cue: "Because making a fortune",
    scene: "scales", caption: "MAKING ≠ KEEPING",
    camera: { type: "sway", dx: 220, zoom: 0.95 },
    elly: [
      { t: 0.00, pose: "open_arms", x: 960, y: 1030, h: 520 },
    ],
    beat: "Elly explanatory two-paw gesture",
  },
  {
    id: "S16", cue: "To understand this story,",
    scene: "city", caption: "BACK TO THE ROARING TWENTIES",
    camera: { type: "pullOut", from: 1.16, to: 1.0 },
    elly: [
      { t: 0.00, pose: "welcome_wave", x: 1470, y: 1020, h: 520 },
      { t: 0.5,  pose: "peek_side",    x: 1470, y: 1020, h: 520 },
    ],
    beat: "Elly welcoming pose -> curious smile",
  },
];
