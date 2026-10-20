import {Img, Node, Circle, Line} from '@motion-canvas/2d';
import {PossibleVector2, SignalValue, Vector2} from '@motion-canvas/core';

import earLImg from '../assets/rig/earL.png';
import earRImg from '../assets/rig/earR.png';
import headClean from '../assets/rig/head_clean.png';
import torsoImg from '../assets/rig/torso.png';
import armLImg from '../assets/rig/armL.png';
import armRImg from '../assets/rig/armR.png';
import legLImg from '../assets/rig/legL.png';
import legRImg from '../assets/rig/legR.png';
import tailImg from '../assets/rig/tail.png';

/**
 * Reusable cutout puppet rig for Elly.
 *
 * The flattened reference was decomposed into overlapping body-part layers
 * (see scripts/rig/build_rig.py). Every joint is a Node positioned at the
 * measured pivot; part images are offset so rotation happens about the joint.
 * Coordinates are rig-space (y-up), origin on the ground between the feet at
 * native image point (650, 1476).
 *
 * Global placement (root position/scale) is fully separate from articulation.
 */

export type MouthShape = 'smile' | 'open' | 'oh' | 'flat' | 'small';

export interface EllyPose {
  /** Global placement, applied to the rig root only. */
  rootX: SignalValue<number>;
  rootY: SignalValue<number>;
  rootScale: SignalValue<number>;
  rootRotation: SignalValue<number>;
  /** Joint angles in degrees, y-up convention (positive = toward screen right). */
  legL: SignalValue<number>;
  legR: SignalValue<number>;
  legFlexL: SignalValue<number>; // vertical squash of the leg (knee flex hint)
  legFlexR: SignalValue<number>;
  spine: SignalValue<number>; // waist bend
  head: SignalValue<number>; // neck rotation
  armL: SignalValue<number>;
  armR: SignalValue<number>;
  /** Cartoon stretch of the reaching arm (1 = natural art size). */
  armScale: SignalValue<number>;
  earL: SignalValue<number>;
  earR: SignalValue<number>;
  tail: SignalValue<number>;
  /** 0 = eyes open, 1 = fully closed (blink). */
  blink: SignalValue<number>;
  /** Pupil offset in head-local pixels from the rest pupil positions. */
  gaze: () => PossibleVector2;
  /** Eyebrow lift, positive = raised (surprise). */
  browLift: SignalValue<number>;
  mouth: SignalValue<MouthShape>;
  /** 0..1 mouth openness multiplier for the 'open'/'oh' shapes. */
  mouthOpen: SignalValue<number>;
}

export const DEFAULT_POSE: EllyPose = {
  rootX: 0,
  rootY: 0,
  rootScale: 1,
  rootRotation: 0,
  legL: 0,
  legR: 0,
  legFlexL: 1,
  legFlexR: 1,
  spine: 0,
  head: 0,
  armL: 0,
  armR: 0,
  armScale: 1,
  earL: 0,
  earR: 0,
  tail: 0,
  blink: 0,
  gaze: () => [0, 0],
  browLift: 0,
  mouth: 'smile',
  mouthOpen: 1,
};

// --- native pivot geometry (from rig-manifest.json) -----------------------
// pivot: rig-space joint; img: center offset of the cropped image inside its
// joint node, plus image size.
interface PartGeom {
  src: string;
  size: [number, number];
  imgOffset: [number, number];
}

function part(
  src: string,
  box: [number, number, number, number],
  pivotNative: [number, number],
  jointNative: [number, number] = pivotNative,
): {pivot: [number, number]; geom: PartGeom} {
  const [x0, y0, x1, y1] = box;
  const w = x1 - x0;
  const h = y1 - y0;
  const plx = jointNative[0] - x0;
  const ply = jointNative[1] - y0;
  const pivot: [number, number] = [
    jointNative[0] - 650,
    1476 - jointNative[1],
  ];
  return {
    pivot,
    geom: {src, size: [w, h], imgOffset: [-plx + w / 2, ply - h / 2]},
  };
}

const G = {
  legL: part(legLImg, [250, 1285, 645, 1472], [430, 1300]),
  legR: part(legRImg, [635, 1285, 1000, 1472], [820, 1300]),
  tail: part(tailImg, [945, 1220, 1130, 1390], [975, 1300]),
  // Torso rotates about the waist, not the neck pivot stored in the manifest.
  torso: part(torsoImg, [120, 770, 1120, 1345], [650, 830], [650, 1240]),
  armL: part(armLImg, [55, 920, 360, 1320], [300, 960]),
  armR: part(armRImg, [853, 691, 1291, 1022], [960, 930]),
  head: part(headClean, [40, 10, 1230, 895], [650, 830]),
  earL: part(earLImg, [15, 180, 330, 770], [300, 330]),
  earR: part(earRImg, [930, 150, 1100, 620], [980, 300]),
};

// Native (650,1472) origin; hips at native (650,1300).
const HIPS: [number, number] = [0, 172];
const WAIST: [number, number] = [0, 232];
const NECK: [number, number] = [0, 642];

// Facial feature geometry, head-local = native point minus neck pivot.
const headLocal = (native: [number, number]): [number, number] => [
  native[0] - 650,
  830 - native[1],
];
const EYE_L: {c: [number, number]; rx: number; ry: number} = {
  c: headLocal([441, 434]), rx: 101, ry: 92,
};
const EYE_R: {c: [number, number]; rx: number; ry: number} = {
  c: headLocal([772, 405]), rx: 95, ry: 87,
};
// Measured dark-disc centroids in the rendered baked artwork (ground truth).
const PUPIL_L = headLocal([513, 441]);
const PUPIL_R = headLocal([840, 411]);
const PUPIL_RADIUS = 17;
const MOUTH_C = headLocal([608, 717]);

const FUR = '#f7f6f2';
const OUTLINE = '#14110f';
const TONGUE = '#d7777f';

function Eye({
  center,
  rx,
  ry,
  pupilRest,
  blink,
  gaze,
}: {
  center: [number, number];
  rx: number;
  ry: number;
  pupilRest: [number, number];
  blink: SignalValue<number>;
  gaze: () => PossibleVector2;
}) {
  return (
    <Node x={center[0]} y={center[1]}>
      {/* Pupil: black disc matching the reference, clamped to the eye. */}
      <Node
        position={() => {
          const g = new Vector2(gaze());
          const maxX = rx - PUPIL_RADIUS - 22;
          const maxY = ry - PUPIL_RADIUS - 18;
          return [
            Math.max(-maxX, Math.min(maxX, g.x)),
            Math.max(-maxY, Math.min(maxY, g.y)),
          ];
        }}
      >
        <Circle
          width={PUPIL_RADIUS * 2}
          height={PUPIL_RADIUS * 2}
          x={pupilRest[0] - center[0]}
          y={pupilRest[1] - center[1]}
          fill={OUTLINE}
          opacity={() => 1 - (blink as number)}
        />
      </Node>
      {/* Fur-coloured eyelid grows down from the top of the eye. */}
      <Node
        scale={() => [1, blink as number]}
        y={() => ry * (1 - (blink as number))}
      >
        <Circle width={rx * 2} height={ry * 2} fill={FUR} />
      </Node>
      <Node opacity={() => ((blink as number) > 0.45 ? 1 : 0)}>
        <Line
          points={[
            [-rx + 12, 0],
            [0, 6],
            [rx - 12, 0],
          ]}
          stroke={OUTLINE}
          lineWidth={9}
          radius={6}
        />
      </Node>
    </Node>
  );
}

function Mouth({shape, open}: {shape: SignalValue<MouthShape>; open: SignalValue<number>}) {
  const c = MOUTH_C;
  return (
    <Node x={c[0]} y={c[1]}>
      {/* smile / small: curved black stroke */}
      <Node opacity={() => ((shape as MouthShape) === 'smile' || (shape as MouthShape) === 'small' ? 1 : 0)}>
        <Line
          points={() =>
            (shape as MouthShape) === 'small'
              ? [[-34, 4], [0, 10], [34, 4]]
              : [[-58, -18], [-16, 30], [40, 24], [62, -8]]
          }
          stroke={OUTLINE}
          lineWidth={11}
          radius={8}
        />
      </Node>
      {/* flat: short neutral line (freeze beat) */}
      <Node opacity={() => ((shape as MouthShape) === 'flat' ? 1 : 0)}>
        <Line points={[[-40, 6], [40, 6]]} stroke={OUTLINE} lineWidth={10} radius={5} />
      </Node>
      {/* open: black interior + tongue */}
      <Node
        opacity={() =>
          (shape as MouthShape) === 'open' ? (open as number) : 0
        }
        scale={() => [1, (open as number) * 0.7 + 0.3]}
      >
        <Circle width={96} height={116} fill={OUTLINE} y={4} />
        <Circle width={62} height={40} fill={TONGUE} y={34} />
      </Node>
      {/* oh: surprised round mouth */}
      <Node
        opacity={() => ((shape as MouthShape) === 'oh' ? 1 : 0)}
        scale={() => 0.6 + 0.4 * (open as number)}
      >
        <Circle width={72} height={82} fill={OUTLINE} />
        <Circle width={34} height={22} fill={TONGUE} y={20} />
      </Node>
    </Node>
  );
}

export function EllyRig({pose, children}: {pose: EllyPose; children?: unknown}) {
  return (
    // The rig is authored y-up; Motion Canvas is y-down, so the root flips y.
    // Part textures carry their own scale[1,-1] and stay upright under it.
    <Node
      x={pose.rootX}
      y={pose.rootY}
      scale={() => [pose.rootScale as number, -(pose.rootScale as number)]}
      rotation={pose.rootRotation}
    >
      <Node x={HIPS[0]} y={HIPS[1]}>
        {/* back-most bits */}
        <Node x={G.tail.pivot[0] - HIPS[0]} y={G.tail.pivot[1] - HIPS[1]} rotation={pose.tail}>
          <Img src={tailImg} width={G.tail.geom.size[0]} height={G.tail.geom.size[1]}
            x={G.tail.geom.imgOffset[0]} y={G.tail.geom.imgOffset[1]} scale={[1, -1]} />
        </Node>

        <Node x={G.legR.pivot[0] - HIPS[0]} y={G.legR.pivot[1] - HIPS[1]} rotation={pose.legR}>
          <Node scale={() => [1, pose.legFlexR as number]}>
            <Img src={legRImg} width={G.legR.geom.size[0]} height={G.legR.geom.size[1]}
              x={G.legR.geom.imgOffset[0]} y={G.legR.geom.imgOffset[1]} scale={[1, -1]} />
          </Node>
        </Node>
        <Node x={G.legL.pivot[0] - HIPS[0]} y={G.legL.pivot[1] - HIPS[1]} rotation={pose.legL}>
          <Node scale={() => [1, pose.legFlexL as number]}>
            <Img src={legLImg} width={G.legL.geom.size[0]} height={G.legL.geom.size[1]}
              x={G.legL.geom.imgOffset[0]} y={G.legL.geom.imgOffset[1]} scale={[1, -1]} />
          </Node>
        </Node>

        {/* spine: torso + arms + neck all inherit the waist bend */}
        <Node x={WAIST[0] - HIPS[0]} y={WAIST[1] - HIPS[1]} rotation={pose.spine}>
          <Node x={G.torso.pivot[0] - WAIST[0]} y={G.torso.pivot[1] - WAIST[1]}>
            <Img src={torsoImg} width={G.torso.geom.size[0]} height={G.torso.geom.size[1]}
              x={G.torso.geom.imgOffset[0]} y={G.torso.geom.imgOffset[1]} scale={[1, -1]} />
          </Node>

          <Node x={G.armL.pivot[0] - WAIST[0]} y={G.armL.pivot[1] - WAIST[1]} rotation={pose.armL}>
            <Img src={armLImg} width={G.armL.geom.size[0]} height={G.armL.geom.size[1]}
              x={G.armL.geom.imgOffset[0]} y={G.armL.geom.imgOffset[1]} scale={[1, -1]} />
          </Node>
          <Node x={G.armR.pivot[0] - WAIST[0]} y={G.armR.pivot[1] - WAIST[1]}
            rotation={pose.armR} scale={pose.armScale}>
            <Img src={armRImg} width={G.armR.geom.size[0]} height={G.armR.geom.size[1]}
              x={G.armR.geom.imgOffset[0]} y={G.armR.geom.imgOffset[1]} scale={[1, -1]} />
          </Node>

          <Node x={NECK[0] - WAIST[0]} y={NECK[1] - WAIST[1]} rotation={pose.head}>
            <Node x={G.earL.pivot[0] - NECK[0]} y={G.earL.pivot[1] - NECK[1]} rotation={pose.earL}>
              <Img src={earLImg} width={G.earL.geom.size[0]} height={G.earL.geom.size[1]}
                x={G.earL.geom.imgOffset[0]} y={G.earL.geom.imgOffset[1]} scale={[1, -1]} />
            </Node>
            <Node x={G.earR.pivot[0] - NECK[0]} y={G.earR.pivot[1] - NECK[1]} rotation={pose.earR}>
              <Img src={earRImg} width={G.earR.geom.size[0]} height={G.earR.geom.size[1]}
                x={G.earR.geom.imgOffset[0]} y={G.earR.geom.imgOffset[1]} scale={[1, -1]} />
            </Node>

            <Node x={G.head.pivot[0] - NECK[0]} y={G.head.pivot[1] - NECK[1]}>
              <Img src={headClean} width={G.head.geom.size[0]} height={G.head.geom.size[1]}
                x={G.head.geom.imgOffset[0]} y={G.head.geom.imgOffset[1]} scale={[1, -1]} />
            </Node>

            {/* Baked brows are covered by fur patches (head_clean still has
                them); the covers extend past the redrawn brows to hide every
                baked stroke. Baked pupils were erased in the artwork itself. */}
            <Line
              points={[[-312, 534], [-235, 560], [-138, 582]]}
              stroke={FUR} lineWidth={34} radius={6}
            />
            <Line
              points={[[82, 598], [150, 588], [214, 572]]}
              stroke={FUR} lineWidth={34} radius={6}
            />

            {/* Facial rig: eyes, brows, mouth, all head-local. */}
            <Node y={() => -14 * (pose.browLift as number)}>
              <Line // left eyebrow
                points={[[-295, 540], [-235, 560], [-175, 575]]}
                stroke={OUTLINE} lineWidth={10} radius={6}
                rotation={() => -8 * (pose.browLift as number)}
                y={() => -10 * (pose.browLift as number)}
              />
              <Line // right eyebrow
                points={[[95, 595], [150, 588], [200, 575]]}
                stroke={OUTLINE} lineWidth={10} radius={6}
                rotation={() => 8 * (pose.browLift as number)}
                y={() => -10 * (pose.browLift as number)}
              />
            </Node>
            <Eye center={EYE_L.c} rx={EYE_L.rx} ry={EYE_L.ry} pupilRest={PUPIL_L}
              blink={pose.blink} gaze={pose.gaze} />
            <Eye center={EYE_R.c} rx={EYE_R.rx} ry={EYE_R.ry} pupilRest={PUPIL_R}
              blink={pose.blink} gaze={pose.gaze} />
            <Mouth shape={pose.mouth} open={pose.mouthOpen} />
          </Node>
        </Node>
      </Node>
      {children as never}
    </Node>
  );
}
