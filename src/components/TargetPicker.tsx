import { ArrowRight, Check, ChevronDown, Layers } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useApp } from "../lib/store";
import type { QueueFile } from "../lib/types";
import { cn } from "../lib/utils";

export default function TargetPicker({ row }: { row: QueueFile }) {
  const formats = useApp((s) => s.formats);
  const setTarget = useApp((s) => s.setTarget);
  const applyToCompatible = useApp((s) => s.applyTargetToCompatible);

  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; right: number }>({
    top: 0,
    right: 0,
  });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const nameOf = (ext: string) =>
    formats.find((f) => f.ext === ext)?.name ?? ext.toUpperCase();

  const toggle = () => {
    if (!open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setPos({
        top: rect.bottom + 6,
        right: window.innerWidth - rect.right,
      });
    }
    setOpen((v) => !v);
  };

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const onPointerDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!panelRef.current?.contains(t) && !buttonRef.current?.contains(t)) {
        close();
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", close);
    document.addEventListener("scroll", close, true);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", close);
      document.removeEventListener("scroll", close, true);
    };
  }, [open]);

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={toggle}
        className={cn(
          "flex h-8 items-center gap-1.5 rounded-ctl border border-hairline-strong px-2.5 transition-colors",
          open
            ? "border-accent/50 bg-accent-soft"
            : "hover:border-white/25 hover:bg-white/[0.04]",
        )}
      >
        <ArrowRight size={12} className="text-ink-faint" />
        <span className="font-mono text-xs font-semibold uppercase tracking-wide text-accent">
          {row.target}
        </span>
        <ChevronDown
          size={13}
          className={cn(
            "text-ink-faint transition-transform duration-150",
            open && "rotate-180",
          )}
        />
      </button>

      {createPortal(
        <AnimatePresence>
          {open && (
            <motion.div
              ref={panelRef}
              role="listbox"
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{
                opacity: 0,
                y: -4,
                scale: 0.98,
                transition: { duration: 0.1 },
              }}
              transition={{ type: "spring", stiffness: 500, damping: 34 }}
              style={{ position: "fixed", top: pos.top, right: pos.right }}
              className="z-[55] w-52 overflow-hidden rounded-card border border-hairline bg-raised shadow-pop"
            >
            <div className="max-h-56 overflow-y-auto p-1">
              {row.meta.targets.map((target) => {
                const selected = target === row.target;
                return (
                  <button
                    key={target}
                    type="button"
                    role="option"
                    aria-selected={selected}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left transition-colors",
                      selected ? "bg-accent-soft" : "hover:bg-white/[0.05]",
                    )}
                    onClick={() => {
                      setTarget(row.id, target);
                      setOpen(false);
                    }}
                  >
                    <span
                      className={cn(
                        "w-11 shrink-0 font-mono text-xs font-semibold uppercase",
                        selected ? "text-accent" : "text-ink",
                      )}
                    >
                      {target}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-xs text-ink-dim">
                      {nameOf(target)}
                    </span>
                    {selected && (
                      <Check size={13} className="shrink-0 text-accent" />
                    )}
                  </button>
                );
              })}
            </div>
            <button
              type="button"
              className="flex w-full items-center gap-2 border-t border-hairline px-3.5 py-2.5 text-xs font-medium text-ink-dim transition-colors hover:bg-white/[0.05] hover:text-accent"
              onClick={() => {
                applyToCompatible(row.id);
                setOpen(false);
              }}
            >
              <Layers size={13} />
              Apply to all compatible
            </button>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body,
      )}
    </>
  );
}
