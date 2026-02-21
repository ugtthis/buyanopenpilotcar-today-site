export type ConfidenceContent = {
  paragraphs: string[];
};

export const CONFIDENCE_CONTENT: Record<string, ConfidenceContent> = {
  extra_high: {
    paragraphs: [
      "As long as it matches the year, make, and model, this car is defintley compatible with openpilot.",
    ],
  },
  high: {
    paragraphs: [
      "Easy to verify car. Ussually just confirming if it has LKAS/ACC",
    ],
  },
  medium: {
    paragraphs: [
      "This specific car requires features that are less easy to verify.",
      "Triple check the requirements. May need to confirm with community members on Discord if not confident.",
    ],
  },
  low: {
    paragraphs: [
      "If not experienced, this specific car requires features that are hard to verify, or have confusing naming conventions.",
      "May need to confirm with community members on Discord if not confident.",
    ],
  },
};
