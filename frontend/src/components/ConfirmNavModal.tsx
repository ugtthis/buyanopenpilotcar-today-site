import clsx from "clsx";
import { For, Show, createMemo } from "solid-js";
import { Portal } from "solid-js/web";
import { SUPPORT_TYPE_CONTENT } from "../supportContent";
import type { PendingNav } from "../types";
import { SupportChip } from "./SupportChip";

type Props = {
  pending: PendingNav | null;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmNavModal(props: Props) {
  const open = () => props.pending !== null;

  // Hold the last non-null pending so content stays mounted during the exit animation.
  const frozen = createMemo<PendingNav | null>((prev) => props.pending ?? prev, null);

  const content = () => SUPPORT_TYPE_CONTENT[frozen()?.supportLevel ?? ""];

  return (
    <Portal>
      {/* Backdrop */}
      <div
        class={clsx(
          "fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px] transition-opacity duration-200",
          open() ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none",
        )}
        onClick={props.onCancel}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Support level warning"
        class="fixed z-50 inset-0 flex items-center justify-center p-4 pointer-events-none"
      >
        <div
          class={clsx(
            "w-full max-w-md rounded-lg border border-white/15 bg-surface",
            "transition-all duration-200 origin-center",
            open() ? "opacity-100 scale-100 pointer-events-auto" : "opacity-0 scale-95 pointer-events-none",
          )}
          style={{ "box-shadow": "0 4px 6px -1px rgba(0,0,0,0.12), 0 20px 60px -10px rgba(0,0,0,0.4), 0 0 0 1px rgba(0,0,0,0.1)" }}
        >
          {/* Header */}
          <div class="flex items-center justify-between px-5 py-4 border-b border-white/8">
            <div class="flex items-center gap-2.5">
              <span class="text-caution text-base select-none">⚠</span>
              <span class="text-sm font-semibold text-content">Before you continue</span>
            </div>
            <button
              onClick={props.onCancel}
              aria-label="Close"
              class="flex items-center justify-center w-6 h-6 rounded-sm text-muted border-0 bg-transparent
                     hover:bg-raised hover:text-content transition-colors cursor-pointer"
            >
              ✕
            </button>
          </div>

          {/* Body */}
          <div class="px-5 py-4 flex flex-col gap-4">
            {/* Car summary */}
            <Show when={frozen()}>
              {(p) => (
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="text-sm font-semibold text-content leading-snug">
                      {p().year} {p().make} {p().model}
                    </div>
                    <Show when={p().trim}>
                      <div class="text-xs text-muted mt-0.5 truncate">{p().trim}</div>
                    </Show>
                  </div>
                  <SupportChip level={p().supportLevel} />
                </div>
              )}
            </Show>

            {/* Divider */}
            <div class="border-t border-white/8" />

            <span class="text-[10px] font-semibold uppercase tracking-wider text-muted">Support Level Details</span>

            <Show
              when={content()}
              fallback={
                <p class="text-xs text-secondary leading-relaxed">
                  This vehicle has a non-standard support level. Proceed with caution.
                </p>
              }
            >
              {(c) => (
                <div class="flex flex-col gap-2">
                  <For each={c().paragraphs}>
                    {(para) => <p class="text-xs text-secondary leading-relaxed">{para}</p>}
                  </For>
                  <Show when={c().reference}>
                    {(ref) => (
                      <a
                        href={ref().url}
                        target="_blank"
                        rel="noreferrer"
                        class="text-xs text-accent-bright hover:underline self-start"
                      >
                        ↗ {ref().text}
                      </a>
                    )}
                  </Show>
                </div>
              )}
            </Show>
          </div>

          {/* Footer */}
          <div class="flex items-center justify-end gap-2 px-5 py-3 border-t border-white/8">
            <button
              onClick={props.onCancel}
              class="px-3 py-1.5 text-xs font-medium rounded-sm border border-white/15 bg-panel text-secondary
                     hover:bg-raised hover:text-content transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={props.onConfirm}
              class="px-3 py-1.5 text-xs font-medium rounded-sm bg-accent text-white
                     hover:bg-accent-muted transition-colors cursor-pointer"
            >
              Continue to listing ↗
            </button>
          </div>
        </div>
      </div>
    </Portal>
  );
}
