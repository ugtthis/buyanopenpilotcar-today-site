import type { CarListing, MatchConfidence, SupportLevel, SupportSpecs } from "./types";
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

type RawSupportSpecs = {
  longitudinal: string;
  fsr_longitudinal: string;
  fsr_steering: string;
  experimental_longitudinal_available: boolean;
  openpilot_longitudinal_control: boolean;
  steering_torque: string;
  auto_resume_star: string;
};

type RawEntry = {
  make: string;
  model: string;
  model_original: string;
  support_specs: RawSupportSpecs;
  package_requirements: string;
  support_level: { type: string };
  available_years: RawYear[];
};

type RawJson = { entries: RawEntry[]; generated_at: string };

const data = rawJson as RawJson;

export const generatedAt = data.generated_at;

// Flatten entries[].available_years[].car into one row per listing
export const cars: CarListing[] = data.entries.flatMap(
  (entry) =>
    entry.available_years
      .filter((ay): ay is RawYear & { car: RawCar } => ay.car !== null)
      .map((ay) => {
        const car = ay.car;
        const supportSpecs: SupportSpecs = {
          longitudinal: entry.support_specs.longitudinal,
          fsrLongitudinal: entry.support_specs.fsr_longitudinal,
          fsrSteering: entry.support_specs.fsr_steering,
          experimentalLongitudinalAvailable: entry.support_specs.experimental_longitudinal_available,
          openpilotLongitudinalControl: entry.support_specs.openpilot_longitudinal_control,
          steeringTorque: entry.support_specs.steering_torque,
          autoResumeStar: entry.support_specs.auto_resume_star,
        };

        return {
          stockNumber: car.stockNumber,
          make: entry.make,
          model: entry.model,
          modelOriginal: entry.model_original,
          supportSpecs,
          packageRequirements: entry.package_requirements ?? "",
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
