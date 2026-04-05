import { readFileSync, writeFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const OPENPILOT_CARS_PATH = join(__dirname, "../data/openpilot_cars.json");
const STORE_COORDS_PATH = join(__dirname, "../data/store-coords.json");
const USER_AGENT = "openpilot-car-finder/1.0 (incremental geocoding carmax stores)";
const REQUEST_DELAY_MS = 1100;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function loadJson(path) {
  return JSON.parse(readFileSync(path, "utf-8"));
}

function saveJson(path, value) {
  writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`);
}

function collectStoresById(carsData) {
  const storesById = new Map();

  for (const entry of carsData.entries ?? []) {
    for (const availableYear of entry.available_years ?? []) {
      const car = availableYear.car;
      if (!car) continue;

      const storeId = String(car.storeId);
      if (storesById.has(storeId)) continue;

      storesById.set(storeId, {
        id: storeId,
        name: car.storeName ?? "",
        city: car.storeCity ?? "",
        state: car.state ?? "",
      });
    }
  }

  return storesById;
}

function findMissingStores(storesById, existingCoords) {
  return [...storesById.values()].filter((store) => existingCoords[store.id] == null);
}

function buildSearchUrl(query) {
  return `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`;
}

async function fetchFirstGeocodeResult(query) {
  const response = await fetch(buildSearchUrl(query), {
    headers: { "User-Agent": USER_AGENT },
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for query: ${query}`);
  }

  const results = await response.json();
  return results[0] ?? null;
}

function toStoreCoords(geocodeResult) {
  return {
    lat: parseFloat(geocodeResult.lat),
    lng: parseFloat(geocodeResult.lon),
  };
}

async function geocodeStore(store) {
  const primaryQuery = `CarMax ${store.city}, ${store.state}`;
  const primaryResult = await fetchFirstGeocodeResult(primaryQuery);
  if (primaryResult) {
    return toStoreCoords(primaryResult);
  }

  await sleep(REQUEST_DELAY_MS);
  const fallbackQuery = `${store.city}, ${store.state}`;
  const fallbackResult = await fetchFirstGeocodeResult(fallbackQuery);
  return fallbackResult ? toStoreCoords(fallbackResult) : null;
}

function sortCoordsByStoreId(coords) {
  return Object.fromEntries(
    Object.entries(coords).sort((a, b) => Number(a[0]) - Number(b[0])),
  );
}

async function main() {
  const carsData = loadJson(OPENPILOT_CARS_PATH);
  const existingCoords = loadJson(STORE_COORDS_PATH);

  const storesById = collectStoresById(carsData);
  const missingStores = findMissingStores(storesById, existingCoords);

  if (missingStores.length === 0) {
    console.log("No missing store coordinates. Nothing to geocode.");
    return;
  }

  console.log(`Found ${missingStores.length} missing store(s). Starting incremental geocoding...`);

  const nextCoords = { ...existingCoords };
  const failedStores = [];
  let geocodedCount = 0;

  for (const store of missingStores) {
    try {
      const coords = await geocodeStore(store);
      if (coords) {
        nextCoords[store.id] = coords;
        geocodedCount += 1;
      } else {
        failedStores.push(store);
        console.warn(
          `FAILED: storeId=${store.id} name="${store.name}" city="${store.city}" state="${store.state}"`,
        );
      }
    } catch (error) {
      failedStores.push(store);
      const message = error instanceof Error ? error.message : String(error);
      console.error(
        `ERROR: storeId=${store.id} name="${store.name}" city="${store.city}" state="${store.state}" -> ${message}`,
      );
    }

    await sleep(REQUEST_DELAY_MS);
  }

  saveJson(STORE_COORDS_PATH, sortCoordsByStoreId(nextCoords));

  console.log(`Geocoded ${geocodedCount} new store(s), ${failedStores.length} failed.`);

  if (failedStores.length > 0) {
    process.exitCode = 1;
  }
}

await main();
