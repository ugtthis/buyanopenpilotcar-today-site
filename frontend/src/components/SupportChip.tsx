export const SUPPORT_LEVEL_STYLES: Record<string, { wrap: string; dot: string }> = {
  upstream:         { wrap: "bg-positive/15 text-positive", dot: "bg-positive"  },
  community:        { wrap: "bg-info/15 text-info",          dot: "bg-info"      },
  custom:           { wrap: "bg-caution/15 text-caution",    dot: "bg-caution"   },
  "under review":   { wrap: "bg-caution/15 text-caution",    dot: "bg-caution"   },
  "not compatible": { wrap: "bg-danger/15 text-danger",      dot: "bg-danger"    },
  "dashcam mode":   { wrap: "bg-hover text-secondary",       dot: "bg-secondary" },
};

const FALLBACK_STYLE = { wrap: "bg-hover text-secondary", dot: "bg-secondary" };

type Props = {
  level: string;
  onClick?: () => void;
};

export function SupportChip(props: Props) {
  const style = () => SUPPORT_LEVEL_STYLES[props.level] ?? FALLBACK_STYLE;
  const label = () => props.level.charAt(0).toUpperCase() + props.level.slice(1);
  const handleClick = (event: MouseEvent) => {
    if (!props.onClick) return;
    event.stopPropagation();
    props.onClick();
  };

  return (
    <span
      onClick={handleClick}
      class={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[0.8em] font-semibold rounded-sm ${style().wrap}`}
      classList={{ "cursor-pointer hover:opacity-80 transition-opacity": !!props.onClick }}
    >
      <span class={`inline-block w-1 h-1 rounded-full ${style().dot}`} />
      {label()}
    </span>
  );
}
