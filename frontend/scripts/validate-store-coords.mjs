import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rawJson   = JSON.parse(readFileSync(join(__dirname, "../../pipeline/data/openpilot_cars.json"), "utf-8"));
const coords    = JSON.parse(readFileSync(join(__dirname, "../src/store-coords.json"), "utf-8"));

const missingIds = new Set();

for (const entry of rawJson.entries) {
  for (const ay of entry.available_years) {
    if (ay.car && !coords[String(ay.car.storeId)]) {
      missingIds.add(ay.car.storeId);
    }
  }
}

if (missingIds.size > 0) {
  console.error(`\n❌ store-coords.json is missing ${missingIds.size} store(s): ${[...missingIds].join(", ")}`);
  console.error("Re-run: node scripts/geocode-stores.mjs\n");
  process.exit(1);
}

console.log(`✓ All stores accounted for in store-coords.json`);
