/**
 * One-time script: geocodes all CarMax stores in openpilot_cars.json
 * via Nominatim (OpenStreetMap) and writes pipeline/data/store-coords.json.
 *
 * Run: node scripts/geocode-stores.mjs
 * Takes ~4 min due to Nominatim's 1 req/sec rate limit.
 */

import { readFileSync, writeFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const USER_AGENT = "openpilot-car-finder/1.0 (geocoding carmax stores)";
const carsData = JSON.parse(readFileSync(join(__dirname, "../data/openpilot_cars.json"), "utf-8"));

// Collect unique stores
const stores = new Map();
for (const entry of carsData.entries) {
  for (const availableYear of entry.available_years) {
    if (availableYear.car && !stores.has(availableYear.car.storeId)) {
      stores.set(availableYear.car.storeId, {
        id: availableYear.car.storeId,
        name: availableYear.car.storeName,
        city: availableYear.car.storeCity,
        state: availableYear.car.state,
      });
    }
  }
}

console.log(`Found ${stores.size} unique stores. Starting geocoding...`);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function buildSearchUrl(query) {
  return `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`;
}

async function fetchFirstGeocodeResult(query) {
  const response = await fetch(buildSearchUrl(query), {
    headers: { "User-Agent": USER_AGENT },
  });
  const results = await response.json();
  return results[0] ?? null;
}

function toStoreCoords(geocodeResult) {
  return {
    lat: parseFloat(geocodeResult.lat),
    lng: parseFloat(geocodeResult.lon),
  };
}

const coords = {};
let done = 0;
let failed = [];

for (const store of stores.values()) {
  try {
    const primaryResult = await fetchFirstGeocodeResult(`CarMax ${store.city}, ${store.state}`);

    if (primaryResult) {
      coords[store.id] = toStoreCoords(primaryResult);
      done++;
      if (done % 20 === 0) console.log(`  ${done}/${stores.size} done...`);
    } else {
      // Fallback: try just city + state without "CarMax"
      await sleep(1100);
      const fallbackResult = await fetchFirstGeocodeResult(`${store.city}, ${store.state}`);
      if (fallbackResult) {
        coords[store.id] = toStoreCoords(fallbackResult);
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

writeFileSync(join(__dirname, "../data/store-coords.json"), JSON.stringify(coords, null, 2));
console.log(`\nDone! ${done} stores geocoded, ${failed.length} failed.`);
if (failed.length > 0) {
  console.log("Failed stores:", failed);
}
