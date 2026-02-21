import { For, Show } from "solid-js";
import { SUPPORT_TYPE_CONTENT } from "../supportContent";

type SupportDetailProps = {
  level: string;
};

export function SupportDetail(props: SupportDetailProps) {
  const content = () => SUPPORT_TYPE_CONTENT[props.level];

  return (
    <Show
      when={content()}
      fallback={<p class="text-sm text-muted">No information available for this support level.</p>}
    >
      <div class="flex flex-col gap-3 mb-4">
        <For each={content().paragraphs}>
          {(paragraph) => <p class="text-sm text-secondary leading-relaxed">{paragraph}</p>}
        </For>
      </div>

      <Show when={content().reference}>
        {(ref) => (
          <a
            href={ref().url}
            target="_blank"
            rel="noreferrer"
            class="inline-flex items-center gap-1 text-xs text-accent-bright hover:underline mb-4"
          >
            ↗ {ref().text}
          </a>
        )}
      </Show>

      <Show when={content().expandableContent}>
        {(expandable) => (
          <div class="flex flex-col gap-2 mt-1">
            <For each={expandable().sections}>
              {(section) => (
                <details class="group rounded-sm border border-white/8 overflow-hidden">
                  <Show
                    when={section.title}
                    fallback={
                      <div class="px-3 py-2.5">
                        <For each={section.paragraphs}>
                          {(p) => <p class="text-xs text-secondary leading-relaxed">{p}</p>}
                        </For>
                      </div>
                    }
                  >
                    <summary class="flex items-center justify-between px-3 py-2.5 cursor-pointer
                                    text-xs font-medium text-secondary bg-raised/60
                                    hover:bg-raised hover:text-content transition-colors select-none
                                    list-none [&::-webkit-details-marker]:hidden">
                      {section.title}
                      <span class="text-[10px] text-muted transition-transform group-open:rotate-180">▾</span>
                    </summary>
                    <div class="px-3 py-2.5 border-t border-white/8 flex flex-col gap-2">
                      <For each={section.paragraphs}>
                        {(p) => <p class="text-xs text-secondary leading-relaxed">{p}</p>}
                      </For>
                      <Show when={section.link}>
                        {(link) => (
                          <a
                            href={link().url}
                            target="_blank"
                            rel="noreferrer"
                            class="inline-flex items-center gap-1 text-xs text-accent-bright hover:underline mt-1"
                          >
                            ↗ {link().text}
                          </a>
                        )}
                      </Show>
                    </div>
                  </Show>
                </details>
              )}
            </For>
          </div>
        )}
      </Show>
    </Show>
  );
}
