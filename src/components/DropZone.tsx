import { FilePlus2 } from "lucide-react";
import { motion } from "motion/react";
import { useApp } from "../lib/store";
import { CATEGORY_ORDER } from "../lib/utils";
import Button from "./Button";
import CategoryPill from "./CategoryPill";

export default function DropZone({ onBrowse }: { onBrowse: () => void }) {
  const formats = useApp((s) => s.formats);
  const pairCount = formats.reduce((n, f) => n + f.targets.length, 0);
  const counts = new Map<string, number>();
  for (const f of formats) {
    counts.set(f.category, (counts.get(f.category) ?? 0) + 1);
  }

  return (
    <div className="flex h-full items-center justify-center p-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 28 }}
        className="fcp-dots relative w-full max-w-xl rounded-2xl border-2 border-dashed border-hairline-strong bg-surface/40 px-10 py-14 text-center"
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-2xl"
          style={{
            background:
              "radial-gradient(420px 200px at 50% 0%, rgba(0,212,170,0.06), transparent 70%)",
          }}
        />
        <div className="relative flex flex-col items-center">
          <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border border-hairline bg-raised shadow-[0_0_40px_rgba(0,212,170,0.12)]">
            <FilePlus2 size={26} strokeWidth={1.5} className="text-accent" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-ink">
            Drop files to convert
          </h1>
          <p className="mt-1 text-[13px] text-ink-dim">
            Drag anything here, or pick from your machine
          </p>
          <Button variant="primary" className="mt-6" onClick={onBrowse}>
            Browse Files
          </Button>
          {formats.length > 0 && (
            <>
              <div className="mt-8 flex max-w-md flex-wrap justify-center gap-1.5">
                {CATEGORY_ORDER.map((c) =>
                  counts.get(c) ? (
                    <CategoryPill key={c} category={c} count={counts.get(c)} />
                  ) : null,
                )}
              </div>
              <p className="mt-4 font-mono text-[11px] uppercase tracking-[0.14em] text-ink-faint">
                {pairCount} conversion paths · all local
              </p>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
}
