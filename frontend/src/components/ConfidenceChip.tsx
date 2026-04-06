import clsx from "clsx";

export const CONFIDENCE_STYLES: Record<string, { wrap: string; dot: string; label: string }> = {
  extra_high: { wrap: "bg-positive/15 text-positive", dot: "bg-positive",  label: "Extra High" },
  high:       { wrap: "bg-info/15 text-info",          dot: "bg-info",      label: "High"       },
  medium:     { wrap: "bg-hover text-secondary",       dot: "bg-secondary", label: "Medium"     },
  low:        { wrap: "bg-caution/15 text-caution",    dot: "bg-caution",   label: "Low"        },
};

const FALLBACK_STYLE = { wrap: "bg-hover text-secondary", dot: "bg-secondary", label: "—" };

type Props = {
  level: string;
  onClick?: () => void;
};

export function ConfidenceChip(props: Props) {
  const style = () => CONFIDENCE_STYLES[props.level] ?? FALLBACK_STYLE;
  const handleClick = (event: MouseEvent) => {
    if (!props.onClick) return;
    event.stopPropagation();
    props.onClick();
  };

  return (
    <span
      onClick={handleClick}
      class={clsx(
        "inline-flex items-center gap-1 px-1.5 py-0.5 text-[0.8em] font-semibold rounded-sm",
        style().wrap,
        props.onClick &&
          "cursor-pointer hover:ring-1 hover:ring-current transition-[box-shadow,color,background-color] duration-150",
      )}
    >
      <span class={clsx("inline-block w-1 h-1 rounded-full", style().dot)} />
      {style().label}
    </span>
  );
}
