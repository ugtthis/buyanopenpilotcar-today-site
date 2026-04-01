import { resolve, relative } from "path";

const ROOT = import.meta.dir;

const INCLUDE_EXTENSIONS = new Set([
  ".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".py",
]);

const EXCLUDE_DIRS = new Set([
  "node_modules", "dist", "build", ".git",
  ".cache", ".output", ".turbo", ".parcel-cache",
  "venv", ".venv", "__pycache__", ".pytest_cache",
]);

const glob = new Bun.Glob("**/*");

const results: { file: string; lines: number }[] = [];

for await (const entry of glob.scan({ cwd: ROOT, onlyFiles: true })) {
  const parts = entry.split("/");
  if (parts.some((p) => EXCLUDE_DIRS.has(p))) continue;

  const ext = entry.slice(entry.lastIndexOf("."));
  if (!INCLUDE_EXTENSIONS.has(ext)) continue;

  const abs = resolve(ROOT, entry);
  const text = await Bun.file(abs).text();
  const lines = text.split("\n").length;

  results.push({ file: relative(ROOT, abs), lines });
}

results.sort((a, b) => b.lines - a.lines);

const totalLines = results.reduce((sum, r) => sum + r.lines, 0);
const maxFileLen = Math.max(...results.map((r) => r.file.length), 4);
const lineColWidth = Math.max(String(totalLines).length, 5);

const separator = `${"-".repeat(lineColWidth + 2)}-+-${"-".repeat(maxFileLen)}`;

console.log("\n");
console.log(`${"Lines".padStart(lineColWidth + 2)} | File`);
console.log(separator);

for (const { file, lines } of results) {
  console.log(`${String(lines).padStart(lineColWidth + 2)} | ${file}`);
}

console.log(separator);
console.log(
  `${String(totalLines).padStart(lineColWidth + 2)} | Total (${results.length} files)`
);
console.log("\n");
