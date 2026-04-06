import { onCleanup, onMount, For, Show, type JSXElement } from "solid-js";
import { CONFIDENCE_CONTENT } from "../confidenceContent";
import { SUPPORT_TYPE_CONTENT } from "../supportContent";
import type { CarListing } from "../types";
import { buildopendbcSiteUrl } from "../urls";
import { ConfidenceChip } from "./ConfidenceChip";
import { SupportChip } from "./SupportChip";

type CarDetailPanelProps = {
  car: CarListing;
  onOpenListingLink: (car: CarListing) => void;
  onCarNameVisibilityChange?: (isVisible: boolean) => void;
};

type DetailItem = {
  label: string;
  value: JSXElement;
};

type DetailSection = {
  title: string;
  items: DetailItem[];
};

const formatPrice = (price: number | null) => (price != null ? `$${price.toLocaleString()}` : "—");
const formatMileage = (mileage: number | null) => (mileage != null ? `${mileage.toLocaleString()} mi` : "—");
const formatDistance = (distance: number | undefined) => (distance != null ? `${distance} mi` : "—");
const formatNumberDetail = (value: number | null, suffix: string) => (value != null ? `${value.toLocaleString()} ${suffix}` : "—");
const formatTextDetail = (value: string | null) => (value?.trim() ? value : "—");
const formatBooleanDetail = (value: boolean) => (value ? "Yes" : "No");
const formatMpg = (city: number | null, highway: number | null) => (
  city != null && highway != null ? `${city} / ${highway}` : "—"
);
const SUPPORT_SPECS_UNAVAILABLE = "N/A";
const CAR_TITLE_VISIBLE_THRESHOLD = 0.25;

const DetailRow = (props: DetailItem) => (
  <div class="flex items-start justify-between gap-4 border-t border-white/8 py-2.5">
    <span class="text-md font-medium text-muted">{props.label}</span>
    <div class="min-w-0 text-right text-base text-content">{props.value}</div>
  </div>
);

const DetailSectionCard = (props: DetailSection) => (
  <div class="rounded-sm border border-white/8 bg-canvas/60 px-4 py-3">
    <div class="mb-1 text-md font-bold uppercase tracking-wide text-muted">{props.title}</div>
    <div class="flex flex-col">
      <For each={props.items}>{(item) => <DetailRow {...item} />}</For>
    </div>
  </div>
);

export function CarDetailPanel(props: CarDetailPanelProps) {
  let carNameRef: HTMLParagraphElement | undefined;

  onMount(() => {
    const onVisibilityChange = props.onCarNameVisibilityChange;
    const target = carNameRef;
    if (!onVisibilityChange || !target || typeof IntersectionObserver === "undefined") return;

    // Keep the drawer header concise until the in-panel car title scrolls away.
    const observer = new IntersectionObserver(
      ([entry]) => onVisibilityChange(entry.isIntersecting && entry.intersectionRatio > CAR_TITLE_VISIBLE_THRESHOLD),
      { threshold: [0, CAR_TITLE_VISIBLE_THRESHOLD, 0.5, 1] },
    );

    onVisibilityChange(true);
    observer.observe(target);
    onCleanup(() => observer.disconnect());
  });

  const supportDescription = () =>
    SUPPORT_TYPE_CONTENT[props.car.supportLevel]?.paragraphs[0] ?? "No support details available for this vehicle.";
  const confidenceDescription = () =>
    CONFIDENCE_CONTENT[props.car.matchConfidence]?.paragraphs[0] ?? "No confidence details available for this vehicle.";
  const showSupportSpecs = props.car.supportLevel === "upstream" || props.car.supportLevel === "dashcam mode";
  const supportSpecItems: DetailItem[] = [
    { label: "Longitudinal", value: props.car.supportSpecs.longitudinal },
    { label: "FSR Longitudinal", value: props.car.supportSpecs.fsrLongitudinal },
    { label: "FSR Steering", value: props.car.supportSpecs.fsrSteering },
    {
      label: "Experimental Long",
      value: formatBooleanDetail(props.car.supportSpecs.experimentalLongitudinalAvailable),
    },
    {
      label: "OP Long Control",
      value: formatBooleanDetail(props.car.supportSpecs.openpilotLongitudinalControl),
    },
    { label: "Steering Torque", value: props.car.supportSpecs.steeringTorque },
    { label: "Auto Resume", value: props.car.supportSpecs.autoResumeStar },
  ];

  const detailSections = (): DetailSection[] => [
    {
      title: "Listing",
      items: [
        { label: "Price", value: <span class="tabular-nums">{formatPrice(props.car.price)}</span> },
        { label: "Mileage", value: <span class="tabular-nums">{formatMileage(props.car.mileage)}</span> },
        ...(props.car.distance != null
          ? [{ label: "Distance", value: <span class="tabular-nums">{formatDistance(props.car.distance)}</span> }]
          : []),
        { label: "State", value: props.car.state },
        { label: "Store", value: props.car.storeName },
        { label: "Stock", value: <span class="tabular-nums">{props.car.stockNumber}</span> },
      ],
    },
    {
      title: "Vehicle",
      items: [
        { label: "Color", value: props.car.exteriorColor },
        { label: "Drive", value: props.car.driveTrain },
        { label: "MPG (C/H)", value: <span class="tabular-nums">{formatMpg(props.car.mpgCity, props.car.mpgHighway)}</span> },
      ],
    },
    {
      title: "Support Specs",
      items: showSupportSpecs
        ? supportSpecItems
        : supportSpecItems.map(({ label }) => ({ label, value: SUPPORT_SPECS_UNAVAILABLE })),
    },
    {
      title: "Powertrain",
      items: [
        { label: "Engine", value: props.car.engineType },
        { label: "Liters", value: formatTextDetail(props.car.engineSize) },
        { label: "HP", value: <span class="tabular-nums">{formatNumberDetail(props.car.horsepower, "hp")}</span> },
        { label: "Torque", value: <span class="tabular-nums">{formatNumberDetail(props.car.engineTorque, "lb-ft")}</span> },
        { label: "HP RPM", value: <span class="tabular-nums">{formatNumberDetail(props.car.horsepowerRpm, "rpm")}</span> },
        { label: "Torque RPM", value: <span class="tabular-nums">{formatNumberDetail(props.car.engineTorqueRpm, "rpm")}</span> },
      ],
    },
  ];

  return (
    <div class="flex min-h-full flex-col gap-5">
      <div class="flex flex-col gap-3">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p ref={carNameRef} class="text-xl font-bold leading-tight text-content">
              {props.car.year} {props.car.make} {props.car.model}
            </p>
            <Show when={props.car.trim}>
              <p class="mt-1 text-sm text-secondary">{props.car.trim}</p>
            </Show>
          </div>
          <span class="rounded-sm bg-raised px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted">
            Price {formatPrice(props.car.price)}
          </span>
        </div>

        <p class="text-sm leading-relaxed text-secondary">
          Review the listing details here, then continue to CarMax when you are ready.
        </p>
      </div>

      <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div class="rounded-sm border border-white/8 bg-canvas/60 px-4 py-3">
          <div class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">Support Level</div>
          <div class="flex flex-col gap-2">
            <SupportChip level={props.car.supportLevel} />
            <p class="text-sm leading-relaxed text-secondary">{supportDescription()}</p>
            <div class="border-t border-white/8 pt-2">
              <div class="text-[11px] font-semibold uppercase tracking-wider text-muted">Package requirements</div>
              <p class="mt-1 text-sm leading-relaxed text-content">{formatTextDetail(props.car.packageRequirements)}</p>
            </div>
          </div>
        </div>
        <div class="rounded-sm border border-white/8 bg-canvas/60 px-4 py-3">
          <div class="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">Confidence Level</div>
          <div class="flex flex-col gap-2">
            <ConfidenceChip level={props.car.matchConfidence} />
            <p class="text-sm leading-relaxed text-secondary">{confidenceDescription()}</p>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-3">
        <For each={detailSections()}>{(section) => <DetailSectionCard {...section} />}</For>
      </div>

      <div class="sticky -bottom-4 z-10 -mx-4 -mb-4 mt-auto flex flex-col gap-3 border-t border-white/8 bg-surface px-4 py-4 pb-1">
        <button
          onClick={() => props.onOpenListingLink(props.car)}
          class="inline-flex min-h-12 w-full items-center justify-center rounded-sm bg-accent px-5 py-3 text-base font-semibold text-white transition-colors hover:bg-accent-muted cursor-pointer"
        >
          View Listing ↗
        </button>
        <a
          href={buildopendbcSiteUrl(props.car.make, props.car.modelOriginal)}
          target="_blank"
          rel="noreferrer"
          class="inline-flex min-h-12 w-full items-center justify-center rounded-sm border border-white/12 bg-transparent px-5 py-3 text-base font-semibold text-secondary transition-colors hover:bg-white/5 cursor-pointer"
        >
          View Detailed Support Specs ↗
        </a>
      </div>
    </div>
  );
}
