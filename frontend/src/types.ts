import type { JSXElement } from "solid-js";

export type SupportLevel =
  | "upstream"
  | "community"
  | "custom"
  | "under review"
  | "not compatible"
  | "dashcam mode";

export type MatchConfidence = "extra_high" | "high" | "medium" | "low";

export type CarListing = {
  stockNumber: number;
  make: string;
  model: string;
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
  key: keyof T & string;
  header: string;
  render?: (value: T[keyof T], row: T) => JSXElement;
};

export type DataTableProps<T extends object> = {
  data: T[];
  columns: Column<T>[];
  pageSize?: number;
  searchQuery: string;
  onSearchChange: (value: string) => void;
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
