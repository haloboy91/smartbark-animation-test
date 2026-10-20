import {defineConfig} from 'vite';
import motionCanvas from '@motion-canvas/vite-plugin';
import ffmpeg from '@motion-canvas/ffmpeg';

// The ffmpeg() plugin lets the Motion Canvas editor export MP4/WebM
// directly in the browser using a bundled, npm-installed ffmpeg binary.
export default defineConfig({
  plugins: [motionCanvas(), ffmpeg()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
});
