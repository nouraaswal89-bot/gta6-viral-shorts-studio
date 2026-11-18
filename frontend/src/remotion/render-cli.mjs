/**
 * Programmatic Remotion Renderer CLI invoked by the Python FastAPI backend.
 * Renders ViralShortComposition at 1080x1920 @ 60fps, H.264 High Profile, CRF 16, yuv420p.
 *
 * Usage:
 *   node src/remotion/render-cli.mjs --props path/to/props.json --output path/to/out.mp4
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--props" && argv[i + 1]) {
      args.props = argv[++i];
    } else if (argv[i] === "--output" && argv[i + 1]) {
      args.output = argv[++i];
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.props || !args.output) {
    console.error("Usage: node render-cli.mjs --props <json> --output <mp4>");
    process.exit(1);
  }

  const clip = JSON.parse(fs.readFileSync(args.props, "utf-8"));
  const inputProps = { clip };

  const entryPoint = path.resolve(__dirname, "index.ts");
  const bundleLocation = await bundle({
    entryPoint,
    webpackOverride: (config) => config,
  });

  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: "ViralShortComposition",
    inputProps,
  });

  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    pixelFormat: "yuv420p",
    crf: 16,
    x264Preset: "medium",
    outputLocation: path.resolve(args.output),
    inputProps,
    concurrency: Number(process.env.RENDER_CONCURRENCY || 2),
    chromiumOptions: {
      disableWebSecurity: true,
    },
  });

  console.log(`Rendered MP4 successfully: ${args.output}`);
}

main().catch((err) => {
  console.error("Remotion render failed:", err);
  process.exit(1);
});
