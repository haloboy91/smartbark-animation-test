import {makeProject} from '@motion-canvas/core';

import coinScene from './scenes/coin.scene?scene';

import './global.css';

export default makeProject({
  name: 'Smart Bark — Elly articulated rig POC',
  scenes: [coinScene],
  // Resolution, frame rate, background color and the FFmpeg exporter are
  // configured in ./project.meta (the editor's Video Settings tab writes
  // back to the same file).
});
