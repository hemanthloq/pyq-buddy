// One-off build-time generator: converts each of the app's fixed loading
// phrases into real SVG path data traced from an actual handwriting font
// (Caveat), so the chalk-writing animation can reveal genuine letterform
// strokes via stroke-dasharray/dashoffset instead of an arbitrary runtime
// text-to-path approximation. The phrase list is fixed and small (see
// ChalkLoader call sites), so this only needs to run once whenever a phrase
// is added/changed - not per request, not in the browser.
//
// The font binary itself is neither committed nor shipped: it's only a
// build-time input (never loaded by the app - the runtime imports the
// generated path data below, not a font file), so it's fetched on demand
// into a gitignored cache instead. HF Spaces' git server rejects committed
// binaries outright (recommends LFS/Xet), and there's no reason to carry
// this one in history when the only durable output that matters is the
// generated path data.
//
// Run with: node scripts/generate-chalk-paths.mjs
// Output:   src/chalkPaths.generated.js (committed, imported at runtime)

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import opentype from 'opentype.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FONT_URL = 'https://github.com/google/fonts/raw/main/ofl/caveat/Caveat%5Bwght%5D.ttf';
const FONT_CACHE_PATH = path.join(__dirname, 'fonts', 'Caveat.ttf'); // gitignored - see frontend/.gitignore
const OUTPUT_PATH = path.join(__dirname, '..', 'src', 'chalkPaths.generated.js');
const FONT_SIZE = 64; // arbitrary generation-time resolution; SVG viewBox scaling makes the display size independent of this
const DECIMALS = 0; // integer path coords: at this font size the rounding error is ~1% of letter height, invisible on a hand-drawn/wobbly typeface, and it roughly halves the committed data size
const PADDING = 4; // a little breathing room around the traced glyphs so stroke width / chalk icon radius don't clip at the viewBox edge

// Every phrase ChalkLoader is ever asked to render, across both call sites
// (search-loading and extraction-loading). Keep in sync with
// SearchScreen.jsx's SEARCH_LOADING_PHRASES and UploadScreen.jsx's
// EXTRACTION_LOADING_PHRASES - this script doesn't import those (they're
// JSX, not plain data modules) so this list is maintained by hand.
const PHRASES = [
  // Search-loading (SearchScreen.jsx)
  'Chalking up an answer…',
  'Digging through old papers…',
  'Sharpening our pencils…',
  'Consulting the syllabus…',
  'Flipping through past papers…',
  'Erasing the wrong turns…',
  // Extraction-loading (UploadScreen.jsx)
  'Flipping through the pages…',
  'Circling every question…',
  'Counting up the marks…',
  'Sorting into piles…',
  'Reading between the lines…',
  'Cross-checking the total…',
];

async function getFontBuffer() {
  if (existsSync(FONT_CACHE_PATH)) {
    return readFileSync(FONT_CACHE_PATH);
  }

  console.log(`Fetching ${FONT_URL} ...`);
  const response = await fetch(FONT_URL);
  if (!response.ok) {
    throw new Error(`Failed to download Caveat font: HTTP ${response.status}`);
  }
  const buffer = Buffer.from(await response.arrayBuffer());

  mkdirSync(path.dirname(FONT_CACHE_PATH), { recursive: true });
  writeFileSync(FONT_CACHE_PATH, buffer); // local cache only - gitignored, re-fetched on a clean checkout
  return buffer;
}

const fontBuffer = await getFontBuffer();
const arrayBuffer = fontBuffer.buffer.slice(
  fontBuffer.byteOffset,
  fontBuffer.byteOffset + fontBuffer.byteLength
);
const font = opentype.parse(arrayBuffer);

// Hand-rolled serializer instead of Path.toPathData(): opentype.js v2.0.0's
// own serializer omits the separator between two adjacent non-negative
// numbers in some cases (observed producing e.g. "13" then "0" concatenated
// into the single invalid token "130"), which silently truncates the path
// at render time - the browser stops parsing at the first bad token. Always
// space-separating every numeric token removes the ambiguity entirely, at
// the cost of a few extra bytes per coordinate.
function formatNum(v) {
  return DECIMALS > 0 ? v.toFixed(DECIMALS) : String(Math.round(v));
}

function commandsToPathData(commands) {
  const parts = [];
  for (const cmd of commands) {
    if (cmd.type === 'M' || cmd.type === 'L') {
      parts.push(cmd.type, formatNum(cmd.x), formatNum(cmd.y));
    } else if (cmd.type === 'C') {
      parts.push(
        cmd.type,
        formatNum(cmd.x1),
        formatNum(cmd.y1),
        formatNum(cmd.x2),
        formatNum(cmd.y2),
        formatNum(cmd.x),
        formatNum(cmd.y)
      );
    } else if (cmd.type === 'Q') {
      parts.push(cmd.type, formatNum(cmd.x1), formatNum(cmd.y1), formatNum(cmd.x), formatNum(cmd.y));
    } else if (cmd.type === 'Z') {
      parts.push('Z');
    }
  }
  return parts.join(' ');
}

const entries = PHRASES.map((phrase) => {
  const otPath = font.getPath(phrase, 0, 0, FONT_SIZE);
  const bbox = otPath.getBoundingBox();
  const d = commandsToPathData(otPath.commands);

  const x = bbox.x1 - PADDING;
  const y = bbox.y1 - PADDING;
  const width = bbox.x2 - bbox.x1 + PADDING * 2;
  const height = bbox.y2 - bbox.y1 + PADDING * 2;

  return {
    text: phrase,
    d,
    viewBox: `${x.toFixed(2)} ${y.toFixed(2)} ${width.toFixed(2)} ${height.toFixed(2)}`,
    // width/height kept alongside viewBox so callers can size the <svg> to
    // the phrase's actual aspect ratio without re-parsing the viewBox string
    width: Number(width.toFixed(2)),
    height: Number(height.toFixed(2)),
  };
});

const banner = `// GENERATED FILE - do not edit by hand.
// Produced by scripts/generate-chalk-paths.mjs from the Caveat handwriting
// font (fetched on demand, see FONT_URL in that script - not committed).
// Re-run that script if a loading phrase is added, removed, or changed.
`;

const body = `export const CHALK_PATHS = ${JSON.stringify(
  Object.fromEntries(entries.map((e) => [e.text, e])),
  null,
  2
)};
`;

writeFileSync(OUTPUT_PATH, banner + '\n' + body);
console.log(`Wrote ${entries.length} phrase paths to ${path.relative(process.cwd(), OUTPUT_PATH)}`);
