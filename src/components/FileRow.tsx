import {
  CircleAlert,
  CircleCheck,
  ExternalLink,
  FolderOpen,
  RotateCcw,
  Square,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import * as ipc from "../lib/ipc";
import { useApp } from "../lib/store";
import type { QueueFile } from "../lib/types";
import { CATEGORY_COLORS, categoryWash, cn } from "../lib/utils";
import Button from "./Button";
import Progress from "./Progress";
import TargetPicker from "./TargetPicker";

const SPRING = { type: "spring", stiffness: 420, damping: 32 } as const;

function StatusArea({ row }: { row: QueueFile }) {
  const removeFile = useApp((s) => s.removeFile);
  const retryRow = useApp((s) => s.retryRow);
  const cancelRow = useApp((s) => s.cancelRow);

  const removeButton = (
    <button
      type="button"
      aria-label={`Remove ${row.meta.name}`}
      className="flex h-7 w-7 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-danger-soft hover:text-danger"
      onClick={() => removeFile(row.id)}
    >
      <X size={14} />
    </button>
  );

  switch (row.status) {
    case "idle":
      return (
        <div className="flex items-center gap-2">
          <TargetPicker row={row} />
          {removeButton}
        </div>
      );
    case "converting":
      return (
        <div className="flex items-center gap-3">
          <Progress value={row.pct} className="w-36" />
          <span className="w-9 text-right font-mono text-xs text-ink-dim">
            {row.pct}%
          </span>
          <Button size="sm" variant="danger" onClick={() => cancelRow(row.id)}>
            <Square size={11} fill="currentColor" />
            Cancel
          </Button>
        </div>
      );
    case "done":
      return (
        <div className="flex items-center gap-2">
          <CircleCheck size={16} className="mr-1 text-accent" />
          <Button
            size="sm"
            variant="outline"
            disabled={row.outputs.length === 0}
            onClick={() => void ipc.openPath(row.outputs[0])}
          >
            <ExternalLink size={12} />
            Open
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={row.outputs.length === 0}
            onClick={() => void ipc.revealPath(row.outputs[0])}
          >
            <FolderOpen size={12} />
            Show in Folder
          </Button>
          {removeButton}
        </div>
      );
    case "failed":
      return (
        <div className="flex items-center gap-2">
          <CircleAlert size={16} className="mr-1 text-danger" />
          <Button size="sm" variant="outline" onClick={() => retryRow(row.id)}>
            <RotateCcw size={12} />
            Retry
          </Button>
          {removeButton}
        </div>
      );
    case "cancelled":
      return (
        <div className="flex items-center gap-2">
          <span className="text-xs text-ink-faint">Cancelled</span>
          <Button size="sm" variant="outline" onClick={() => retryRow(row.id)}>
            <RotateCcw size={12} />
            Retry
          </Button>
          {removeButton}
        </div>
      );
  }
}

export default function FileRow({ row }: { row: QueueFile }) {
  const color = CATEGORY_COLORS[row.meta.category];

  const subline = (() => {
    switch (row.status) {
      case "converting":
        return <span className="text-accent">{row.message}</span>;
      case "done":
        return <span className="text-ink-dim">{row.message}</span>;
      case "failed":
        return (
          <span className="text-danger" title={row.message}>
            {row.message}
          </span>
        );
      case "cancelled":
        return <span className="text-ink-faint">Cancelled</span>;
      default:
        return (
          <span className="text-ink-faint">
            {row.meta.formatName} · {row.meta.sizeLabel}
          </span>
        );
    }
  })();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10, scale: 0.99 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: -16, transition: { duration: 0.12 } }}
      transition={SPRING}
      className={cn(
        "flex items-center gap-3.5 rounded-card border border-hairline bg-surface px-4 py-3 transition-colors",
        row.status === "converting" && "border-accent/25",
        row.status === "failed" && "border-danger/25",
      )}
    >
      <div
        aria-hidden
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-ctl font-mono text-[11px] font-bold uppercase tracking-tight"
        style={{
          color,
          background: categoryWash(color),
          border: `1px solid ${categoryWash(color, 30)}`,
        }}
      >
        {row.meta.ext}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-medium text-ink">
          {row.meta.name}
        </p>
        <p className="mt-0.5 truncate text-xs">{subline}</p>
      </div>
      <div className="shrink-0">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={row.status}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6, transition: { duration: 0.1 } }}
            transition={SPRING}
          >
            <StatusArea row={row} />
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
