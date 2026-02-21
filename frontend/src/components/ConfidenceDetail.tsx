import { For, Show } from "solid-js";
import { CONFIDENCE_CONTENT } from "../confidenceContent";

type ConfidenceDetailProps = {
  level: string;
};

export function ConfidenceDetail(props: ConfidenceDetailProps) {
  const content = () => CONFIDENCE_CONTENT[props.level];

  return (
    <Show
      when={content()}
      fallback={<p class="text-sm text-muted">No information available for this confidence level.</p>}
    >
      <div class="flex flex-col gap-3">
        <For each={content().paragraphs}>
          {(paragraph) => <p class="text-sm text-secondary leading-relaxed">{paragraph}</p>}
        </For>
      </div>
    </Show>
  );
}
