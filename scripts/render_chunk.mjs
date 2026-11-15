import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const idx = a.indexOf('=');
    if (idx === -1) return [a.replace(/^--/, ''), 'true'];
    return [a.slice(0, idx).replace(/^--/, ''), a.slice(idx + 1)];
  })
);

const timelinePath = args.timeline ?? 'out/compiled_timeline.json';
const shard = Number(args.shard ?? 0);
const totalShards = Number(args['total-shards'] ?? 4);
const outFile = args.out ?? `out/chunk_${shard}.mp4`;

const timeline = JSON.parse(fs.readFileSync(timelinePath, 'utf-8'));
const fps = Number(args.fps ?? timeline.fps ?? 60);
const duration = Number(
  timeline.totalDuration ??
  timeline.scenes?.reduce((acc, sc) => acc + (Number(sc.duration) || 5), 0) ??
  60
);

const totalFrames = Math.max(1, Math.round(fps * duration));
const framesPerShard = Math.ceil(totalFrames / totalShards);
const startFrame = shard * framesPerShard;
const endFrame = Math.min(totalFrames, (shard + 1) * framesPerShard);

fs.mkdirSync(path.dirname(outFile), { recursive: true });
console.log(`[Shard ${shard}/${totalShards}] Frames ${startFrame}..${endFrame - 1} (Total ${totalFrames} frames @ ${fps}fps)`);

const browser = await chromium.launch({
  headless: true,
  args: ['--disable-dev-shm-usage', '--no-sandbox', '--enable-gpu-rasterization']
});

const page = await browser.newPage({
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1
});

const htmlUrl = 'file://' + path.resolve('index.html');
await page.goto(htmlUrl, { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
await page.evaluate((data) => window.loadScript(data), timeline);

const ffmpeg = spawn('ffmpeg', [
  '-y',
  '-f', 'image2pipe',
  '-vcodec', 'png',
  '-r', String(fps),
  '-i', '-',
  '-c:v', 'libx264',
  '-pix_fmt', 'yuv420p',
  '-preset', 'fast',
  '-crf', '18',
  outFile
], { stdio: ['pipe', 'inherit', 'inherit'] });

for (let f = startFrame; f < endFrame; f++) {
  const t = f / fps;
  await page.evaluate((sec) => window.renderFrameAt(sec), t);
  const pngBuffer = await page.screenshot({ type: 'png', omitBackground: false });
  if (!ffmpeg.stdin.write(pngBuffer)) {
    await new Promise((r) => ffmpeg.stdin.once('drain', r));
  }
  if ((f - startFrame) % 120 === 0) {
    console.log(`[Shard ${shard}] ${f - startFrame}/${endFrame - startFrame} frames done`);
  }
}

ffmpeg.stdin.end();
await new Promise((resolve, reject) => {
  ffmpeg.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`FFmpeg exit ${code}`))));
});

await browser.close();
console.log(`[Shard ${shard}] Completed -> ${outFile}`);
