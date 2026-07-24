import { motion } from "motion/react";
import { cn } from "../lib/utils";

export default function Progress({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn(
        "h-1 w-full overflow-hidden rounded-full bg-white/[0.08]",
        className,
      )}
    >
      <motion.div
        className="h-full rounded-full bg-accent shadow-[0_0_8px_rgba(0,212,170,0.5)]"
        initial={false}
        animate={{ width: `${pct}%` }}
        transition={{ type: "spring", stiffness: 180, damping: 28 }}
      />
    </div>
  );
}
