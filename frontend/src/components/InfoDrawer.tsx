import Drawer from "@corvu/drawer";
import clsx from "clsx";
import { createSignal, onCleanup, onMount, type JSX } from "solid-js";

type InfoDrawerProps = {
  open: boolean;
  title: JSX.Element;
  onClose: () => void;
  onClosed?: () => void;
  mobileHeight?: string;
  children: JSX.Element;
};

const OVERLAY_OPACITY = 0.5;
export const INFO_DRAWER_ANIMATION_MS = 500;

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
  let closedTimer: number | undefined;
  onCleanup(() => {
    if (!closedTimer) return;
    window.clearTimeout(closedTimer);
    closedTimer = undefined;
  });

  return (
    <Drawer
      open={props.open}
      onOpenChange={(open) => {
        if (closedTimer) {
          window.clearTimeout(closedTimer);
          closedTimer = undefined;
        }
        if (!open) {
          props.onClose();
          if (props.onClosed) {
            closedTimer = window.setTimeout(() => {
              props.onClosed?.();
              closedTimer = undefined;
            }, INFO_DRAWER_ANIMATION_MS);
          }
        }
      }}
      side={isDesktop() ? "right" : "bottom"}
      breakPoints={isDesktop() ? [0.97] : [0.85]}
    >
      {(drawerProps) => (
        <Drawer.Portal>
          <Drawer.Overlay
            class="fixed inset-0 z-40
                   data-transitioning:transition-colors
                   data-opening:duration-(--info-drawer-animation-ms) data-opening:ease-[cubic-bezier(0.32,0.72,0,1)]
                   data-closing:duration-(--info-drawer-animation-ms) data-closing:ease-out
                   data-snapping:duration-(--info-drawer-animation-ms) data-snapping:ease-out"
            style={{
              "background-color": `rgb(0 0 0 / ${OVERLAY_OPACITY * drawerProps.openPercentage})`,
              "--info-drawer-animation-ms": `${INFO_DRAWER_ANIMATION_MS}ms`,
            }}
          />

          <Drawer.Content
            class={clsx(
              "fixed z-50 flex flex-col bg-surface border border-white/15 will-change-transform",
              "data-transitioning:transition-transform",
              "data-opening:duration-(--info-drawer-animation-ms) data-opening:ease-[cubic-bezier(0.32,0.72,0,1)]",
              "data-closing:duration-(--info-drawer-animation-ms) data-closing:ease-out",
              "data-snapping:duration-(--info-drawer-animation-ms) data-snapping:ease-out",
              isDesktop()
                ? "top-4 bottom-4 right-4 w-[560px] rounded-lg overflow-hidden"
                : "bottom-0 left-0 right-0 rounded-t-lg h-full overflow-visible",
              !isDesktop() && "after:absolute after:inset-x-0 after:top-[calc(100%-1px)] after:h-1/2 after:bg-inherit",
            )}
            style={{
              "box-shadow": "0 4px 6px -1px rgba(0,0,0,0.08), 0 16px 48px -8px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.08)",
              "--info-drawer-animation-ms": `${INFO_DRAWER_ANIMATION_MS}ms`,
              "max-height": isDesktop() ? undefined : (props.mobileHeight ?? "85%"),
            }}
          >
            <div class={clsx("flex justify-center pt-2.5 pb-1 shrink-0", isDesktop() && "hidden")}>
              <div class="w-8 h-1 rounded-full bg-raised" />
            </div>

            <div class="flex items-center justify-between px-4 py-3 border-b border-white/8 shrink-0">
              <Drawer.Label class="text-base font-semibold text-content">{props.title}</Drawer.Label>
              <Drawer.Close
                aria-label="Close"
                class={clsx(
                  "flex items-center justify-center w-6 h-6 rounded-sm text-muted",
                  "hover:bg-raised hover:text-content transition-colors border-0 bg-transparent cursor-pointer",
                  !isDesktop() && "hidden",
                )}
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
