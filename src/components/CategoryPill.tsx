import type { Category } from "../lib/types";
import { CATEGORY_COLORS, categoryWash } from "../lib/utils";

export default function CategoryPill({
  category,
  count,
}: {
  category: Category;
  count?: number;
}) {
  const color = CATEGORY_COLORS[category];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-hairline px-2.5 py-1 text-[11px] font-medium text-ink-dim"
      style={{ background: categoryWash(color, 7) }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: color, boxShadow: `0 0 6px ${color}` }}
      />
      {category}
      {count !== undefined && (
        <span className="font-mono text-[10px] text-ink-faint">{count}</span>
      )}
    </span>
  );
}
