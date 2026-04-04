import Drawer from "@corvu/drawer";
import { createSignal, onCleanup, onMount, type JSX } from "solid-js";

type InfoDrawerProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: JSX.Element;
};

const OVERLAY_OPACITY = 0.25;

function createMediaQuery(query: string) {
  const [matches, setMatches] = createSignal(false);

  onMount(() => {
    const mediaQuery = window.matchMedia(query);
    const handleChange = (event: MediaQueryListEvent) => setMatches(event.matches);

    setMatches(mediaQuery.matches);
    mediaQuery.addEventListener("change", handleChange);

    onCleanup(() => mediaQuery.removeEventListener("change", handleChange));
  });

  return matches;
}

export function InfoDrawer(props: InfoDrawerProps) {
  const isDesktop = createMediaQuery("(min-width: 768px)");

  return (
    <Drawer
      open={props.open}
      onOpenChange={(open) => {
        if (!open) props.onClose();
      }}
      side={isDesktop() ? "right" : "bottom"}
      breakPoints={isDesktop() ? [0.97] : [0.85]}
    >
      {(drawerProps) => (
        <Drawer.Portal>
          <Drawer.Overlay
            class="fixed inset-0 z-40
                   data-transitioning:transition-colors
                   data-opening:duration-500 data-opening:ease-[cubic-bezier(0.32,0.72,0,1)]
                   data-closing:duration-200 data-closing:ease-out
                   data-snapping:duration-200 data-snapping:ease-out"
            style={{ "background-color": `rgb(0 0 0 / ${OVERLAY_OPACITY * drawerProps.openPercentage})` }}
          />

          <Drawer.Content
            aria-label={props.title}
            class="fixed z-50 flex flex-col bg-surface border border-white/15 will-change-transform
                   data-transitioning:transition-transform
                   data-opening:duration-300 data-opening:ease-[cubic-bezier(0.32,0.72,0,1)]
                   data-closing:duration-200 data-closing:ease-out
                   data-snapping:duration-200 data-snapping:ease-out"
            classList={{
              "bottom-0 left-0 right-0 rounded-t-lg min-h-[25vh] max-h-[70vh]": !isDesktop(),
              "top-4 bottom-4 right-4 w-[min(380px,calc(100vw-1rem))] rounded-lg": isDesktop(),
            }}
            style={{ "box-shadow": "0 4px 6px -1px rgba(0,0,0,0.08), 0 16px 48px -8px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.08)" }}
          >
            <div class="flex justify-center pt-2.5 pb-1 shrink-0" classList={{ hidden: isDesktop() }}>
              <div class="w-8 h-1 rounded-full bg-raised" />
            </div>

            <div class="flex items-center justify-between px-4 py-3 border-b border-white/8 shrink-0">
              <Drawer.Label class="text-sm font-semibold text-content">{props.title}</Drawer.Label>
              <Drawer.Close
                aria-label="Close"
                class="flex items-center justify-center w-6 h-6 rounded-sm text-muted
                     hover:bg-raised hover:text-content transition-colors border-0 bg-transparent cursor-pointer"
                classList={{ hidden: !isDesktop() }}
              >
                ✕
              </Drawer.Close>
            </div>

            <div class="flex-1 overflow-y-auto px-4 py-4">
              {props.children}
            </div>
          </Drawer.Content>
        </Drawer.Portal>
      )}
    </Drawer>
  );
}
