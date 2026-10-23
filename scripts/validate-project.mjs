/**
 * validate-project.mjs — feeds the generated project through StykAnimate's own
 * loader pipeline (native container decode + full scene validation).
 *
 * STYK_ANIMATE_HOME points at a checkout of the StykAnimate-App repository.
 */

import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const APP = process.env.STYK_ANIMATE_HOME || join(ROOT, '../stykanimate');

const {decodeDocument, normalizeDecodedDocument} = await import(join(APP, 'src/native-container.mjs'));
const {validateSceneSteps} = await import(join(APP, 'src/pivot/model.mjs'));

const bytes = readFileSync(join(ROOT, 'animation/dog-walk-sit-stand.styk'));
const decoded = await decodeDocument(new Uint8Array(bytes), 'styk');
const document_ = normalizeDecodedDocument(decoded.document, 'styk');
console.log(`decode OK: container v${decoded.version}, ${document_.keyframes.length} frames, ${document_.figure_types.length} figures`);

for (const step of validateSceneSteps(document_, {sliceMs: 1000})) {
  if (step?.phase) process.stdout.write(`\rvalidating ${step.phase}...`);
}
console.log('\nscene validation OK');

// Angle-array length sanity for every object in every frame
for (const [fi, frame] of document_.keyframes.entries()) {
  for (const obj of frame.objects) {
    const fig = document_.figure_types.find(f => f.figure_type_id === obj.figure_type_id);
    if (obj.angles.length !== fig.segments.length) {
      throw new Error(`frame ${fi} object ${obj.unique_id}: ${obj.angles.length} angles vs ${fig.segments.length} segments`);
    }
  }
}
console.log('pose arrays match figure definitions on every frame');
