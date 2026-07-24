import { History, RefreshCw, Settings2 } from "lucide-react";
import { motion } from "motion/react";
import { useApp } from "../lib/store";
import type { ViewId } from "../lib/types";
import { cn } from "../lib/utils";

const ITEMS: { id: ViewId; label: string; Icon: typeof RefreshCw }[] = [
  { id: "convert", label: "Convert", Icon: RefreshCw },
  { id: "history", label: "History", Icon: History },
  { id: "settings", label: "Settings", Icon: Settings2 },
];

export default function Nav() {
  const view = useApp((s) => s.view);
  const setView = useApp((s) => s.setView);
  const formats = useApp((s) => s.formats);
  const pairCount = formats.reduce((n, f) => n + f.targets.length, 0);

  return (
    <nav className="flex w-16 shrink-0 flex-col items-center border-r border-hairline bg-surface/50 py-3">
      <div className="flex flex-col items-center gap-1.5">
        {ITEMS.map(({ id, label, Icon }) => {
          const active = view === id;
          return (
            <button
              key={id}
              type="button"
              title={label}
              aria-label={label}
              aria-current={active ? "page" : undefined}
              onClick={() => setView(id)}
              className={cn(
                "relative flex h-10 w-10 items-center justify-center rounded-ctl transition-colors duration-150",
                active
                  ? "text-accent"
                  : "text-ink-faint hover:bg-white/[0.05] hover:text-ink-dim",
              )}
            >
              {active && (
                <motion.span
                  layoutId="nav-active"
                  transition={{ type: "spring", stiffness: 500, damping: 38 }}
                  className="absolute inset-0 rounded-ctl bg-accent-soft"
                />
              )}
              {active && (
                <motion.span
                  layoutId="nav-bar"
                  transition={{ type: "spring", stiffness: 500, damping: 38 }}
                  className="absolute -left-[13px] h-5 w-[2.5px] rounded-r-full bg-accent"
                />
              )}
              <Icon size={19} strokeWidth={1.75} className="relative" />
            </button>
          );
        })}
      </div>
      <div className="flex-1" />
      {pairCount > 0 && (
        <div
          title={`${pairCount} conversion paths`}
          className="flex flex-col items-center gap-0.5 rounded-ctl border border-hairline bg-raised px-1.5 py-1.5"
        >
          <span className="font-mono text-[11px] font-semibold leading-none text-accent">
            {pairCount}
          </span>
          <span className="text-[8.5px] uppercase tracking-[0.08em] leading-none text-ink-faint">
            paths
          </span>
        </div>
      )}
    </nav>
  );
}
