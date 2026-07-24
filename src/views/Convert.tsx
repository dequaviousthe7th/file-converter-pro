import { getCurrentWebview } from "@tauri-apps/api/webview";
import { FilePlus2, Plus, RefreshCw, Square } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import Button from "../components/Button";
import DropZone from "../components/DropZone";
import FileRow from "../components/FileRow";
import * as ipc from "../lib/ipc";
import { useApp } from "../lib/store";
import { errorMessage } from "../lib/utils";

export default function Convert() {
  const files = useApp((s) => s.files);
  const running = useApp((s) => s.running);
  const addPaths = useApp((s) => s.addPaths);
  const convertAll = useApp((s) => s.convertAll);
  const cancelEverything = useApp((s) => s.cancelEverything);
  const pushToast = useApp((s) => s.pushToast);

  const [dragging, setDragging] = useState(false);
  const lastDrop = useRef({ sig: "", t: 0 });

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let alive = true;
    void getCurrentWebview()
      .onDragDropEvent((event) => {
        const payload = event.payload;
        if (payload.type === "enter" || payload.type === "over") {
          setDragging(true);
        } else if (payload.type === "leave") {
          setDragging(false);
        } else if (payload.type === "drop") {
          setDragging(false);
          // Dedupe duplicate drop events fired within 100ms (Tauri #14134).
          const sig = payload.paths.join("\n");
          const now = Date.now();
          if (
            sig === lastDrop.current.sig &&
            now - lastDrop.current.t < 100
          ) {
            return;
          }
          lastDrop.current = { sig, t: now };
          void useApp.getState().addPaths(payload.paths);
        }
      })
      .then((fn) => {
        if (alive) unlisten = fn;
        else fn();
      });
    return () => {
      alive = false;
      unlisten?.();
    };
  }, []);

  const browse = async () => {
    try {
      const paths = await ipc.pickFiles();
      if (paths.length > 0) await addPaths(paths);
    } catch (e) {
      pushToast({
        kind: "error",
        title: "Could not open file picker",
        message: errorMessage(e),
        sticky: true,
      });
    }
  };

  const idleCount = files.filter((f) => f.status === "idle").length;
  const doneCount = files.filter((f) => f.status === "done").length;

  return (
    <div className="relative flex h-full flex-col">
      {files.length === 0 ? (
        <DropZone onBrowse={() => void browse()} />
      ) : (
        <>
          <div className="flex shrink-0 items-center gap-3 border-b border-hairline px-6 py-4">
            <div className="min-w-0 flex-1">
              <h1 className="text-[15px] font-semibold tracking-tight text-ink">
                Queue
              </h1>
              <p className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.1em] text-ink-faint">
                {files.length} file{files.length === 1 ? "" : "s"}
                {doneCount > 0 && ` · ${doneCount} done`}
              </p>
            </div>
            <Button variant="outline" onClick={() => void browse()}>
              <Plus size={14} />
              Add Files
            </Button>
            {running ? (
              <Button variant="danger" onClick={cancelEverything}>
                <Square size={12} fill="currentColor" />
                Cancel All
              </Button>
            ) : (
              <Button
                variant="primary"
                disabled={idleCount === 0}
                onClick={() => void convertAll()}
              >
                <RefreshCw size={14} />
                Convert All
                {idleCount > 0 && (
                  <span className="font-mono text-xs opacity-70">
                    {idleCount}
                  </span>
                )}
              </Button>
            )}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
            <div className="flex flex-col gap-2">
              <AnimatePresence initial={false} mode="popLayout">
                {files.map((row) => (
                  <FileRow key={row.id} row={row} />
                ))}
              </AnimatePresence>
            </div>
          </div>
        </>
      )}

      <AnimatePresence>
        {dragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="pointer-events-none fixed inset-0 z-40 bg-bg/80 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.985 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 26 }}
              className="absolute inset-5 top-[60px] flex items-center justify-center rounded-2xl border-2 border-dashed border-accent bg-accent-soft/40"
            >
              <div className="flex flex-col items-center gap-3">
                <FilePlus2 size={34} strokeWidth={1.5} className="text-accent" />
                <p className="text-base font-semibold text-ink">
                  Drop to add files
                </p>
                <p className="text-[13px] text-ink-dim">
                  They&rsquo;ll join the queue
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
