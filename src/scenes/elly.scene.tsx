import {
  Camera,
  Circle,
  Gradient,
  Img,
  Line,
  Node,
  Polygon,
  Rect,
  Txt,
  makeScene2D,
} from '@motion-canvas/2d';
import {
  Vector2,
  all,
  chain,
  createRef,
  createSignal,
  delay,
  easeInCubic,
  easeInOutCubic,
  easeInOutQuad,
  easeInOutSine,
  easeOutBack,
  easeOutCubic,
  loop,
  sequence,
  waitFor,
} from '@motion-canvas/core';
import type {ThreadGenerator, TimingFunction} from '@motion-canvas/core';

import ellyImage from '../assets/elly.png';

/* ------------------------------------------------------------------ */
/* Timeline constants (seconds). Total scene length is exactly 10s.    */
/* ------------------------------------------------------------------ */
const TOTAL = 10;
const INTRO = 0.5;
const WALK = 4.2;
const TURN = 0.9;
const CURIOUS = 0.6;
const ANTIC = 0.15;
const JUMP_UP = 0.3;
const JUMP_DOWN = 0.25;
const POP = 0.41; // exclamation mark + staggered accent lines
const LAND_SETTLE = 0.45;
const CAM_SETTLE = 0.3;
// Everything before the final hold is fixed-length, so the hold fills the
// remainder and the scene ends at exactly TOTAL seconds.
const HOLD =
  TOTAL -
  (INTRO +
    WALK +
    TURN +
    CURIOUS +
    ANTIC +
    JUMP_UP +
    JUMP_DOWN +
    POP +
    LAND_SETTLE +
    CAM_SETTLE);

/* Elly is 1306x1476 px, so keep that aspect ratio when sizing her. */
const ELLY_HEIGHT = 720;
const ELLY_WIDTH = (ELLY_HEIGHT * 1306) / 1476;
const GROUND_Y = 430;

/* Fixed star positions for the illustrated night sky. */
const DIAMONDS: Array<[number, number, number]> = [
  [-760, -380, 26],
  [-540, -250, 18],
  [-260, -420, 22],
  [120, -360, 18],
  [420, -460, 24],
  [760, -180, 18],
];
const DOTS: Array<[number, number, number]> = [
  [-820, -180, 8],
  [-640, -460, 6],
  [-420, -330, 9],
  [-150, -220, 7],
  [60, -470, 6],
  [280, -260, 8],
  [560, -360, 7],
  [830, -380, 9],
  [-880, -420, 7],
];

export default makeScene2D(function* (view) {
  /* ---------------------------- refs ---------------------------- */
  const camera = createRef<Camera>();
  const walkRoot = createRef<Node>(); // horizontal travel + shared origin
  const flip = createRef<Node>(); // facing direction (scaleX)
  const bob = createRef<Node>(); // walk bob / body wobble
  const body = createRef<Node>(); // squash & stretch
  const shadow = createRef<Circle>();
  const exclaim = createRef<Node>();
  const cloudA = createRef<Node>();
  const cloudB = createRef<Node>();

  const diamondRefs = DIAMONDS.map(() => createRef<Polygon>());
  const dotRefs = DOTS.map(() => createRef<Circle>());
  const accentRefs = [0, 1, 2].map(() => createRef<Line>());

  // Drives the procedural walk cycle (0 -> 12 strides during the walk).
  const phase = createSignal(0);

  /* ----------------------------- scene --------------------------- */
  view.add(
    <Camera ref={camera}>
      {/* Sky */}
      <Rect
        width={1920}
        height={1080}
        fill={
          new Gradient({
            from: new Vector2(0, -540),
            to: new Vector2(0, 540),
            stops: [
              {offset: 0, color: '#14162b'},
              {offset: 0.55, color: '#232a55'},
              {offset: 1, color: '#3a3566'},
            ],
          })
        }
      />

      {/* Twinkling diamond stars */}
      {DIAMONDS.map(([x, y, size], i) => (
        <Polygon
          key={`diamond-${i}`}
          ref={diamondRefs[i]}
          sides={4}
          x={x}
          y={y}
          width={size}
          height={size}
          fill="#ffe9a8"
          opacity={0.7}
        />
      ))}

      {/* Twinkling dot stars */}
      {DOTS.map(([x, y, size], i) => (
        <Circle
          key={`dot-${i}`}
          ref={dotRefs[i]}
          x={x}
          y={y}
          width={size}
          height={size}
          fill="#fdf6dd"
          opacity={0.6}
        />
      ))}

      {/* Moon with a soft glow */}
      <Circle width={320} height={320} x={610} y={-325} fill="#ffedb0" opacity={0.18} />
      <Circle
        width={150}
        height={150}
        x={610}
        y={-325}
        fill="#f6e7bd"
        shadowBlur={70}
        shadowColor="#ffedb0"
      />

      {/* Drifting clouds */}
      <Node ref={cloudA} x={-560} y={-250} opacity={0.08}>
        <Circle width={260} height={120} x={0} y={0} fill="#ffffff" />
        <Circle width={180} height={110} x={150} y={18} fill="#ffffff" />
        <Circle width={150} height={90} x={-150} y={24} fill="#ffffff" />
      </Node>
      <Node ref={cloudB} x={520} y={-120} opacity={0.07}>
        <Circle width={300} height={130} x={0} y={0} fill="#ffffff" />
        <Circle width={180} height={100} x={180} y={22} fill="#ffffff" />
        <Circle width={160} height={90} x={-170} y={26} fill="#ffffff" />
      </Node>

      {/* Layered hills */}
      <Circle width={2500} height={820} y={760} fill="#252b52" />
      <Circle width={2100} height={720} x={-380} y={820} fill="#1f2547" />

      {/* Ground */}
      <Rect width={1920} height={220} y={500} fill="#1a1f3d" />
      <Circle width={1500} height={190} y={470} fill="#232a55" />

      {/* Elly + contact shadow */}
      <Node ref={walkRoot} x={-1350}>
        <Circle
          ref={shadow}
          width={300}
          height={56}
          y={GROUND_Y + 22}
          fill="#0a0c1c"
          opacity={0.5}
          shadowBlur={14}
          shadowColor="#000000"
        />

        <Node ref={flip} scale={[-1, 1]}>
          <Node ref={bob}>
            <Node ref={body} y={GROUND_Y}>
              <Img
                src={ellyImage}
                width={ELLY_WIDTH}
                height={ELLY_HEIGHT}
                y={-ELLY_HEIGHT / 2}
              />
            </Node>
          </Node>
        </Node>

        {/* Surprise exclamation mark */}
        <Node ref={exclaim} x={250} y={-355} scale={0} opacity={0}>
          <Line
            points={[
              [0, -58],
              [0, 28],
            ]}
            stroke="#ffd54a"
            lineWidth={22}
            radius={11}
          />
          <Circle width={26} height={26} y={72} fill="#ffd54a" />
        </Node>

        {/* Radiating surprise accent lines */}
        <Line
          ref={accentRefs[0]}
          x={-140}
          y={-295}
          rotation={-35}
          points={[
            [-26, 0],
            [26, 0],
          ]}
          stroke="#fff2c0"
          lineWidth={9}
          radius={4.5}
          scale={0}
          opacity={0}
        />
        <Line
          ref={accentRefs[1]}
          x={-10}
          y={-330}
          points={[
            [-26, 0],
            [26, 0],
          ]}
          stroke="#fff2c0"
          lineWidth={9}
          radius={4.5}
          scale={0}
          opacity={0}
        />
        <Line
          ref={accentRefs[2]}
          x={120}
          y={-300}
          rotation={35}
          points={[
            [-26, 0],
            [26, 0],
          ]}
          stroke="#fff2c0"
          lineWidth={9}
          radius={4.5}
          scale={0}
          opacity={0}
        />
      </Node>

      {/* Channel watermark (positioned to stay inside at max 1.14x zoom) */}
      <Txt
        text={'SMART BARK'}
        x={680}
        y={435}
        fontSize={30}
        letterSpacing={6}
        fill={'rgba(255,255,255,0.45)'}
        fontFamily={'Arial, sans-serif'}
      />
    </Camera>,
  );

  /* --------------------- ambient background loop -------------------- */
  // Five 1.6s cycles (8s) plus a staggered start (<2s) stay inside 10s.
  const twinkle = (
    i: number,
    getNode: () => {
      opacity(value: number, duration: number, timing: TimingFunction): ThreadGenerator;
    },
  ) =>
    delay(
      (i * 0.35) % 2,
      loop(5, function* () {
        yield* getNode().opacity(0.2, 0.8, easeInOutSine);
        yield* getNode().opacity(1, 0.8, easeInOutSine);
      }),
    );

  const ambient = all(
    ...diamondRefs.map((ref, i) => twinkle(i, ref)),
    ...dotRefs.map((ref, i) => twinkle(i + diamondRefs.length, ref)),
    cloudA().x(140, TOTAL, easeInOutSine),
    cloudB().x(-140, TOTAL, easeInOutSine),
  );

  /* ---------------------------- main action -------------------------- */
  const story = (function* () {
    yield* waitFor(INTRO);

    // Gentle camera push-in synced with the walk. Zoom levels are kept
    // modest so Elly's head and the exclamation mark never leave the frame.

    // Procedural walk cycle: bob, wobble and volume-preserving
    // squash & stretch derived from a single phase signal.
    bob().position.y(() => Math.abs(Math.sin(phase() * Math.PI)) * -20);
    bob().rotation(() => Math.sin(phase() * Math.PI * 2) * 3);
    body().scale(() => {
      const contact = Math.cos(phase() * Math.PI * 2);
      return new Vector2(1 + contact * 0.05, 1 - contact * 0.07);
    });
    shadow().scale(() => 1 - Math.abs(Math.sin(phase() * Math.PI)) * 0.22);
    shadow().opacity(() => 0.5 - Math.abs(Math.sin(phase() * Math.PI)) * 0.18);

    // Enter from the left and walk to the center.
    yield* all(
      walkRoot().position.x(0, WALK, easeInOutQuad),
      phase(12, WALK),
      camera().zoom(1.03, WALK, easeInOutSine),
    );

    // Stop: detach the walk-cycle getters and settle back to neutral.
    bob().position.y(0);
    bob().rotation(0);
    body().scale(new Vector2(1, 1));
    shadow().scale(1);
    shadow().opacity(0.5);

    // Turn toward the camera (flip the 2D pose with a turning squash).
    yield* all(
      chain(
        waitFor(0.1),
        flip().scale.x(1, 0.4, easeInOutCubic),
        waitFor(TURN - 0.5),
      ),
      chain(
        body().scale(new Vector2(1.08, 0.92), 0.2, easeInCubic),
        body().scale(new Vector2(1, 1), TURN - 0.2, easeOutBack),
      ),
    );

    // Brief curious beat while facing the camera.
    yield* waitFor(CURIOUS);

    // Surprise: anticipation squash.
    yield* body().scale(new Vector2(1.14, 0.86), ANTIC, easeInCubic);

    // Surprise: jump up with a stretch.
    yield* all(
      bob().position.y(-90, JUMP_UP, easeOutCubic),
      body().scale(new Vector2(0.9, 1.06), JUMP_UP, easeOutCubic),
      shadow().scale(0.7, JUMP_UP, easeOutCubic),
      shadow().opacity(0.28, JUMP_UP, easeOutCubic),
    );

    // Pop the exclamation mark + accent lines.
    yield* all(
      all(exclaim().scale(1, 0.28, easeOutBack), exclaim().opacity(1, 0.15)),
      sequence(
        0.08,
        ...accentRefs.map(ref =>
          all(ref().scale(1, 0.25, easeOutBack), ref().opacity(1, 0.15)),
        ),
      ),
    );

    // Camera punch-in with a quick shake as she lands.
    const punch = camera().zoom(1.12, 0.18, easeOutCubic);
    const shake = chain(
      camera().position.x(16, 0.05, easeInOutSine),
      camera().position.x(-12, 0.05, easeInOutSine),
      camera().position.x(7, 0.05, easeInOutSine),
      camera().position.x(0, 0.07, easeInOutSine),
    );

    yield* all(
      bob().position.y(0, JUMP_DOWN, easeInCubic),
      body().scale(new Vector2(1.12, 0.88), JUMP_DOWN, easeInCubic),
      shadow().scale(1, JUMP_DOWN, easeOutCubic),
      shadow().opacity(0.5, JUMP_DOWN, easeOutCubic),
      punch,
      shake,
    );
    yield* body().scale(new Vector2(1, 1), LAND_SETTLE, easeOutBack);
    yield* camera().zoom(1.1, 0.3, easeInOutSine);

    // Hold the reaction: nervous tremble, floating exclamation, slow push.
    // Finite loop counts are used so the scene ends at exactly 10 seconds.
    yield* all(
      // 6 tremble cycles * 0.28s = 1.68s (< HOLD)
      loop(6, () =>
        chain(
          bob().rotation(1.4, 0.07, easeInOutSine),
          bob().rotation(-1.4, 0.14, easeInOutSine),
          bob().rotation(0, 0.07, easeInOutSine),
        ),
      ),
      // 2 float cycles * 0.96s = 1.92s (< HOLD)
      loop(2, () =>
        chain(
          exclaim().position.y(-343, 0.48, easeInOutSine),
          exclaim().position.y(-367, 0.48, easeInOutSine),
        ),
      ),
      camera().zoom(1.14, HOLD, easeInOutSine),
      waitFor(HOLD),
    );
  })();

  yield* all(ambient, story);
});
