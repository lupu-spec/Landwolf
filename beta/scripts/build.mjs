import { build } from "esbuild";
import { copyFile, cp, mkdir } from "node:fs/promises";
const output = "landwolf/static";
await mkdir(`${output}/assets`, { recursive: true });
await build({
  entryPoints: ["web/app.ts"],
  bundle: true,
  format: "esm",
  target: "es2022",
  outfile: `${output}/assets/app.js`,
  minify: true,
});
await copyFile("web/index.html", `${output}/index.html`);
await copyFile("web/styles.css", `${output}/assets/styles.css`);
await copyFile("web/favicon.svg", `${output}/favicon.svg`);
await copyFile(
  "node_modules/leaflet/dist/leaflet.css",
  `${output}/assets/leaflet.css`,
);
await cp("web/assets", `${output}/assets`, { recursive: true });
console.log("LandWolf browser bundle built");
