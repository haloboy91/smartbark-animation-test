import {
  Camera,
  Circle,
  Gradient,
  Node,
  Polygon,
  Rect,
  Txt,
  makeScene2D,
} from '@motion-canvas/2d';
import {
  Vector2,
  all,
  createRef,
  createSignal,
  delay,
  easeInOutSine,
  loop,
} from '@motion-canvas/core';
import type {ThreadGenerator} from '@motion-canvas/core';

import {EllyRig, type EllyPose, type MouthShape} from '../rig/ellyRig';
import {SCENE_DURATION, poseAt} from '../rig/animation';

const DIAMONDS: Array<[number, number, number]> = [
  [-760, -380, 26], [-540, -250, 18], [-260, -420, 22],
  [120, -360, 18], [420, -460, 24], [760, -180, 18],
];
const DOTS: Array<[number, number, number]> = [
  [-820, -180, 8], [-640, -460, 6], [-420, -330, 9], [-150, -220, 7],
  [60, -470, 6], [280, -260, 8], [560, -360, 7], [830, -380, 9], [-880, -420, 7],
];

export default makeScene2D(function* (view) {
  // One clock drives every pose signal: the articulation timeline lives in
  // animation.ts and is identical to the headless renderer's math.
  const clock = createSignal(0);
  const pose = (): ReturnType<typeof poseAt> => poseAt(clock());

  const rigPose: EllyPose = {
    rootX: () => pose().rootX,
    rootY: () => pose().rootY,
    rootScale: () => pose().rootScale,
    rootRotation: () => pose().rootRotation,
    legL: () => pose().legL,
    legR: () => pose().legR,
    legFlexL: () => pose().flexL,
    legFlexR: () => pose().flexR,
    spine: () => pose().spine,
    head: () => pose().head,
    armL: () => pose().armL,
    armR: () => pose().armR,
    armScale: () => pose().armScale as number,
    earL: () => pose().earL,
    earR: () => pose().earR,
    tail: () => pose().tail,
    blink: () => pose().blink,
    gaze: () => new Vector2(pose().gazeX, pose().gazeY),
    browLift: () => pose().browLift,
    mouth: () => pose().mouth as MouthShape,
    mouthOpen: () => pose().mouthOpen,
  };

  const camera = createRef<Camera>();
  const shadow = createRef<Circle>();
  const coinRef = createRef<Node>();
  const diamondRefs = DIAMONDS.map(() => createRef<Polygon>());
  const dotRefs = DOTS.map(() => createRef<Circle>());

  view.add(
    <Camera ref={camera}>
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
      {DIAMONDS.map(([x, y, size], i) => (
        <Polygon key={`d${i}`} ref={diamondRefs[i]} sides={4} x={x} y={y}
          width={size} height={size} fill="#ffe9a8" opacity={0.7} />
      ))}
      {DOTS.map(([x, y, size], i) => (
        <Circle key={`o${i}`} ref={dotRefs[i]} x={x} y={y}
          width={size} height={size} fill="#fdf6dd" opacity={0.6} />
      ))}
      <Circle width={320} height={320} x={610} y={-325} fill="#ffedb0" opacity={0.18} />
      <Circle width={150} height={150} x={610} y={-325} fill="#f6e7bd"
        shadowBlur={70} shadowColor="#ffedb0" />
      <Circle width={2500} height={820} y={760} fill="#252b52" />
      <Circle width={2100} height={720} x={-380} y={820} fill="#1f2547" />
      <Rect width={1920} height={220} y={500} fill="#1a1f3d" />
      <Circle width={1500} height={190} y={470} fill="#232a55" />

      {/* Contact shadow follows the root, shrinking on lifts/bends.
          rootY is y-up, so its screen (y-down) position is negated. */}
      <Circle
        ref={shadow}
        width={330}
        height={52}
        fill="#0a0c1c"
        opacity={0.5}
        shadowBlur={14}
        shadowColor="#000000"
        x={() => pose().rootX}
        y={() => -(pose().rootY + 14)}
        scale={() => 1 - clamp01((-450 - pose().rootY) / 400) * 0.35}
      />

      <EllyRig pose={rigPose}>
        {/* Coin lives in the rig root so attached coordinates match. The
            inner counter-flip keeps its highlight upright under the root's
            y-axis flip (circles themselves are symmetric). */}
        <Node
          ref={coinRef}
          x={() => pose().coin.x}
          y={() => pose().coin.y}
          scale={() => pose().coin.scale}
          opacity={() => (pose().coin.visible ? 1 : 0)}
        >
          <Node scale={[1, -1]}>
            <Node scale={() => [Math.cos(pose().coin.spin), 1]}>
              <Circle width={64} height={64} fill="#e3b65b" stroke="#8a6a2f" lineWidth={5} />
              <Circle width={42} height={42} fill="#f3d27e" stroke="#b98f3c" lineWidth={3} />
              <Circle width={12} height={12} x={-9} y={-9} fill="#fff3cf" opacity={0.9} />
            </Node>
          </Node>
        </Node>
      </EllyRig>

      <Txt text={'SMART BARK'} x={700} y={435} fontSize={30} letterSpacing={6}
        fill={'rgba(255,255,255,0.45)'} fontFamily={'Arial, sans-serif'} />
    </Camera>,
  );

  // Ambient twinkle (finite loops so the scene length stays exact).
  const twinkle = (i: number, getNode: () => {
    opacity(value: number, duration: number, timing: typeof easeInOutSine): ThreadGenerator;
  }) =>
    delay(
      (i * 0.35) % 2,
      loop(6, function* () {
        yield* getNode().opacity(0.2, 0.8, easeInOutSine);
        yield* getNode().opacity(1, 0.8, easeInOutSine);
      }),
    );
  const ambient = all(
    ...diamondRefs.map((ref, i) => twinkle(i, ref)),
    ...dotRefs.map((ref, i) => twinkle(i + diamondRefs.length, ref)),
  );

  // Camera push-in read from the same timeline.
  camera().zoom(() => pose().cameraZoom);

  // Linear clock: all easing is authored inside poseAt().
  yield* all(ambient, clock(SCENE_DURATION, SCENE_DURATION));
});

function clamp01(v: number) {
  return Math.max(0, Math.min(1, v));
}
