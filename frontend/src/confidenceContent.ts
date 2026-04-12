export type ConfidenceContent = {
  paragraphs: string[];
};

export const CONFIDENCE_CONTENT: Record<string, ConfidenceContent> = {
  extra_high: {
    paragraphs: [
      "As long as it matches the year, make, and model, this car is definitely compatible with openpilot.",
    ],
  },
  high: {
    paragraphs: [
      "Easy to verify car. Usually just confirming if it has LKAS/ACC",
    ],
  },
  medium: {
    paragraphs: [
      "This specific car requires features that are less easy to verify.",
      "May need to confirm with community members on Discord if not confident.",
    ],
  },
  low: {
    paragraphs: [
      "If not experienced, this specific car can be harder to verify correct package because of confusing naming conventions.",
      "May need to confirm with community members on Discord if not confident.",
    ],
  },
};
