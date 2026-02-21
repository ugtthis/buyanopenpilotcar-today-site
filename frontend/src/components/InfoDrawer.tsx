import { createEffect, createSignal, on, onCleanup, onMount, Show, type JSX } from "solid-js";
import { Portal } from "solid-js/web";

type InfoDrawerProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: JSX.Element;
};

const TRANSITION_MS = 300;

function useScrollLock(isLocked: () => boolean) {
  createEffect(() => {
    const scrollRoot = document.documentElement;
    const scrollbarWidth = window.innerWidth - scrollRoot.clientWidth;
    scrollRoot.style.overflow = isLocked() ? "hidden" : "";
    scrollRoot.style.paddingRight = isLocked() ? `${scrollbarWidth}px` : "";
  });
}

export function InfoDrawer(props: InfoDrawerProps) {
  useScrollLock(() => props.open);
  const [viewportIsDesktop, setViewportIsDesktop] = createSignal(
    typeof window !== "undefined" ? window.matchMedia("(min-width: 768px)").matches : false,
  );
  const [activeIsDesktop, setActiveIsDesktop] = createSignal(viewportIsDesktop());
  const [isRendered, setIsRendered] = createSignal(props.open);
  const [isVisible, setIsVisible] = createSignal(false);

  let enterFrame = 0;
  let exitTimer: ReturnType<typeof setTimeout> | undefined;

  onMount(() => {
    const mediaQuery = window.matchMedia("(min-width: 768px)");
    const syncBreakpoint = (matches: boolean) => {
      setViewportIsDesktop(matches);
      if (props.open) props.onClose();
    };

    setViewportIsDesktop(mediaQuery.matches);
    setActiveIsDesktop(mediaQuery.matches);

    const handleChange = (event: MediaQueryListEvent) => syncBreakpoint(event.matches);
    mediaQuery.addEventListener("change", handleChange);

    onCleanup(() => {
      cancelAnimationFrame(enterFrame);
      if (exitTimer) clearTimeout(exitTimer);
      mediaQuery.removeEventListener("change", handleChange);
    });
  });

  createEffect(on(() => props.open, (open) => {
    if (open) {
      if (exitTimer) {
        clearTimeout(exitTimer);
        exitTimer = undefined;
      }

      setIsRendered(true);
      setActiveIsDesktop(viewportIsDesktop());
      cancelAnimationFrame(enterFrame);
      enterFrame = requestAnimationFrame(() => setIsVisible(true));
      return;
    }

    setIsVisible(false);

    exitTimer = setTimeout(() => {
      setIsRendered(false);
      setActiveIsDesktop(viewportIsDesktop());
      exitTimer = undefined;
    }, TRANSITION_MS);
  }, { defer: false }));

  return (
    <Portal>
      <Show when={isRendered()}>
        <div
          class="fixed inset-0 z-40 bg-black/20 transition-opacity duration-300"
          classList={{
            "opacity-100": isVisible(),
            "opacity-0": !isVisible(),
          }}
          onClick={props.onClose}
          aria-hidden="true"
        />

        <div
          role="dialog"
          aria-modal="true"
          aria-label={props.title}
          class="fixed z-50 flex flex-col bg-surface border border-white/15 transition-transform duration-300 ease-in-out"
          classList={{
            "bottom-0 left-0 right-0 rounded-t-lg min-h-[25vh] max-h-[70vh]": !activeIsDesktop(),
            "top-4 bottom-4 right-4 w-[min(380px,calc(100vw-1rem))] rounded-lg": activeIsDesktop(),
            "translate-y-0": isVisible() && !activeIsDesktop(),
            "translate-y-full": !isVisible() && !activeIsDesktop(),
            "translate-x-0": isVisible() && activeIsDesktop(),
            "translate-x-[calc(100%+1rem)]": !isVisible() && activeIsDesktop(),
          }}
          style={{ "box-shadow": "0 4px 6px -1px rgba(0,0,0,0.08), 0 16px 48px -8px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.08)" }}
        >
          <div class="flex justify-center pt-2.5 pb-1 shrink-0" classList={{ hidden: activeIsDesktop() }}>
            <div class="w-8 h-1 rounded-full bg-raised" />
          </div>

          <div class="flex items-center justify-between px-4 py-3 border-b border-white/8 shrink-0">
            <span class="text-sm font-semibold text-content">{props.title}</span>
            <button
              onClick={props.onClose}
              aria-label="Close"
              class="flex items-center justify-center w-6 h-6 rounded-sm text-muted
                   hover:bg-raised hover:text-content transition-colors border-0 bg-transparent"
            >
              ✕
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-4 py-4">
            {props.children}
          </div>
        </div>
      </Show>
    </Portal>
  );
}
