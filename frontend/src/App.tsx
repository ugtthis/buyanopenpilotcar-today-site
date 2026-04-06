import clsx from "clsx";
import { createEffect, createMemo, createResource, createSignal, For, onMount, Show, type JSXElement } from "solid-js";
import { CheckmarkBadgeIcon, CmdIcon, InfoCircleIcon, PencilFeedbackIcon, PinIcon, RemoveCircleIcon, SearchIcon } from "./components/Icons";
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
import storeCoords from "../../pipeline/data/store-coords.json";
import type { CarListing, Column, PendingNav } from "./types";
import logo from "./assets/logo.png";

type Coords = { lat: number; lng: number };
const STORE_COORDS = storeCoords as Record<string, Coords>;

const trackEvent = (name: string, props: Record<string, string | number>) => {
  (window as unknown as { plausible?: (n: string, o: { props: Record<string, string | number> }) => void })
    .plausible?.(name, { props });
};
const MAX_SEARCH_QUERY_LENGTH = 50;

const formatPrice = (price: number | null) =>
  price != null ? `$${price.toLocaleString()}` : <span class="text-muted">—</span>;

const formatMpg = (city: number | null, hwy: number | null) =>
  city != null && hwy != null ? `${city} / ${hwy}` : <span class="text-muted">—</span>;

const formatNumberDetail = (value: number | null, suffix: string) =>
  value != null ? `${value.toLocaleString()} ${suffix}` : <span class="text-muted">—</span>;

const formatTextDetail = (value: string | null) =>
  value?.trim() ? value : <span class="text-muted">—</span>;

const normalizeSearchQuery = (value: string) =>
  value.replace(/[\u0000-\u001F\u007F]/g, "").slice(0, MAX_SEARCH_QUERY_LENGTH);


export default function App() {
  const [searchQuery, setSearchQuery] = createSignal("");
  let searchInputRef: HTMLInputElement | undefined;
  const blurOnEnter = (e: KeyboardEvent & { currentTarget: HTMLInputElement }) => {
    if (e.key === "Enter") e.currentTarget.blur();
  };

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
  const [isCarDrawerOpen, setIsCarDrawerOpen] = createSignal(false);
  const [carDrawerTitle, setCarDrawerTitle] = createSignal<JSXElement>("Car Details");
  const [pendingNav, setPendingNav] = createSignal<PendingNav | null>(null);
  const [reopenCarDrawerAfterModal, setReopenCarDrawerAfterModal] = createSignal(false);
  const [showLegend, setShowLegend] = createSignal(false);
  const [showFeedback, setShowFeedback] = createSignal(false);

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
  createEffect(() => {
    if (!validZip()) setRadius(null);
  });

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

  const canFilterByDistance = createMemo(() => zipCoords() != null);

  // Reruns only when radius changes — cheap filter on already-computed distances
  const filteredCars = createMemo((): CarListing[] => {
    const maxMiles = radius();
    if (!canFilterByDistance() || maxMiles == null) return carsWithDistance();
    return carsWithDistance().filter((car) => car.distance != null && car.distance <= maxMiles);
  });

  const buildListingUrl = (car: CarListing) => `https://www.carmax.com/car/${car.stockNumber}`;

  function closeCarDetail() {
    setIsCarDrawerOpen(false);
    setCarDrawerTitle("Car Details");
  }

  function openCarDetail(car: CarListing) {
    setReopenCarDrawerAfterModal(false);
    setSelectedCar(car);
    setIsCarDrawerOpen(true);
    trackEvent("Car Detail Opened", { make: car.make, model: car.model, year: car.year, supportLevel: car.supportLevel, confidence: car.matchConfidence, package: car.packageRequirements ?? "" });
  }

  function startCarNavigation(car: CarListing) {
    const url = buildListingUrl(car);
    if (car.supportLevel === "upstream") {
      trackEvent("Listing Clicked", { make: car.make, model: car.model, year: car.year, supportLevel: car.supportLevel, confidence: car.matchConfidence, package: car.packageRequirements ?? "", friction: "none" });
      window.open(url, "_blank", "noreferrer");
      closeCarDetail();
      return;
    }

    setReopenCarDrawerAfterModal(true);
    setIsCarDrawerOpen(false);
    setPendingNav({
      url,
      make: car.make,
      model: car.model,
      year: car.year,
      trim: car.trim,
      supportLevel: car.supportLevel,
      matchConfidence: car.matchConfidence,
      packageRequirements: car.packageRequirements ?? "",
    });
  }

  function confirmPendingNavigation() {
    const nav = pendingNav();
    if (nav) {
      trackEvent("Listing Clicked", { make: nav.make, model: nav.model, year: nav.year, supportLevel: nav.supportLevel, confidence: nav.matchConfidence, package: nav.packageRequirements, friction: "warning shown" });
      window.open(nav.url, "_blank", "noreferrer");
    }
    setReopenCarDrawerAfterModal(false);
    setPendingNav(null);
    closeCarDetail();
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
      header: () => (
        <span title="How confident a given car listing is to be compatible with openpilot.">
          Confidence Level
        </span>
      ),
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
    {
      id: "car",
      header: "Car",
      accessorFn: (row) => `${row.make} ${row.model}`,
    },
    { key: "year", header: "Year" },
    { key: "trim",  header: "Trim"  },
    {
      key: "supportLevel",
      header: "Support Level",
      render: (value) => (
        <SupportChip
          level={value as string}
          onClick={() => setActiveSupportLevel(value as string)}
        />
      ),
    },
    {
      key: "packageRequirements",
      header: () => (
        <span
          class="inline-flex items-center gap-1.5 rounded border px-1.75 py-0.75 font-semibold"
          title="Without the required package, the car will not be compatible with openpilot."
        >
          <span aria-hidden="true">⚠</span>
          <span>Package To Verify</span>
        </span>
      ),
      render: (value) => formatTextDetail(value as string | null),
    },
    {
      key: "mileage",
      header: "Mileage",
      render: (value) =>
        value != null
          ? <span class="tabular-nums">{(value as number).toLocaleString()} mi</span>
          : <span class="text-muted">—</span>,
    },
    { key: "exteriorColor", header: "Color" },
    { key: "state",        header: "State"  },
    {
      id: "longitudinal",
      header: () => (
        <span title="The system responsible for acceleration and braking control.">
          Longitudinal
        </span>
      ),
      accessorFn: (row) => row.supportSpecs.longitudinal,
    },
    {
      id: "autoResume",
      header: () => (
        <span title="Whether openpilot can automatically resume driving after coming to a complete stop.">
          Auto Resume
        </span>
      ),
      accessorFn: (row) => row.supportSpecs.autoResumeStar,
      render: (value) => (
        (value as string) === "full"
          ? (
            <span class="flex w-full justify-center">
              <span class="inline-flex items-center text-positive/80" title="Auto resume supported">
                <CheckmarkBadgeIcon class="w-[1.5em] h-[1.5em]" />
              </span>
            </span>
          )
          : (
            <span class="flex w-full justify-center">
              <span class="inline-flex items-center text-danger/80" title="Auto resume not supported">
                <RemoveCircleIcon class="w-[1.5em] h-[1.5em]" />
              </span>
            </span>
          )
      ),
    },
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
        {/* Logo row */}
        <div class="max-w-[1800px] mx-auto px-5 pt-15 sm:pt-17 pb-8 ">
          <img src={logo} alt="buyanopenpilotcar.today" class="h-auto max-[401px]:max-h-13 max-h-15 sm:max-h-20 w-auto max-w-full" />
        </div>
      </div>

      {/* ── Search band ── */}
      <div class="bg-accent/5 border-b border-black/10 shrink-0">
        <div class="max-w-[1800px] mx-auto px-5 py-4 flex flex-col gap-3">

          {/* Row 1: Main text search */}
          <div
            class="flex items-center gap-3.5 px-4 py-3 rounded overflow-hidden bg-surface transition-[border-color,box-shadow]"
            style={{
              border: "1.5px solid var(--color-accent)",
              "box-shadow": "0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.06)",
            }}
          >
            <SearchIcon class="w-5 h-5 text-accent shrink-0" />
            <input
              ref={searchInputRef}
              type="search"
              placeholder="Search makes, models, states…"
              value={searchQuery()}
              onInput={(e) => setSearchQuery(normalizeSearchQuery(e.currentTarget.value))}
              maxLength={MAX_SEARCH_QUERY_LENGTH}
              onKeyDown={blurOnEnter}
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
                class="-my-3 -mr-4 px-4 flex items-center justify-center self-stretch shrink-0 rounded-none
                       border-none cursor-pointer text-lg font-bold transition-colors
                       hover:bg-red-500/10 hover:text-red-600"
              >
                ✕
              </button>
            </Show>
          </div>

          {/* Row 2: Location + radius — two linked controls, stacked on mobile, side-by-side on desktop */}
          <div class="flex flex-col sm:flex-row gap-2 items-stretch">

            {/* Left: zip input — always visible, acts as the feature entry point */}
            <div
              class="flex items-center gap-2.5 px-3.5 py-2.5 rounded overflow-hidden bg-surface flex-1 min-w-0 transition-[border-color]"
              style={{
                border: zipCoords()
                  ? "1.5px solid var(--color-accent)"
                  : "1.5px solid rgba(255,255,255,0.15)",
              }}
            >
              <PinIcon
                class={clsx(
                  "w-5 h-5 shrink-0 transition-colors",
                  zipCoords() ? "text-accent" : "text-muted",
                )}
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
                onKeyDown={blurOnEnter}
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
                      class="-my-2.5 -mr-3.5 px-3.5 flex items-center justify-center self-stretch shrink-0 rounded-none
                             border-none cursor-pointer text-lg font-bold transition-colors
                             hover:bg-red-500/10 hover:text-red-600"
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
                    class={clsx(
                      "flex-1 sm:flex-none px-3 py-2.5 text-xs font-medium whitespace-nowrap border-0",
                      "transition-colors duration-150 relative",
                      radius() === opt.value ? "bg-raised text-content" : "bg-transparent text-muted hover:text-secondary",
                    )}
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
              isRowSelected={(row) => row.stockNumber === selectedCar()?.stockNumber}
              distanceActive={!!zipCoords()}
              toolbarSlot={
                <div class="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => { setShowFeedback(true); trackEvent("Feedback Drawer Opened", {}); }}
                    class="flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium rounded-sm bg-panel
                           border border-white/15 text-secondary hover:bg-raised hover:text-content
                           transition-colors cursor-pointer"
                    title="Leave feedback"
                  >
                    <PencilFeedbackIcon class="w-4 h-4 shrink-0" />
                  </button>

                  <div class="relative shrink-0">
                    <button
                      onClick={() => setShowLegend(v => !v)}
                      class={clsx(
                        "flex items-center gap-1.5 px-3 py-2.5 text-xs font-medium rounded-sm bg-panel",
                        "border border-white/15 text-secondary hover:bg-raised hover:text-content transition-colors cursor-pointer",
                        showLegend() && "text-content bg-raised",
                      )}
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
                </div>
              }
            />
          </div>
        </div>
      </div>

      <ConfirmNavModal
        pending={pendingNav()}
        onConfirm={confirmPendingNavigation}
        onCancel={() => {
          setPendingNav(null);
          setIsCarDrawerOpen(true);
          setReopenCarDrawerAfterModal(false);
        }}
      />

      <InfoDrawer
        open={isCarDrawerOpen()}
        title={carDrawerTitle()}
        onClose={closeCarDetail}
        onClosed={() => {
          if (reopenCarDrawerAfterModal()) return;
          setSelectedCar(null);
        }}
      >
        <Show when={selectedCar()}>
          {(car) => (
            <CarDetailPanel
              car={car()}
              onOpenListingLink={startCarNavigation}
              onTitleChange={setCarDrawerTitle}
            />
          )}
        </Show>
      </InfoDrawer>

      <InfoDrawer
        open={activeSupportLevel() !== null}
        title="Support Levels"
        onClose={() => setActiveSupportLevel(null)}
      >
        <SupportDetail />
      </InfoDrawer>

      <InfoDrawer
        open={activeConfidenceLevel() !== null}
        title="Confidence Levels"
        onClose={() => setActiveConfidenceLevel(null)}
      >
        <ConfidenceDetail />
      </InfoDrawer>

      <InfoDrawer
        open={showFeedback()}
        title="Leave Feedback"
        onClose={() => setShowFeedback(false)}
        mobileHeight="35%"
      >
        <div class="flex flex-col gap-6">
          <p class="text-sm text-secondary leading-relaxed">
            Have a suggestion, found inaccurate information, or want to request a feature?
          </p>
          <div class="flex flex-col gap-3">
            <a
              href="https://buyanopenpilotcar-today.userjot.com/?cursor=1&order=top&limit=10"
              target="_blank"
              rel="noreferrer"
              onClick={() => trackEvent("Feedback Link Clicked", {})}
              class="inline-flex min-h-12 w-full items-center justify-center rounded-sm bg-accent px-5 py-3 text-base font-semibold text-white transition-colors hover:bg-accent-muted cursor-pointer"
            >
              Submit Feedback ↗
            </a>
          </div>
        </div>
      </InfoDrawer>
    </div>
  );
}
