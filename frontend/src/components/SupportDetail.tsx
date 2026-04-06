import { For, Show } from "solid-js";
import { SUPPORT_LEVEL_STYLES } from "./SupportChip";
import { SUPPORT_TYPE_CONTENT } from "../supportContent";
import { SupportChip } from "./SupportChip";

const LEVELS = Object.keys(SUPPORT_LEVEL_STYLES);

export function SupportDetail() {
  return (
    <div class="flex flex-col gap-3">
      <For each={LEVELS}>
        {(level) => {
          const content = SUPPORT_TYPE_CONTENT[level]!;

          return (
            <div class="rounded-sm border border-white/8 bg-canvas/60 px-4 py-3 flex flex-col gap-2.5">
              <SupportChip level={level} />

              <div class="flex flex-col gap-2">
                <For each={content.paragraphs}>
                  {(paragraph) => (
                    <p class="text-sm text-secondary leading-relaxed">{paragraph}</p>
                  )}
                </For>
              </div>

              <Show when={content.reference}>
                {(ref) => (
                  <a
                    href={ref().url}
                    target="_blank"
                    rel="noreferrer"
                    class="inline-flex items-center gap-1 text-xs text-accent-bright hover:underline"
                  >
                    ↗ {ref().text}
                  </a>
                )}
              </Show>

              <Show when={content.expandableContent}>
                {(expandable) => (
                  <div class="flex flex-col gap-2 mt-0.5">
                    <For each={expandable().sections}>
                      {(section) => (
                        <details class="group rounded-sm border border-white/8 overflow-hidden">
                          <summary class="flex items-center justify-between px-3 py-2.5 cursor-pointer
                                          text-xs font-medium text-secondary bg-raised/60
                                          hover:bg-raised hover:text-content transition-colors select-none list-none">
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
                        </details>
                      )}
                    </For>
                  </div>
                )}
              </Show>
            </div>
          );
        }}
      </For>
    </div>
  );
}
