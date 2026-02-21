/**
 * One-time script: geocodes all CarMax stores in openpilot_cars.json
 * via Nominatim (OpenStreetMap) and writes store-coords.json.
 *
 * Run: node scripts/geocode-stores.mjs
 * Takes ~4 min due to Nominatim's 1 req/sec rate limit.
 */

import { readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const rawJson = JSON.parse(readFileSync(join(__dirname, "../openpilot_cars.json"), "utf-8"));

// Collect unique stores
const stores = new Map();
for (const entry of rawJson.entries) {
  for (const ay of entry.available_years) {
    if (ay.car && !stores.has(ay.car.storeId)) {
      stores.set(ay.car.storeId, {
        id: ay.car.storeId,
        name: ay.car.storeName,
        city: ay.car.storeCity,
        state: ay.car.state,
      });
    }
  }
}

console.log(`Found ${stores.size} unique stores. Starting geocoding...`);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const coords = {};
let done = 0;
let failed = [];

for (const store of stores.values()) {
  const query = `CarMax ${store.city}, ${store.state}`;
  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`;

  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "openpilot-car-finder/1.0 (geocoding carmax stores)" },
    });
    const data = await res.json();

    if (data.length > 0) {
      coords[store.id] = {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
      };
      done++;
      if (done % 20 === 0) console.log(`  ${done}/${stores.size} done...`);
    } else {
      // Fallback: try just city + state without "CarMax"
      const url2 = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(`${store.city}, ${store.state}`)}&format=json&limit=1`;
      await sleep(1100);
      const res2 = await fetch(url2, {
        headers: { "User-Agent": "openpilot-car-finder/1.0 (geocoding carmax stores)" },
      });
      const data2 = await res2.json();
      if (data2.length > 0) {
        coords[store.id] = {
          lat: parseFloat(data2[0].lat),
          lng: parseFloat(data2[0].lon),
        };
        done++;
      } else {
        console.warn(`  FAILED: storeId=${store.id} name="${store.name}" city="${store.city}" state="${store.state}"`);
        failed.push(store);
      }
    }
  } catch (err) {
    console.error(`  ERROR: storeId=${store.id}:`, err.message);
    failed.push(store);
  }

  // Respect Nominatim rate limit: max 1 request/second
  await sleep(1100);
}

writeFileSync(join(__dirname, "../src/store-coords.json"), JSON.stringify(coords, null, 2));
console.log(`\nDone! ${done} stores geocoded, ${failed.length} failed.`);
if (failed.length > 0) {
  console.log("Failed stores:", failed);
}
