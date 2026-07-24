import {
  ExternalLink,
  FolderOpen,
  History as HistoryIcon,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import Button from "../components/Button";
import Modal from "../components/Modal";
import * as ipc from "../lib/ipc";
import { useApp } from "../lib/store";
import { cn, formatDuration, historyOk } from "../lib/utils";

export default function History() {
  const history = useApp((s) => s.history);
  const loadHistory = useApp((s) => s.loadHistory);
  const clearAllHistory = useApp((s) => s.clearAllHistory);
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-3 border-b border-hairline px-6 py-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-[15px] font-semibold tracking-tight text-ink">
            History
          </h1>
          <p className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.1em] text-ink-faint">
            {history.length === 0
              ? "No records"
              : `${history.length} record${history.length === 1 ? "" : "s"}`}
          </p>
        </div>
        {history.length > 0 && (
          <Button variant="danger" onClick={() => setConfirmOpen(true)}>
            <Trash2 size={14} />
            Clear All
          </Button>
        )}
      </div>

      {history.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-hairline bg-surface">
            <HistoryIcon size={22} strokeWidth={1.5} className="text-ink-faint" />
          </div>
          <div>
            <p className="text-[13px] font-medium text-ink-dim">
              No conversions yet
            </p>
            <p className="mt-0.5 text-xs text-ink-faint">
              Finished jobs will show up here
            </p>
          </div>
        </div>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          <div className="overflow-hidden rounded-card border border-hairline bg-surface">
            <div className="grid grid-cols-[1.2fr_1.2fr_64px_140px_70px_72px] items-center gap-3 border-b border-hairline px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.1em] text-ink-faint">
              <span>Source</span>
              <span>Output</span>
              <span>Status</span>
              <span>Date</span>
              <span className="text-right">Time</span>
              <span />
            </div>
            {history.map((record, i) => {
              const ok = historyOk(record.status);
              return (
                <div
                  key={`${record.timestamp}-${i}`}
                  className="group grid grid-cols-[1.2fr_1.2fr_64px_140px_70px_72px] items-center gap-3 border-b border-hairline px-4 py-2.5 last:border-b-0 transition-colors hover:bg-white/[0.025]"
                >
                  <span
                    className="truncate text-[13px] text-ink"
                    title={record.source}
                  >
                    {record.sourceName}
                  </span>
                  <span
                    className="truncate text-[13px] text-ink-dim"
                    title={record.output}
                  >
                    {record.outputName}
                  </span>
                  <span
                    className={cn(
                      "inline-flex w-fit items-center rounded-full px-2 py-0.5 font-mono text-[10px] font-bold uppercase",
                      ok
                        ? "bg-accent-soft text-accent"
                        : "bg-danger-soft text-danger",
                    )}
                  >
                    {ok ? "OK" : "Fail"}
                  </span>
                  <span className="truncate text-xs text-ink-faint">
                    {record.datetime}
                  </span>
                  <span className="text-right font-mono text-xs text-ink-faint">
                    {formatDuration(record.duration)}
                  </span>
                  <span className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      type="button"
                      title="Open output"
                      aria-label="Open output"
                      disabled={!ok}
                      className="flex h-7 w-7 items-center justify-center rounded-md text-ink-dim transition-colors hover:bg-white/[0.06] hover:text-ink disabled:pointer-events-none disabled:opacity-30"
                      onClick={() => void ipc.openPath(record.output)}
                    >
                      <ExternalLink size={13} />
                    </button>
                    <button
                      type="button"
                      title="Show in folder"
                      aria-label="Show in folder"
                      disabled={!ok}
                      className="flex h-7 w-7 items-center justify-center rounded-md text-ink-dim transition-colors hover:bg-white/[0.06] hover:text-ink disabled:pointer-events-none disabled:opacity-30"
                      onClick={() => void ipc.revealPath(record.output)}
                    >
                      <FolderOpen size={13} />
                    </button>
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Clear conversion history?"
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              className="bg-danger text-white shadow-none hover:bg-danger/85"
              onClick={() => {
                void clearAllHistory();
                setConfirmOpen(false);
              }}
            >
              Clear All
            </Button>
          </>
        }
      >
        <p className="text-[13px] leading-relaxed text-ink-dim">
          This permanently removes all {history.length} record
          {history.length === 1 ? "" : "s"}. Converted files on disk are not
          touched.
        </p>
      </Modal>
    </div>
  );
}
