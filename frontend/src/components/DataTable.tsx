import {
  createSolidTable,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
} from "@tanstack/solid-table";
import type { ColumnDef, SortingState, VisibilityState } from "@tanstack/solid-table";
import clsx from "clsx";
import { createEffect, createSignal, For, on, Show, untrack, type JSX } from "solid-js";
import type { DataTableProps } from "../types";
import { DensityComfortableIcon, DensityNormalIcon } from "./Icons";

type RowDensity = "normal" | "comfortable";

const DENSITIES: RowDensity[] = ["normal", "comfortable"];
const UNKNOWN_RANK = 99;

const COLUMN_SORT_RANK: Partial<Record<string, Record<string, number>>> = {
  matchConfidence: { extra_high: 0, high: 1, medium: 2, low: 3 },
  supportLevel:    { upstream: 0, community: 1, custom: 2, "under review": 3, "dashcam mode": 4, "not compatible": 5 },
};

const DENSITY_CONFIG: Record<RowDensity, {
  cellPy: string; headPy: string; textSize: string; label: string; icon: () => JSX.Element;
}> = {
  normal:      { cellPy: "py-1.5", headPy: "py-2", textSize: "text-xs",   label: "Normal",      icon: () => <DensityNormalIcon /> },
  comfortable: { cellPy: "py-3",   headPy: "py-3", textSize: "text-base", label: "Comfortable", icon: () => <DensityComfortableIcon /> },
};


const BpBtn = (props: { onClick: () => void; disabled: boolean; children: string }) => (
  <button
    onClick={props.onClick}
    disabled={props.disabled}
    class="min-w-12 h-11 px-4 text-base font-medium rounded-sm border border-white/15 bg-panel
           text-secondary select-none transition-colors
           hover:bg-hover hover:text-content cursor-pointer
           disabled:opacity-30 disabled:cursor-not-allowed"
  >
    {props.children}
  </button>
);

export function DataTable<T extends object>(props: DataTableProps<T>) {
  const globalFilter = () => props.searchQuery;
  const setGlobalFilter = props.onSearchChange;
  const [sorting, setSorting] = createSignal<SortingState>([{ id: "car", desc: false }]);
  const [columnVisibility, setColumnVisibility] = createSignal<VisibilityState>({});
  // Distance column visibility is always derived from the prop — never stored in signal state.
  // This means TanStack always reads the ground truth directly; no sync needed.
  const effectiveColumnVisibility = () => ({ ...columnVisibility(), distance: props.distanceActive ?? false });

  createEffect(() => {
    if (props.distanceActive) {
      setSorting([{ id: "distance", desc: false }]);
    } else {
      // If sort is still on distance when zip is cleared, the user never changed it manually —
      // reset to make so the list has an obvious order. Otherwise leave their sort alone.
      const s = untrack(sorting); // read without subscribing — this effect should only react to distanceActive, not to user sort changes
      if (s.length === 1 && s[0].id === "distance") setSorting([{ id: "car", desc: false }]);
    }
  });
  const isMobile = typeof window !== "undefined" && !window.matchMedia("(min-width: 640px)").matches;
  const [density, setDensity] = createSignal<RowDensity>(isMobile ? "comfortable" : "normal");
  const densityIndex = () => DENSITIES.indexOf(density());
  const handleDensityClick = (densityOption: RowDensity) => {
    setDensity((current) => {
      if (current !== densityOption) return densityOption;
      const nextIndex = (DENSITIES.indexOf(current) + 1) % DENSITIES.length;
      return DENSITIES[nextIndex];
    });
  };
  const hasActiveSearch = () => globalFilter().trim().length > 0;

  const rankSort = (rankMap: Record<string, number>) =>
    (rowA: { getValue: (id: string) => unknown }, rowB: { getValue: (id: string) => unknown }, id: string) =>
      (rankMap[String(rowA.getValue(id))] ?? UNKNOWN_RANK) -
      (rankMap[String(rowB.getValue(id))] ?? UNKNOWN_RANK);

  const columnDefs = (): ColumnDef<T>[] =>
    props.columns.map((col) => {
      const id = (col.key ?? col.id)!;
      const rank = COLUMN_SORT_RANK[id];
      const accessor = col.accessorFn
        ? { id: col.id, accessorFn: col.accessorFn }
        : { accessorKey: col.key };
      return {
        ...accessor,
        header: col.header,
        cell: (info) =>
          col.render
            ? col.render(info.getValue(), info.row.original)
            : String(info.getValue() ?? ""),
        ...(rank ? { sortingFn: rankSort(rank) } : {}),
      };
    });

  const table = createSolidTable<T>({
    get data() { return props.data; },
    get columns() { return columnDefs(); },
    state: {
      get globalFilter() { return globalFilter(); },
      get sorting() { return sorting(); },
      get columnVisibility() { return effectiveColumnVisibility(); },
    },
    initialState: {
      pagination: { pageSize: props.pageSize ?? 30, pageIndex: 0 },
    },
    globalFilterFn: "includesString",
    onGlobalFilterChange: setGlobalFilter,
    onSortingChange: setSorting,
    onColumnVisibilityChange: setColumnVisibility,
    enableSortingRemoval: false,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  // TanStack's autoResetPageIndex relies on React's render-cycle diffing; SolidJS needs an explicit effect.
  const autoResetPageIndex = () => table.setPageIndex(0);
  createEffect(on(() => [globalFilter(), props.data] as const, autoResetPageIndex, { defer: true }));

  const totalFiltered = () => table.getFilteredRowModel().rows.length;
  const totalAll = () => props.data.length;
  const pagedRows = () => table.getRowModel().rows;
  const isEmpty = () => totalFiltered() === 0;
  const isSearchEmpty = () => hasActiveSearch() && isEmpty();
  const pageSize = () => table.getState().pagination.pageSize;
  const pageIdx = () => table.getState().pagination.pageIndex;
  const pageStart = () => (isEmpty() ? 0 : pageIdx() * pageSize() + 1);
  const pageEnd = () => (isEmpty() ? 0 : Math.min(pageStart() + pageSize() - 1, totalFiltered()));
  const handleRowClick = (event: MouseEvent, row: T) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.closest("a, button, input, select, textarea")) return;
    props.onRowClick?.(row);
  };

  return (
    <div class="flex flex-col gap-2">

      {/* ── Table controls ── */}
      <div class="flex items-end gap-2 flex-wrap pb-2">

        {/* Object count */}
        <div class="text-md text-muted tabular-nums whitespace-nowrap">
          <Show when={globalFilter()} fallback={
            <span><strong class="text-secondary">{totalAll().toLocaleString()}</strong> cars</span>
          }>
            <span><strong class="text-secondary">{totalFiltered().toLocaleString()}</strong> of {totalAll().toLocaleString()} cars</span>
          </Show>
        </div>

        {/* Legend slot + Row density toggle */}
        <div class="flex items-center gap-2 ml-auto">
          {props.legendSlot}
          <div class="relative flex items-center rounded-sm border border-white/15 bg-panel overflow-hidden">
            {/* Sliding indicator */}
            <div
              class="absolute inset-y-0 left-0 bg-raised shadow-[inset_0_0_0_1px_rgba(255,255,255,0.15)] pointer-events-none"
              style={{
                width: `${100 / DENSITIES.length}%`,
                transform: `translateX(${densityIndex() * 100}%)`,
                transition: "transform 150ms ease",
              }}
            />
            <For each={DENSITIES}>
              {(densityOption) => (
                <button
                  onClick={() => handleDensityClick(densityOption)}
                  title={DENSITY_CONFIG[densityOption].label}
                  class={clsx(
                    "relative z-10 flex items-center justify-center w-10 py-2.5 border-0 bg-transparent",
                    "transition-colors duration-150 cursor-pointer",
                    density() === densityOption ? "text-content" : "text-muted hover:text-secondary",
                  )}
                  aria-pressed={density() === densityOption}
                >
                  {DENSITY_CONFIG[densityOption].icon()}
                </button>
              )}
            </For>
          </div>
        </div>

      </div>

      {/* ── Table ── */}
      <div class="overflow-x-auto rounded-sm border border-white/8 bp-elevation-1">
        <Show
          when={!isEmpty()}
          fallback={
            <div class="flex min-h-64 flex-col items-center justify-center gap-3 bg-surface px-4 py-10 text-center sm:px-6">
              <div
                class={clsx(
                  "text-[11px] font-semibold uppercase tracking-[0.18em]",
                  isSearchEmpty() ? "text-danger" : "text-muted",
                )}
              >
                {isSearchEmpty() ? "No matches found" : "No cars available"}
              </div>
              <div class="max-w-full wrap-break-word text-balance text-lg font-semibold text-content">
                {isSearchEmpty() ? `No cars match "${globalFilter().trim()}".` : "There are no cars to display right now."}
              </div>
              <p class="max-w-md text-sm leading-6 text-secondary">
                {isSearchEmpty()
                  ? "Try a different make, model, trim, or state, or clear the search to see everything again."
                  : "Try again in a moment or adjust the current filters."}
              </p>
              <Show when={isSearchEmpty()}>
                <button
                  onClick={() => setGlobalFilter("")}
                  class="mt-1 inline-flex min-h-9 max-w-full items-center justify-center rounded-sm border border-white/15 bg-panel px-4 py-2 text-center text-sm font-medium text-secondary transition-colors hover:bg-hover hover:text-content cursor-pointer"
                >
                  Clear search
                </button>
              </Show>
            </div>
          }
        >
          <table class={clsx("w-max min-w-full text-left border-collapse", DENSITY_CONFIG[density()].textSize)}>
            <thead>
              <For each={table.getHeaderGroups()}>
                {(headerGroup) => (
                  <tr class="bg-panel border-b border-white/15">
                    <For each={headerGroup.headers}>
                      {(header) => (
                        <th
                          class={clsx(
                            "px-3 h-16 align-middle text-[1.15em] font-semibold select-none transition-colors",
                            DENSITY_CONFIG[density()].headPy,
                            header.column.getCanSort() && "hover:bg-raised cursor-pointer",
                            header.column.getIsSorted() ? "text-accent-bright" : "text-secondary",
                          )}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          <Show when={!header.isPlaceholder}>
                            <span class="flex items-center gap-0.5 leading-tight whitespace-nowrap">
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              <Show when={header.column.getIsSorted()}>
                                {(dir) => (
                                  <span class="ml-1 inline-flex w-[1em] justify-center text-[0.8em] opacity-60 select-none">
                                    {dir() === "asc" ? "↑" : "↓"}
                                  </span>
                                )}
                              </Show>
                            </span>
                          </Show>
                        </th>
                      )}
                    </For>
                  </tr>
                )}
              </For>
            </thead>
            <tbody>
              <For each={pagedRows()}>
                {(row, i) => {
                  const selected = () => props.isRowSelected?.(row.original) ?? false;
                  return (
                    <tr
                      class={clsx(
                        "group transition-colors cursor-pointer",
                        selected()
                          ? "bg-accent/25"
                          : i() % 2 === 0
                            ? "bg-canvas hover:bg-accent/8"
                            : "bg-white/60 hover:bg-accent/8",
                      )}
                      onClick={(event) => handleRowClick(event, row.original)}
                    >
                      <For each={row.getVisibleCells()}>
                        {(cell) => (
                          <td
                            class={clsx(
                              "px-3 whitespace-nowrap tabular-nums transition-colors",
                              DENSITY_CONFIG[density()].cellPy,
                              selected() ? "text-content" : "text-secondary group-hover:text-content",
                            )}
                          >
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </td>
                        )}
                      </For>
                    </tr>
                  );
                }}
              </For>
            </tbody>
          </table>
        </Show>
      </div>

      {/* ── Pagination ── */}
      <div class="flex flex-col-reverse items-center gap-3 pt-3 pb-3 sm:flex-row sm:items-center sm:justify-between">

        <span class="text-md text-muted tabular-nums text-center sm:text-left">
          Showing{" "}
          <strong class="text-secondary">{pageStart().toLocaleString()}–{pageEnd().toLocaleString()}</strong>
          {" "}of{" "}
          <strong class="text-secondary">{totalFiltered().toLocaleString()}</strong> cars
        </span>

        <Show when={!isEmpty()}>
          <div class="flex w-full items-center justify-center gap-2 flex-wrap sm:w-auto">
            {/* Page nav */}
            <div class="flex items-center gap-1.5">
              <BpBtn onClick={() => table.firstPage()}    disabled={!table.getCanPreviousPage()}>⟨⟨</BpBtn>
              <BpBtn onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>⟨</BpBtn>

              <span class="min-w-24 h-11 px-4 inline-flex items-center justify-center text-base rounded-sm border border-white/8 bg-surface text-secondary select-none tabular-nums">
                {pageIdx() + 1}
                <span class="text-muted"> / {table.getPageCount()}</span>
              </span>

              <BpBtn onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>⟩</BpBtn>
              <BpBtn onClick={() => table.lastPage()} disabled={!table.getCanNextPage()}>⟩⟩</BpBtn>
            </div>
          </div>
        </Show>
      </div>
    </div>
  );
}
