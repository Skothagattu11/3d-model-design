/**
 * add_holo.js — Inject KHR_materials_iridescence into a badge GLB.
 *
 * Adds a view-angle-reactive holographic rainbow sheen to the disc face
 * of the badge. The effect shifts colour as you rotate the model in any
 * WebGL viewer (donmccurdy gltf-viewer, Babylon.js Sandbox, Three.js).
 *
 * Usage:
 *   node add_holo.js input.glb output_holo.glb
 *   node add_holo.js input.glb output_holo.glb --factor 0.95 --ior 2.0 --min 80 --max 600
 *
 * Parameters:
 *   --factor  0–1    iridescence intensity          (default 0.88)
 *   --ior     1–2.5  thin-film refraction index      (default 1.8, higher = stronger shift)
 *   --min     nm     film thickness thin end         (default 100)
 *   --max     nm     film thickness thick end        (default 500)
 */

import { NodeIO } from '@gltf-transform/core';
import { KHRMaterialsIridescence, ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { readFileSync, statSync } from 'fs';

// ── CLI args ─────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
if (args.length < 2 || args[0].startsWith('--')) {
  console.error('Usage: node add_holo.js <input.glb> <output_holo.glb> [options]');
  process.exit(1);
}

const inputPath  = args[0];
const outputPath = args[1];

function getArg(flag, fallback) {
  const i = args.indexOf(flag);
  return i !== -1 ? parseFloat(args[i + 1]) : fallback;
}

const factor    = getArg('--factor', 0.88);
const ior       = getArg('--ior',    1.80);
const thickMin  = getArg('--min',   100);
const thickMax  = getArg('--max',   500);

// ── Transform ────────────────────────────────────────────────────────────────
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);

console.log(`Reading  : ${inputPath}`);
const doc = await io.read(inputPath);

const iridescenceExt = doc.createExtension(KHRMaterialsIridescence);
let applied = 0;

for (const mat of doc.getRoot().listMaterials()) {
  // Only apply to materials that have a base-colour texture (the disc face).
  // Side walls and back plate use vertex colours — skip them.
  if (!mat.getBaseColorTexture()) continue;

  const iridescence = iridescenceExt
    .createIridescence()
    .setIridescenceFactor(factor)
    .setIridescenceIOR(ior)
    .setIridescenceThicknessMinimum(thickMin)
    .setIridescenceThicknessMaximum(thickMax);

  mat.setExtension('KHR_materials_iridescence', iridescence);

  // Boost metallic + lower roughness so the sheen reads against the texture
  mat.setMetallicFactor(Math.min(1.0, mat.getMetallicFactor() + 0.20));
  mat.setRoughnessFactor(Math.max(0.05, mat.getRoughnessFactor() - 0.15));

  applied++;
}

console.log(`Applied  : iridescence to ${applied} material(s)`);
console.log(`  factor=${factor}  IOR=${ior}  thickness=${thickMin}–${thickMax}nm`);

await io.write(outputPath, doc);

const kb = statSync(outputPath).size / 1024;
console.log(`Saved    : ${outputPath}  (${kb.toFixed(1)} KB)`);
console.log();
console.log('Preview  : https://gltf-viewer.donmccurdy.com  (drag & drop the GLB)');
