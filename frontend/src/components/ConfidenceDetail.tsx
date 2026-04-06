import { For } from "solid-js";
import { CONFIDENCE_STYLES } from "./ConfidenceChip";
import { CONFIDENCE_CONTENT } from "../confidenceContent";
import { ConfidenceChip } from "./ConfidenceChip";

const LEVELS = Object.keys(CONFIDENCE_STYLES);

export function ConfidenceDetail() {
  return (
    <div class="flex flex-col gap-3">
      <For each={LEVELS}>
        {(level) => {
          const content = CONFIDENCE_CONTENT[level]!;

          return (
            <div class="rounded-sm border border-white/8 bg-canvas/60 px-4 py-3 flex flex-col gap-2.5">
              <ConfidenceChip level={level} />

              <div class="flex flex-col gap-2">
                <For each={content.paragraphs}>
                  {(paragraph) => (
                    <p class="text-sm text-secondary leading-relaxed">{paragraph}</p>
                  )}
                </For>
              </div>
            </div>
          );
        }}
      </For>
    </div>
  );
}
