import type { JSXElement } from "solid-js";

export type SupportLevel =
  | "upstream"
  | "community"
  | "custom"
  | "under review"
  | "not compatible"
  | "dashcam mode";

export type MatchConfidence = "extra_high" | "high" | "medium" | "low";

export type SupportSpecs = {
  longitudinal: string;
  fsrLongitudinal: string;
  fsrSteering: string;
  experimentalLongitudinalAvailable: boolean;
  openpilotLongitudinalControl: boolean;
  steeringTorque: string;
  autoResumeStar: string;
};

export type CarListing = {
  stockNumber: number;
  make: string;
  model: string;
  modelOriginal: string;
  supportSpecs: SupportSpecs;
  supportLevel: SupportLevel;
  matchConfidence: MatchConfidence;
  year: number;
  trim: string;
  price: number | null;
  mileage: number;
  state: string;
  exteriorColor: string;
  driveTrain: string;
  mpgCity: number | null;
  mpgHighway: number | null;
  engineType: string;
  storeName: string;
  storeId: number;
  horsepower: number | null;
  engineTorque: number | null;
  engineSize: string | null;
  horsepowerRpm: number | null;
  engineTorqueRpm: number | null;
  distance?: number;
};

export type Column<T> = {
  header: string;
  render?: (value: unknown, row: T) => JSXElement;
} & (
  | { key: keyof T & string; id?: never; accessorFn?: never }
  | { id: string; accessorFn: (row: T) => unknown; key?: never }
);

export type DataTableProps<T extends object> = {
  data: T[];
  columns: Column<T>[];
  pageSize?: number;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onRowClick?: (row: T) => void;
  distanceActive?: boolean;
  legendSlot?: JSXElement;
};

export type PendingNav = {
  url: string;
  make: string;
  model: string;
  year: number;
  trim: string;
  supportLevel: string;
};
