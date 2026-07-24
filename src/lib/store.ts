import {
  isPermissionGranted,
  requestPermission,
  sendNotification,
} from "@tauri-apps/plugin-notification";
import { create } from "zustand";
import * as ipc from "./ipc";
import type {
  FormatInfo,
  HistoryRecord,
  QueueFile,
  Settings,
  ToastItem,
  ViewId,
} from "./types";
import { baseName, errorMessage, extOf, formatDuration } from "./utils";

export const DEFAULT_KNOBS = {
  afterConversion: "ask",
  imageQuality: 85,
  audioBitrate: "192k",
  pdfDpi: 144,
} as const;

interface AppState {
  view: ViewId;
  setView: (view: ViewId) => void;

  formats: FormatInfo[];
  settings: Settings | null;
  history: HistoryRecord[];
  /** One-time app boot: formats + settings. */
  init: () => Promise<void>;
  loadHistory: () => Promise<void>;
  clearAllHistory: () => Promise<void>;
  updateSettings: (patch: Partial<Settings>) => void;

  files: QueueFile[];
  running: boolean;
  addPaths: (paths: string[]) => Promise<void>;
  removeFile: (id: string) => void;
  setTarget: (id: string, target: string) => void;
  applyTargetToCompatible: (id: string) => void;
  convertAll: () => Promise<void>;
  startRow: (id: string) => Promise<void>;
  retryRow: (id: string) => void;
  cancelRow: (id: string) => void;
  cancelEverything: () => void;

  toasts: ToastItem[];
  pushToast: (toast: Omit<ToastItem, "id">) => void;
  dismissToast: (id: string) => void;
}

let booted = false;
let stopRequested = false;
let saveTimer: ReturnType<typeof setTimeout> | null = null;

async function notify(title: string, body: string): Promise<void> {
  let granted = await isPermissionGranted();
  if (!granted) {
    granted = (await requestPermission()) === "granted";
  }
  if (granted) sendNotification({ title, body });
}

export const useApp = create<AppState>()((set, get) => {
  const patchRow = (id: string, patch: Partial<QueueFile>) =>
    set((s) => ({
      files: s.files.map((f) => (f.id === id ? { ...f, ...patch } : f)),
    }));

  const toastError = (title: string, message?: string) =>
    get().pushToast({ kind: "error", title, message, sticky: true });

  /** Post-success side effects for "ask" / "notify" modes ("open_folder" is
   *  handled once per queue run). */
  const onDone = (row: QueueFile, outputs: string[]) => {
    const mode = get().settings?.afterConversion ?? "ask";
    const first = outputs[0];
    if (mode === "ask" && first) {
      get().pushToast({
        kind: "success",
        title: `${row.meta.name} converted`,
        message: baseName(first),
        duration: 10_000,
        actions: [
          { label: "Open File", run: () => void ipc.openPath(first) },
          { label: "Open Folder", run: () => void ipc.revealPath(first) },
        ],
      });
    } else if (mode === "notify") {
      void notify(
        "Conversion complete",
        `${row.meta.name} → ${row.target.toUpperCase()}`,
      ).catch(() => undefined);
    }
  };

  /** Runs one row to a terminal state; resolves with its outputs (null on
   *  failure/cancel). */
  const runRow = (id: string): Promise<string[] | null> => {
    const row = get().files.find((f) => f.id === id);
    if (!row || row.status !== "idle") return Promise.resolve(null);
    patchRow(id, {
      status: "converting",
      pct: 0,
      message: "Starting…",
      outputs: [],
    });
    return new Promise((resolve) => {
      let settled = false;
      const finish = (outputs: string[] | null) => {
        if (!settled) {
          settled = true;
          resolve(outputs);
        }
      };
      ipc
        .startJob(row.path, row.target, (event) => {
          switch (event.state) {
            case "running":
              patchRow(id, { pct: event.pct, message: event.message });
              break;
            case "done":
              patchRow(id, {
                status: "done",
                pct: 100,
                message: `Done in ${formatDuration(event.duration)}`,
                outputs: event.outputs,
                jobId: null,
              });
              onDone(row, event.outputs);
              finish(event.outputs);
              break;
            case "failed":
              patchRow(id, {
                status: "failed",
                message: event.message,
                jobId: null,
              });
              finish(null);
              break;
            case "cancelled":
              patchRow(id, {
                status: "cancelled",
                message: "Cancelled",
                jobId: null,
              });
              finish(null);
              break;
          }
        })
        .then((jobId) => {
          // Guard: terminal events can arrive before the invoke resolves.
          set((s) => ({
            files: s.files.map((f) =>
              f.id === id && f.status === "converting" ? { ...f, jobId } : f,
            ),
          }));
        })
        .catch((e) => {
          patchRow(id, {
            status: "failed",
            message: errorMessage(e),
            jobId: null,
          });
          finish(null);
        });
    });
  };

  /** Sequential queue driver shared by Convert All and single-row runs. */
  const runQueue = async (pickNext: () => QueueFile | undefined) => {
    if (get().running) return;
    stopRequested = false;
    set({ running: true });
    let lastOutput: string | null = null;
    for (;;) {
      if (stopRequested) break;
      const next = pickNext();
      if (!next) break;
      const outputs = await runRow(next.id);
      if (outputs && outputs.length > 0) {
        lastOutput = outputs[outputs.length - 1];
      }
    }
    set({ running: false });
    if (lastOutput && get().settings?.afterConversion === "open_folder") {
      void ipc.revealPath(lastOutput).catch(() => undefined);
    }
  };

  return {
    view: "convert",
    setView: (view) => set({ view }),

    formats: [],
    settings: null,
    history: [],

    init: async () => {
      if (booted) return;
      booted = true;
      const [formats, settings] = await Promise.allSettled([
        ipc.getFormats(),
        ipc.getSettings(),
      ]);
      if (formats.status === "fulfilled") set({ formats: formats.value });
      else toastError("Failed to load formats", errorMessage(formats.reason));
      if (settings.status === "fulfilled") set({ settings: settings.value });
      else toastError("Failed to load settings", errorMessage(settings.reason));
    },

    loadHistory: async () => {
      try {
        set({ history: await ipc.getHistory(200) });
      } catch (e) {
        toastError("Failed to load history", errorMessage(e));
      }
    },

    clearAllHistory: async () => {
      try {
        await ipc.clearHistory();
        set({ history: [] });
      } catch (e) {
        toastError("Failed to clear history", errorMessage(e));
      }
    },

    updateSettings: (patch) => {
      const current = get().settings;
      if (!current) return;
      const next = { ...current, ...patch };
      set({ settings: next });
      if (saveTimer) clearTimeout(saveTimer);
      saveTimer = setTimeout(() => {
        void ipc
          .setSettings(next)
          .catch((e) =>
            toastError("Failed to save settings", errorMessage(e)),
          );
      }, 200);
    },

    files: [],
    running: false,

    addPaths: async (paths) => {
      for (const path of paths) {
        const queued = get().files.some(
          (f) =>
            f.path === path &&
            (f.status === "idle" || f.status === "converting"),
        );
        if (queued) continue;
        try {
          const meta = await ipc.probeFile(path);
          set((s) => ({
            files: [
              ...s.files,
              {
                id: crypto.randomUUID(),
                path,
                meta,
                target: meta.targets[0] ?? "",
                status: "idle",
                pct: 0,
                message: "",
                outputs: [],
                jobId: null,
              },
            ],
          }));
        } catch (e) {
          const ext = extOf(path);
          const detail = errorMessage(e);
          if (ext && /support/i.test(detail)) {
            toastError(`.${ext} files are not supported`);
          } else {
            toastError(`Could not add ${baseName(path)}`, detail);
          }
        }
      }
    },

    removeFile: (id) =>
      set((s) => ({
        files: s.files.filter((f) => f.id !== id || f.status === "converting"),
      })),

    setTarget: (id, target) =>
      set((s) => ({
        files: s.files.map((f) =>
          f.id === id && f.status === "idle" ? { ...f, target } : f,
        ),
      })),

    applyTargetToCompatible: (id) => {
      const row = get().files.find((f) => f.id === id);
      if (!row) return;
      const compatible = get().files.filter(
        (f) =>
          f.id !== id &&
          f.status === "idle" &&
          f.target !== row.target &&
          f.meta.targets.includes(row.target),
      );
      if (compatible.length === 0) {
        get().pushToast({
          kind: "info",
          title: "No other compatible files in the queue",
        });
        return;
      }
      const ids = new Set(compatible.map((f) => f.id));
      set((s) => ({
        files: s.files.map((f) =>
          ids.has(f.id) ? { ...f, target: row.target } : f,
        ),
      }));
      get().pushToast({
        kind: "info",
        title: `${row.target.toUpperCase()} applied to ${compatible.length} more file${compatible.length === 1 ? "" : "s"}`,
      });
    },

    convertAll: () =>
      runQueue(() => get().files.find((f) => f.status === "idle")),

    startRow: (id) => {
      let picked = false;
      return runQueue(() => {
        if (picked) return undefined;
        picked = true;
        return get().files.find((f) => f.id === id && f.status === "idle");
      });
    },

    retryRow: (id) => {
      const row = get().files.find((f) => f.id === id);
      if (!row || (row.status !== "failed" && row.status !== "cancelled")) {
        return;
      }
      patchRow(id, { status: "idle", pct: 0, message: "", outputs: [] });
      if (!get().running) void get().startRow(id);
    },

    cancelRow: (id) => {
      const row = get().files.find((f) => f.id === id);
      if (row?.jobId != null) {
        void ipc.cancelJob(row.jobId).catch(() => undefined);
      }
    },

    cancelEverything: () => {
      stopRequested = true;
      void ipc.cancelAll().catch(() => undefined);
    },

    toasts: [],
    pushToast: (toast) =>
      set((s) => ({
        toasts: [...s.toasts.slice(-4), { ...toast, id: crypto.randomUUID() }],
      })),
    dismissToast: (id) =>
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  };
});
