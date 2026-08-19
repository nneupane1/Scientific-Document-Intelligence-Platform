import path from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDirectory, "..");
const assetDirectory = path.join(projectRoot, "apps/web/public/ai-assets");

const assets = [
  "structured-data-crystal-v2.png",
  "semantic-inspection-v2.png",
  "data-export-v2.png",
  "ai-observability-v2.png",
  "document-transformer-v2.png",
];

function isCanvasPixel(data, offset) {
  const red = data[offset];
  const green = data[offset + 1];
  const blue = data[offset + 2];
  const lightest = Math.max(red, green, blue);
  const darkest = Math.min(red, green, blue);
  return darkest >= 238 && lightest - darkest <= 16;
}

function matchesCheckerShade(data, width, x, y) {
  const offset = (y * width + x) * 3;
  const red = data[offset];
  const green = data[offset + 1];
  const blue = data[offset + 2];
  const expected = (Math.floor(x / 18) + Math.floor(y / 18)) % 2 === 0 ? 254 : 244;
  return (
    Math.max(red, green, blue) - Math.min(red, green, blue) <= 12
    && Math.abs(red - expected) <= 7
    && Math.abs(green - expected) <= 7
    && Math.abs(blue - expected) <= 7
  );
}

for (const filename of assets) {
  const inputPath = path.join(assetDirectory, filename);
  const outputPath = path.join(assetDirectory, filename.replace("-v2.png", "-transparent.png"));
  const { data, info } = await sharp(inputPath)
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const pixelCount = info.width * info.height;
  const removed = new Uint8Array(pixelCount);
  const queue = new Int32Array(pixelCount);
  let head = 0;
  let tail = 0;

  function enqueue(pixelIndex) {
    if (removed[pixelIndex] || !isCanvasPixel(data, pixelIndex * 3)) return;
    removed[pixelIndex] = 1;
    queue[tail] = pixelIndex;
    tail += 1;
  }

  for (let x = 0; x < info.width; x += 1) {
    enqueue(x);
    enqueue((info.height - 1) * info.width + x);
  }
  for (let y = 1; y < info.height - 1; y += 1) {
    enqueue(y * info.width);
    enqueue(y * info.width + info.width - 1);
  }

  while (head < tail) {
    const pixelIndex = queue[head];
    head += 1;
    const x = pixelIndex % info.width;
    const y = Math.floor(pixelIndex / info.width);
    if (x > 0) enqueue(pixelIndex - 1);
    if (x + 1 < info.width) enqueue(pixelIndex + 1);
    if (y > 0) enqueue(pixelIndex - info.width);
    if (y + 1 < info.height) enqueue(pixelIndex + info.width);
  }

  // Checkerboard areas can be enclosed by orbit wires, glass rims, and routing
  // lines, so they are not always connected to the outer canvas. Seed those
  // enclosed regions only when their pixels follow the generator's alternating
  // 18px checker pattern. Uniform white document surfaces therefore remain.
  const checkerOffsets = [[-18, 0], [18, 0], [0, -18], [0, 18]];
  for (let y = 0; y < info.height; y += 1) {
    for (let x = 0; x < info.width; x += 1) {
      if (!matchesCheckerShade(data, info.width, x, y)) continue;
      let matchingNeighbours = 0;
      for (const [offsetX, offsetY] of checkerOffsets) {
        const neighbourX = x + offsetX;
        const neighbourY = y + offsetY;
        if (
          neighbourX >= 0 && neighbourX < info.width
          && neighbourY >= 0 && neighbourY < info.height
          && matchesCheckerShade(data, info.width, neighbourX, neighbourY)
        ) matchingNeighbours += 1;
      }
      if (matchingNeighbours >= 2) enqueue(y * info.width + x);
    }
  }

  while (head < tail) {
    const pixelIndex = queue[head];
    head += 1;
    const x = pixelIndex % info.width;
    const y = Math.floor(pixelIndex / info.width);
    if (x > 0) enqueue(pixelIndex - 1);
    if (x + 1 < info.width) enqueue(pixelIndex + 1);
    if (y > 0) enqueue(pixelIndex - info.width);
    if (y + 1 < info.height) enqueue(pixelIndex + info.width);
  }

  let removedCount = 0;
  for (let pixelIndex = 0; pixelIndex < pixelCount; pixelIndex += 1) {
    if (removed[pixelIndex]) removedCount += 1;
  }

  const output = Buffer.alloc(pixelCount * 4);
  for (let pixelIndex = 0; pixelIndex < pixelCount; pixelIndex += 1) {
    const sourceOffset = pixelIndex * 3;
    const outputOffset = pixelIndex * 4;
    output[outputOffset] = data[sourceOffset];
    output[outputOffset + 1] = data[sourceOffset + 1];
    output[outputOffset + 2] = data[sourceOffset + 2];
    output[outputOffset + 3] = removed[pixelIndex] ? 0 : 255;
  }

  await sharp(output, { raw: { width: info.width, height: info.height, channels: 4 } })
    .png({ compressionLevel: 9, palette: false })
    .toFile(outputPath);

  console.log(`${path.basename(outputPath)}: removed ${removedCount.toLocaleString()} canvas pixels`);
}
