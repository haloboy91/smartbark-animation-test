#!/usr/bin/env python3
"""Decompose the flat Elly cut-out into articulated body-part layers.

The supplied reference is a single flattened cartoon drawing, so true limb
interiors/backs do not exist. This script cuts the *exact* artwork into
overlapping puppet layers along seams hidden under natural body overlaps
(scarf, sweater hem, head fur). Every visible pixel is preserved; nothing is
redesigned, recolored, or redrawn.

Outputs (src/assets/rig/):
  earL.png, earR.png, head.png, torso.png, armL.png, armR.png,
  legL.png, legR.png, tail.png, head_clean.png (mouth area fur-patched),
  rig-manifest.json (crop boxes, pivots, facial feature coordinates)

Run:  python3 scripts/rig/build_rig.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImagePath

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src/assets/elly.png'
OUT = ROOT / 'src/assets/rig'

# --- native-image crop boxes (x0, y0, x1, y1) and joint pivots -------------
PARTS = {
    'earL':  {'box': (15, 180, 330, 770),    'pivot': (300, 330)},
    'earR':  {'box': (930, 150, 1100, 620),  'pivot': (980, 300)},
    'head':  {'box': (40, 10, 1230, 895),    'pivot': (650, 830)},
    'torso': {'box': (120, 770, 1120, 1345), 'pivot': (650, 830)},
    'armL':  {'box': (55, 920, 360, 1320),   'pivot': (300, 960)},
    'armR':  {'box': (890, 685, 1295, 1020), 'pivot': (960, 930)},
    'legL':  {'box': (250, 1285, 645, 1472), 'pivot': (430, 1300)},
    'legR':  {'box': (635, 1285, 1000, 1472),'pivot': (820, 1300)},
    'tail':  {'box': (945, 1220, 1130, 1390),'pivot': (975, 1300)},
}

# Back-to-front draw order AND pixel-claim priority. Each artwork pixel is
# owned by exactly one layer: back layers claim first, front layers claim the
# overlap. At the rest pose the layers rebuild the original pixel-for-pixel.
Z_ORDER = ['armR', 'earL', 'earR', 'tail', 'legL', 'legR', 'torso', 'armL', 'head']

# The raised right arm + hand crosses the huge head box, so a rectangle cannot
# separate the cream hand from the near-identical cream face fur. Its visible
# silhouette is traced as a polygon (seam runs along the sleeve/cuff outline);
# it gets first claim, which is correct because the arm is in front of the
# torso/scarf and its polygon never includes head-fur pixels.
ARMR_POLYGON = [
    (895, 1000), (880, 900), (875, 830), (895, 775), (1000, 735),
    (1035, 720), (1045, 700), (1120, 690), (1230, 685), (1278, 700),
    (1278, 745), (1265, 800), (1245, 858), (1235, 878), (1130, 905),
    (1075, 905),
    (1010, 895), (1060, 940), (1000, 985),
]

# Facial features measured in native coordinates (see repo docs/RIG_NOTES.md).
FEATURES = {
    'eyeL_white': {'center': (441, 434), 'rx': 101, 'ry': 92},
    'eyeR_white': {'center': (772, 405), 'rx': 95, 'ry': 87},
    'pupilL_rest': (488, 447),
    'pupilR_rest': (843, 400),
    'pupil_radius': 17,
    'nose_box': (620, 462, 780, 588),
}
FUR = (247, 246, 242, 255)
NECK = (650, 830)


def rect_mask(shape, box):
    m = np.zeros(shape, dtype=bool)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = True
    return m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC).convert('RGBA')
    arr = np.array(src)
    h, w = arr.shape[:2]
    alpha = arr[:, :, 3] > 8
    rgb = arr[:, :, :3].astype(int)

    manifest = {'source': 'src/assets/elly.png', 'image_size': [w, h],
                'neck_pivot': list(NECK), 'parts': {}, 'features': FEATURES}
    layer_images = {}
    claimed = np.zeros((h, w), dtype=bool)
    ownership = {}

    # Traced polygon mask for the raised hand/cuff (front priority). A small
    # dilation absorbs anti-aliased edges; the navy cuff separates the hand
    # from the face fur, so the dilation cannot reach head pixels.
    poly_mask_img = Image.new('L', (w, h), 0)
    ImageDraw.Draw(poly_mask_img).polygon(ARMR_POLYGON, fill=255)
    poly_mask_img = poly_mask_img.filter(ImageFilter.MaxFilter(13))
    poly_mask = np.array(poly_mask_img).astype(bool)

    # Sleeve portion: the arm rectangle below/outside the head box, restricted
    # to arm materials so the pink scarf can never be stolen into the arm
    # layer. Gold stars printed on the sleeve stay with the arm on purpose.
    arm_rect = rect_mask((h, w), (855, 685, 1295, 1020))
    head_rect = rect_mask((h, w), PARTS['head']['box'])
    pink = (rgb[:, :, 0] > 140) & (rgb[:, :, 0] > rgb[:, :, 1] + 25) & \
        (rgb[:, :, 0] > rgb[:, :, 2] + 15)
    sleeve_mask = arm_rect & ~head_rect & ~pink
    # Pink is excluded everywhere: the raised arm has no pink parts, so any
    # pink pixel reached by the dilated polygon is scarf, never arm.
    armr_mask = (poly_mask | sleeve_mask) & alpha & ~pink

    # The crop box must cover every owned pixel (dilation can extend the mask
    # beyond the traced polygon), so derive it from the final mask.
    ays, axs = np.where(armr_mask)
    armr_box = (int(max(axs.min() - 2, 0)), int(max(ays.min() - 2, 0)),
                int(min(axs.max() + 3, w)), int(min(ays.max() + 3, h)))
    PARTS['armR'] = {
        'box': armr_box,
        'pivot': (960, 930),
        'polygon': ARMR_POLYGON,
    }

    # armR claims first: the polygon is the exact hand silhouette and the
    # sleeve mask only contains arm materials outside the head box.
    ownership['armR'] = armr_mask
    claimed |= ownership['armR']

    # Single-owner rectangle claim pass for every other part, back to front.
    for name in Z_ORDER:
        if name == 'armR':
            continue
        spec = PARTS[name]
        mask = rect_mask((h, w), spec['box']) & alpha & ~claimed
        ownership[name] = mask
        claimed |= mask

    orphan = alpha & ~claimed
    if orphan.any():
        ys, xs = np.where(orphan)
        raise RuntimeError(
            f'{len(xs)} artwork pixels are not covered by any part box; '
            f'bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]')

    for name, spec in PARTS.items():
        box = spec['box']
        m_img = Image.fromarray((ownership[name] * 255).astype(np.uint8), 'L')
        layer = src.copy()
        layer.putalpha(Image.composite(layer.getchannel('A'),
                                       Image.new('L', (w, h), 0), m_img))
        cropped = layer.crop(box)
        cropped.save(OUT / f'{name}.png')
        layer_images[name] = (cropped, box)
        px, py = spec['pivot']
        manifest['parts'][name] = {
            'box': list(box),
            'pivot_native': list(spec['pivot']),
            'pivot_local': [px - box[0], py - box[1]],
        }

    # head_clean: remove ONLY the flattened smile expression and inpaint
    # plain muzzle fur, so runtime mouth shapes can replace it without
    # redesigning the face. Dark/pink pixels split into connected components:
    # the largest is the mouth (interior + tongue + smile arcs); the smaller
    # ones are chin/muzzle fur outlines that must stay untouched.
    px0, py0, px1, py1 = 520, 600, 850, 830
    region_rgb = np.array(src.crop((px0, py0, px1, py1)).convert('RGB')).astype(int)
    dark = region_rgb.sum(axis=-1) < 200
    pink = (region_rgb[:, :, 0] > 150) & \
        (region_rgb[:, :, 0] > region_rgb[:, :, 1] + 25)
    seed_mask = dark | pink
    labels = np.zeros(seed_mask.shape, dtype=np.int32)
    next_label, sizes = 1, {}
    for ry, rx in np.argwhere(seed_mask):
        if labels[ry, rx]:
            continue
        stack = [(ry, rx)]
        labels[ry, rx] = next_label
        count = 0
        while stack:
            y, x = stack.pop()
            count += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < labels.shape[0] and 0 <= nx < labels.shape[1] \
                            and seed_mask[ny, nx] and not labels[ny, nx]:
                        labels[ny, nx] = next_label
                        stack.append((ny, nx))
        sizes[next_label] = count
        next_label += 1
    mouth_label = max(sizes, key=sizes.get)
    mouth_strokes = labels == mouth_label
    # Tight dilation encloses anti-aliased edges without reaching the chin
    # outline components, which are explicitly removed from the fill mask.
    fill_mask = np.array(
        Image.fromarray((mouth_strokes * 255).astype(np.uint8), 'L')
        .filter(ImageFilter.MaxFilter(15))
    ).astype(bool)
    # Overwrite the mouth itself plus its dilation ring, but never the other
    # (chin/muzzle outline) components.
    fill_mask &= (labels == 0) | (labels == mouth_label)
    mx_ = region_rgb.max(axis=-1)
    mn_ = region_rgb.min(axis=-1)
    fur_like = (mn_ > 215) & ((mx_ - mn_) < 30) & ~pink
    fur_median = np.median(region_rgb[fur_like & ~fill_mask], axis=0)
    filled = region_rgb.astype(np.float32).copy()
    filled[~fill_mask & ~fur_like] = fur_median
    filled[fill_mask] = fur_median
    for _ in range(160):
        padded = np.pad(filled, ((1, 1), (1, 1), (0, 0)), mode='edge')
        neigh = (
            padded[:-2, 1:-1] + padded[2:, 1:-1] +
            padded[1:-1, :-2] + padded[1:-1, 2:]
        ) / 4.0
        filled[fill_mask] = neigh[fill_mask]
    filled = np.clip(filled, 0, 255).astype(np.uint8)
    patch_alpha = Image.fromarray((fill_mask * 255).astype(np.uint8), 'L') \
        .filter(ImageFilter.GaussianBlur(0.8))
    patch_img = Image.fromarray(
        np.dstack([filled, np.array(patch_alpha)]), 'RGBA')
    head_clean = src.copy()
    head_clean.alpha_composite(patch_img, (px0, py0))

    # Erase the two baked pupil discs too, so the runtime facial rig owns the
    # pupils (gaze + blink) and a shifted pupil can never reveal a baked one.
    # Centers are the measured dark-disc centroids of the flattened artwork;
    # r=20 stays well inside both eye-white ellipses.
    pupil_layer = Image.new('RGBA', (40, 40), (0, 0, 0, 0))
    ImageDraw.Draw(pupil_layer).ellipse(
        (0, 0, 40, 40), fill=(253, 253, 253, 255))
    pupil_layer = pupil_layer.filter(ImageFilter.GaussianBlur(1.2))
    for nx, ny in ((513, 441), (840, 411)):
        head_clean.alpha_composite(pupil_layer, (nx - 20, ny - 20))
    head_clean.crop(PARTS['head']['box']).save(OUT / 'head_clean.png')
    mys, mxs = np.where(mouth_strokes)
    FEATURES['mouth'] = {
        'center': [int(mxs.mean() + px0), int(mys.mean() + py0)],
        'box': [int(mxs.min() + px0), int(mys.min() + py0),
                int(mxs.max() + px0), int(mys.max() + py0)],
    }

    # ---- recomposition check: layers must rebuild the original artwork ----
    recomp = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for name in Z_ORDER:
        cropped, box = layer_images[name]
        recomp.alpha_composite(cropped, (box[0], box[1]))
    diff = np.abs(np.array(recomp).astype(int) - arr.astype(int))
    changed = (diff.sum(axis=-1) > 24) & alpha
    ys, xs = np.where(changed)
    if len(xs):
        print(f'WARNING: {len(xs)} pixels differ after recomposition; '
              f'bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]')
    else:
        print('Recomposition matches original artwork exactly.')
    recomp.save('/tmp/rig_recomposition.png')

    with open(OUT / 'rig-manifest.json', 'w') as fh:
        json.dump(manifest, fh, indent=2)
    print(f'Wrote {len(PARTS)} layers + head_clean + manifest to {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
