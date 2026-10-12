// Builds the unpacked extension into dist/: TypeScript via tsc (no native bundler), static pages copied, the
// livekit-client ES module copied next to the Media Session Page, and the EMS origin written into the manifest.
//   EMS_ORIGIN=https://app.ems.example npm run build      (default http://localhost:3000)
import { execFileSync } from "node:child_process";
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";

const root = dirname(fileURLToPath(import.meta.url));
const dist = join(root, "dist");
const origin = (process.env.EMS_ORIGIN ?? "http://localhost:3000").replace(/\/$/, "");
if (!/^https?:\/\/[^/]+$/.test(origin)) throw new Error(`EMS_ORIGIN must be an origin like https://app.example.com, got ${origin}`);

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });

// 1. TypeScript -> dist (one file per module; pages load them as ES modules)
execFileSync(process.execPath, [join(root, "node_modules", "typescript", "bin", "tsc"), "-p", join(root, "tsconfig.json")], { stdio: "inherit" });

// 2. Static files (HTML, CSS) keep their folder layout
const copyStatic = (from, to) => {
  for (const entry of readdirSync(from, { withFileTypes: true })) {
    const src = join(from, entry.name);
    const dst = join(to, entry.name);
    if (entry.isDirectory()) {
      mkdirSync(dst, { recursive: true });
      copyStatic(src, dst);
    } else if (/\.(html|css)$/.test(entry.name)) {
      cpSync(src, dst);
    }
  }
};
copyStatic(join(root, "src"), dist);

// 3. LiveKit client for the Media Session Page; the compiled import of "livekit-client" points at the local copy.
cpSync(join(root, "node_modules", "livekit-client", "dist", "livekit-client.esm.mjs"), join(dist, "media", "livekit-client.esm.mjs"));
const mediaJs = join(dist, "media", "media.js");
writeFileSync(mediaJs, readFileSync(mediaJs, "utf8").replace(/from\s+["']livekit-client["']/g, 'from "./livekit-client.esm.mjs"'));

// 4. Origin: manifest host permission and the runtime config
writeFileSync(join(dist, "manifest.json"), readFileSync(join(root, "manifest.template.json"), "utf8").replaceAll("__EMS_ORIGIN__", origin));
const configJs = join(dist, "config.js");
writeFileSync(configJs, readFileSync(configJs, "utf8").replace("__EMS_ORIGIN__", origin));

// 5. Icons: solid brand-colour PNGs generated here, so the repo holds no binary files.
function png(size) {
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc = (buf) => {
    let c = 0xffffffff;
    for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const c = Buffer.alloc(4);
    c.writeUInt32BE(crc(td));
    return Buffer.concat([len, td, c]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  const raw = Buffer.alloc((size * 4 + 1) * size);
  const r = size / 2;
  for (let y = 0; y < size; y++) {
    raw[y * (size * 4 + 1)] = 0;
    for (let x = 0; x < size; x++) {
      const inside = (x - r + 0.5) ** 2 + (y - r + 0.5) ** 2 <= r * r;
      const o = y * (size * 4 + 1) + 1 + x * 4;
      raw[o] = 0x4f; raw[o + 1] = 0x5b; raw[o + 2] = 0xd5; raw[o + 3] = inside ? 255 : 0;
    }
  }
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}
mkdirSync(join(dist, "icons"), { recursive: true });
for (const s of [16, 48, 128]) writeFileSync(join(dist, "icons", `icon${s}.png`), png(s));

for (const f of ["manifest.json", "background.js", "popup/popup.html", "popup/popup.js", "media/media.html", "media/media.js", "settings/settings.html"]) {
  if (!existsSync(join(dist, f))) throw new Error(`build output missing: ${f}`);
}
console.log(`EMS extension built for ${origin} -> ${dist}`);
