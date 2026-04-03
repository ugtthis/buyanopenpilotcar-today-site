import type { CarListing, MatchConfidence, SupportLevel } from "./types";
import rawJson from "../../pipeline/data/openpilot_cars.json";

type RawCar = {
  stockNumber: number;
  year: number;
  make: string;
  model: string;
  trim: string;
  basePrice: number | null;
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
  horsepowerRpm: number | null;
  engineSize: string | null;
  engineTorque: number | null;
  engineTorqueRpm: number | null;
};

type RawYear = {
  year: number;
  match_confidence: string;
  car: RawCar | null;
};

type RawEntry = {
  make: string;
  model: string;
  package_requirements: string;
  support_level: { type: string };
  available_years: RawYear[];
};

type RawJson = { entries: RawEntry[] };

// Flatten entries[].available_years[].car into one row per listing
export const cars: CarListing[] = (rawJson as RawJson).entries.flatMap(
  (entry) =>
    entry.available_years
      .filter((ay) => ay.car !== null)
      .map((ay) => {
        const car = ay.car!;
        return {
          stockNumber: car.stockNumber,
          make: entry.make,
          model: entry.model,
          supportLevel: entry.support_level.type as SupportLevel,
          matchConfidence: ay.match_confidence as MatchConfidence,
          year: car.year,
          trim: car.trim ?? "",
          price: car.basePrice,
          mileage: car.mileage,
          state: car.state ?? "",
          exteriorColor: car.exteriorColor ?? "",
          driveTrain: car.driveTrain ?? "",
          mpgCity: car.mpgCity,
          mpgHighway: car.mpgHighway,
          engineType: car.engineType ?? "",
          storeName: car.storeName ?? "",
          storeId: car.storeId,
          horsepower: car.horsepower,
          engineTorque: car.engineTorque,
          engineSize: car.engineSize,
          horsepowerRpm: car.horsepowerRpm,
          engineTorqueRpm: car.engineTorqueRpm,
        };
      }),
);
