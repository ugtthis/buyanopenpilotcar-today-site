import { createEffect, createMemo, createResource, createSignal, For, onMount, Show } from "solid-js";
import { CmdIcon, InfoCircleIcon, PinIcon, SearchIcon } from "./components/Icons";
import { CarDetailPanel } from "./components/CarDetailPanel";
import { ConfidenceChip, CONFIDENCE_STYLES } from "./components/ConfidenceChip";
import { ConfidenceDetail } from "./components/ConfidenceDetail";
import { ConfirmNavModal } from "./components/ConfirmNavModal";
import { DataTable } from "./components/DataTable";
import { InfoDrawer } from "./components/InfoDrawer";
import { SupportChip, SUPPORT_LEVEL_STYLES } from "./components/SupportChip";
import { SupportDetail } from "./components/SupportDetail";
import { cars } from "./data";
import { haversineMiles } from "./haversine";
import storeCoords from "./store-coords.json";
import type { CarListing, Column, PendingNav } from "./types";
import logo from "./assets/logo.png";

type Coords = { lat: number; lng: number };
const STORE_COORDS = storeCoords as Record<string, Coords>;

const formatPrice = (price: number | null) =>
  price != null ? `$${price.toLocaleString()}` : <span class="text-muted">—</span>;

const formatMpg = (city: number | null, hwy: number | null) =>
  city != null && hwy != null ? `${city} / ${hwy}` : <span class="text-muted">—</span>;

const formatNumberDetail = (value: number | null, suffix: string) =>
  value != null ? `${value.toLocaleString()} ${suffix}` : <span class="text-muted">—</span>;

const formatTextDetail = (value: string | null) =>
  value?.trim() ? value : <span class="text-muted">—</span>;

export default function App() {
  const [searchQuery, setSearchQuery] = createSignal("");
  let searchInputRef: HTMLInputElement | undefined;

  onMount(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef?.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  });
  const [activeSupportLevel, setActiveSupportLevel] = createSignal<string | null>(null);
  const [activeConfidenceLevel, setActiveConfidenceLevel] = createSignal<string | null>(null);
  const [selectedCar, setSelectedCar] = createSignal<CarListing | null>(null);
  const [pendingNav, setPendingNav] = createSignal<PendingNav | null>(null);
  const [showLegend, setShowLegend] = createSignal(false);

  const [userZip, setUserZip] = createSignal("");
  const [radius, setRadius] = createSignal<number | null>(null);

  const RADIUS_OPTIONS: { label: string; value: number | null }[] = [
    { label: "Any", value: null },
    { label: "25 mi", value: 25 },
    { label: "50 mi", value: 50 },
    { label: "100 mi", value: 100 },
  ];

  // Only triggers a fetch when the input is exactly 5 digits; undefined = skip fetch
  const validZip = () => /^\d{5}$/.test(userZip().trim()) ? userZip().trim() : undefined;

  const [zipCoords, { mutate: resetZipCoords }] = createResource(validZip, async (zip) => {
    const res = await fetch(`https://api.zippopotam.us/us/${zip}`);
    if (res.status === 404) return null; // valid zip format, but doesn't exist
    if (!res.ok) throw new Error(`Unexpected response ${res.status}`); // real network problem
    const data = await res.json();
    const place = data.places?.[0];
    if (!place) return null;
    return {
      lat: parseFloat(place.latitude),
      lng: parseFloat(place.longitude),
      city: place["place name"] as string,
      state: place["state abbreviation"] as string,
    };
  });

  // Invariant: whenever the zip is not valid, the cached result must be clear.
  // One declarative rule beats two imperative call sites.
  createEffect(() => { if (!validZip()) resetZipCoords(undefined); });

  function clearZip() {
    setUserZip("");
    setRadius(null);
  }

  // Reruns only when the zip changes — attaches distance to every car
  const carsWithDistance = createMemo((): CarListing[] => {
    const coords = zipCoords();
    if (!coords) return cars;
    return cars.map((car) => {
      const store = STORE_COORDS[String(car.storeId)];
      if (!store) return car;
      return { ...car, distance: Math.round(haversineMiles(coords.lat, coords.lng, store.lat, store.lng)) };
    });
  });

  // Reruns only when radius changes — cheap filter on already-computed distances
  const filteredCars = createMemo((): CarListing[] => {
    const maxMiles = radius();
    if (maxMiles == null) return carsWithDistance();
    return carsWithDistance().filter((car) => car.distance != null && car.distance <= maxMiles);
  });

  const confidenceLevelTitle = () => {
    const level = activeConfidenceLevel();
    return level ? `${CONFIDENCE_STYLES[level]?.label ?? level} Confidence` : "";
  };
  const selectedCarTitle = () => {
    const car = selectedCar();
    return car ? `${car.year} ${car.make} ${car.model}` : "";
  };
  const buildListingUrl = (car: CarListing) => `https://www.carmax.com/car/${car.stockNumber}`;

  function openCarDetail(car: CarListing) {
    setSelectedCar(car);
  }

  function startCarNavigation(car: CarListing) {
    const url = buildListingUrl(car);
    if (car.supportLevel === "upstream") {
      window.open(url, "_blank", "noreferrer");
      setSelectedCar(null);
      return;
    }

    setPendingNav({
      url,
      make: car.make,
      model: car.model,
      year: car.year,
      trim: car.trim,
      supportLevel: car.supportLevel,
    });
  }

  function confirmPendingNavigation() {
    const nav = pendingNav();
    if (nav) window.open(nav.url, "_blank", "noreferrer");
    setPendingNav(null);
    setSelectedCar(null);
  }

  const columns: Column<CarListing>[] = [
    {
      key: "distance",
      header: "Distance",
      render: (value) =>
        value != null
          ? <span class="tabular-nums font-medium text-accent-bright">{value as number} mi</span>
          : <span class="text-muted">—</span>,
    },
    {
      key: "matchConfidence",
      header: "Confidence",
      render: (value) => (
        <ConfidenceChip
          level={value as string}
          onClick={() => setActiveConfidenceLevel(value as string)}
        />
      ),
    },
    {
      key: "price",
      header: "Price",
      render: (value) => formatPrice(value as number | null),
    },
    { key: "make",  header: "Make"  },
    { key: "model", header: "Model" },
    { key: "year",  header: "Year"  },
    { key: "trim",  header: "Trim"  },
    {
      key: "supportLevel",
      header: "Support",
      render: (value) => (
        <SupportChip
          level={value as string}
          onClick={() => setActiveSupportLevel(value as string)}
        />
      ),
    },
    {
      key: "mileage",
      header: "Mileage",
      render: (value) =>
        value != null
          ? <span class="tabular-nums">{(value as number).toLocaleString()} mi</span>
          : <span class="text-muted">—</span>,
    },
    { key: "state",        header: "State"  },
    { key: "exteriorColor", header: "Color" },
    { key: "driveTrain",   header: "Drive"  },
    {
      key: "mpgCity",
      header: "MPG (C/H)",
      render: (_value, row) => formatMpg(row.mpgCity, row.mpgHighway),
    },
    { key: "engineType", header: "Engine" },
    { key: "storeName",  header: "Store"  },
    {
      key: "horsepower",
      header: "HP",
      render: (value) => formatNumberDetail(value as number | null, "hp"),
    },
    {
      key: "engineTorque",
      header: "Torque",
      render: (value) => formatNumberDetail(value as number | null, "lb-ft"),
    },
    {
      key: "engineSize",
      header: "Liters",
      render: (value) => formatTextDetail(value as string | null),
    },
    {
      key: "horsepowerRpm",
      header: "HP RPM",
      render: (value) => formatNumberDetail(value as number | null, "rpm"),
    },
    {
      key: "engineTorqueRpm",
      header: "Torque RPM",
      render: (value) => formatNumberDetail(value as number | null, "rpm"),
    },
  ];

  return (
    <div class="min-h-screen bg-canvas flex flex-col">


      <div class="bg-paper bg-noise border-b border-white/8 shrink-0">
        <div class="max-w-[1800px] mx-auto px-5 pt-12 pb-8">
          <img src={logo} alt="buyanopenpilotcar.today" class="h-auto max-h-16 sm:max-h-20 w-auto max-w-full" />
        </div>
      </div>

      {/* ── Search band ── */}
      <div class="bg-accent/5 border-b border-black/10 shrink-0">
        <div class="max-w-[1800px] mx-auto px-5 py-4 flex flex-col gap-3">

          {/* Row 1: Main text search */}
          <div
            class="flex items-center gap-3.5 px-4 py-3 rounded bg-surface transition-[border-color,box-shadow]"
            style={{
              border: "1.5px solid var(--color-accent)",
              "box-shadow": "0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.06)",
            }}
          >
            <SearchIcon class="w-5 h-5 text-accent shrink-0" />
            <input
              ref={searchInputRef}
              type="search"
              placeholder="Search makes, models, trims, states…"
              value={searchQuery()}
              onInput={(e) => setSearchQuery(e.currentTarget.value)}
              class="flex-1 min-w-0 bg-transparent border-none text-base text-content placeholder:text-muted
                     focus:shadow-none focus:border-transparent"
              style={{ "box-shadow": "none" }}
            />
            <Show when={searchQuery()} fallback={
              <kbd class="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 text-[11px] font-medium
                          rounded border border-black/12 text-muted bg-canvas select-none leading-5">
                <CmdIcon class="w-3 h-3" />
                K
              </kbd>
            }>
              <button
                onClick={() => setSearchQuery("")}
                aria-label="Clear search"
                class="flex items-center justify-center w-5 h-5 rounded text-muted shrink-0
                       hover:bg-raised hover:text-content transition-colors border-0 bg-transparent cursor-pointer text-xs"
              >
                ✕
              </button>
            </Show>
          </div>

          {/* Row 2: Location + radius — two linked controls, stacked on mobile, side-by-side on desktop */}
          <div class="flex flex-col sm:flex-row gap-2 items-stretch">

            {/* Left: zip input — always visible, acts as the feature entry point */}
            <div
              class="flex items-center gap-2.5 px-3.5 py-2.5 rounded bg-surface flex-1 min-w-0 transition-[border-color]"
              style={{
                border: zipCoords()
                  ? "1.5px solid var(--color-accent)"
                  : "1.5px solid rgba(255,255,255,0.15)",
              }}
            >
              <PinIcon
                class="w-3.5 h-3.5 shrink-0 transition-colors"
                classList={{ "text-accent": !!zipCoords(), "text-muted": !zipCoords() }}
              />

              <span class="text-xs font-medium text-muted shrink-0 select-none">Near</span>

              <input
                type="text"
                inputmode="numeric"
                pattern="\d{5}"
                maxlength="5"
                placeholder="ZIP code"
                value={userZip()}
                onInput={(e) => {
                  const digits = e.currentTarget.value.replace(/\D/g, "");
                  e.currentTarget.value = digits;
                  setUserZip(digits);
                }}
                class="flex-1 min-w-0 bg-transparent border-none text-sm text-content placeholder:text-muted
                       focus:shadow-none focus:border-transparent tabular-nums"
                style={{ "box-shadow": "none" }}
                aria-label="Enter your ZIP code to find nearest cars"
              />

              <Show when={zipCoords.loading}>
                <span class="text-muted text-[11px] animate-pulse shrink-0 select-none">Locating…</span>
              </Show>
              <Show when={!zipCoords.loading && validZip() && zipCoords() === null}>
                <span class="text-[11px] text-warning shrink-0 select-none">ZIP not found</span>
              </Show>
              <Show when={zipCoords.error}>
                <span class="text-[11px] text-warning shrink-0 select-none">Connection error</span>
              </Show>
              <Show when={zipCoords()}>
                {(coords) => (
                  <>
                    <span class="text-[11px] font-medium text-accent-bright shrink-0 whitespace-nowrap select-none">
                      {coords().city}, {coords().state}
                    </span>
                    <button
                      onClick={clearZip}
                      aria-label="Clear location"
                      class="flex items-center justify-center w-5 h-5 rounded shrink-0 text-muted
                             hover:bg-raised hover:text-content transition-colors border-0 bg-transparent cursor-pointer text-[11px]"
                    >
                      ✕
                    </button>
                  </>
                )}
              </Show>
            </div>

            {/* Right: radius selector — appears once ZIP resolves, full-width on mobile */}
            <div
              class="flex items-center rounded bg-surface overflow-hidden transition-[opacity,border-color]"
              style={{
                border: "1.5px solid rgba(255,255,255,0.15)",
                opacity: zipCoords() ? "1" : "0.4",
                "pointer-events": zipCoords() ? "auto" : "none",
              }}
            >
              <span class="pl-3 pr-2.5 text-[11px] font-semibold text-muted uppercase tracking-wider shrink-0 select-none whitespace-nowrap">
                Within
              </span>
              <div class="w-px self-stretch bg-white/10 shrink-0" />
              <For each={RADIUS_OPTIONS}>
                {(opt) => (
                  <button
                    onClick={() => setRadius(opt.value)}
                    disabled={!zipCoords()}
                    class="flex-1 sm:flex-none px-3 py-2.5 text-xs font-medium whitespace-nowrap border-0
                           transition-colors duration-150 relative"
                    classList={{
                      "bg-raised text-content": radius() === opt.value,
                      "bg-transparent text-muted hover:text-secondary": radius() !== opt.value,
                    }}
                    aria-pressed={radius() === opt.value}
                  >
                    {opt.label}
                  </button>
                )}
              </For>
            </div>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-hidden">
        <div class="h-full overflow-auto">
          <div class="max-w-[1800px] mx-auto px-5 pt-4 pb-10">
            <DataTable
              data={filteredCars()}
              columns={columns}
              pageSize={30}
              searchQuery={searchQuery()}
              onSearchChange={setSearchQuery}
              onRowClick={openCarDetail}
              distanceActive={!!zipCoords()}
              legendSlot={
                <div class="relative shrink-0">
                  <button
                    onClick={() => setShowLegend(v => !v)}
                    class="flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium rounded-sm bg-panel border border-white/15 text-secondary hover:bg-raised hover:text-content transition-colors cursor-pointer"
                    classList={{ "text-content bg-raised": showLegend() }}
                  >
                    <InfoCircleIcon class="w-3.5 h-3.5 shrink-0" />
                    <span>Legend</span>
                  </button>
                  <Show when={showLegend()}>
                    <div class="fixed inset-0 z-10" onClick={() => setShowLegend(false)} aria-hidden="true" />
                    <div class="absolute right-0 z-20 mt-1 w-72 max-w-[calc(100vw-2rem)] rounded-sm border border-white/15 bg-panel bp-elevation-3 p-3 flex flex-col gap-3">
                      <div>
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-muted mb-2.5">Support levels</p>
                        <div class="flex flex-wrap gap-x-1.5 gap-y-2.5">
                          {Object.keys(SUPPORT_LEVEL_STYLES).map((level) => (
                            <SupportChip level={level} onClick={() => { setActiveSupportLevel(level); setShowLegend(false); }} />
                          ))}
                        </div>
                      </div>
                      <div class="border-t border-white/8" />
                      <div>
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-muted mb-2.5">Confidence levels</p>
                        <div class="flex flex-wrap gap-x-1.5 gap-y-2.5">
                          {Object.keys(CONFIDENCE_STYLES).map((level) => (
                            <ConfidenceChip level={level} onClick={() => { setActiveConfidenceLevel(level); setShowLegend(false); }} />
                          ))}
                        </div>
                      </div>
                    </div>
                  </Show>
                </div>
              }
            />
            </div>
        </div>
      </div>

      <ConfirmNavModal
        pending={pendingNav()}
        onConfirm={confirmPendingNavigation}
        onCancel={() => setPendingNav(null)}
      />

      <InfoDrawer
        open={selectedCar() !== null}
        title={selectedCarTitle()}
        onClose={() => setSelectedCar(null)}
      >
        <Show when={selectedCar()}>
          {(car) => <CarDetailPanel car={car()} onOpenListingLink={startCarNavigation} />}
        </Show>
      </InfoDrawer>

      <InfoDrawer
        open={activeSupportLevel() !== null}
        title={activeSupportLevel() ?? ""}
        onClose={() => setActiveSupportLevel(null)}
      >
        <SupportDetail level={activeSupportLevel() ?? ""} />
      </InfoDrawer>

      <InfoDrawer
        open={activeConfidenceLevel() !== null}
        title={confidenceLevelTitle()}
        onClose={() => setActiveConfidenceLevel(null)}
      >
        <ConfidenceDetail level={activeConfidenceLevel() ?? ""} />
      </InfoDrawer>
    </div>
  );
}
