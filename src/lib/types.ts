/** Mirrors the Tauri IPC contract (serde camelCase). Keep in sync with
 *  crates/engine registry types and src-tauri/src/commands.rs. */

export type Category =
  | "Documents"
  | "Images"
  | "Audio"
  | "Video"
  | "Data"
  | "Config";

export interface FormatInfo {
  ext: string;
  name: string;
  category: Category;
  targets: string[];
  /** Present in the engine registry; unused fields are tolerated. */
  icon?: string;
}

export interface FileMeta {
  ext: string;
  name: string;
  sizeBytes: number;
  sizeLabel: string;
  formatName: string;
  category: Category;
  targets: string[];
}

export type AfterConversion = "ask" | "open_folder" | "notify";

export interface Settings {
  outputDir: string;
  afterConversion: AfterConversion;
  imageQuality: number;
  audioBitrate: string;
  pdfDpi: number;
}

export interface HistoryRecord {
  source: string;
  output: string;
  sourceName: string;
  outputName: string;
  timestamp: number;
  datetime: string;
  status: string;
  duration: number;
}

/** Channel payload from `start_job` — `#[serde(rename_all = "camelCase", tag = "state")]`. */
export type JobEvent =
  | { state: "running"; pct: number; message: string }
  | { state: "done"; outputs: string[]; duration: number }
  | { state: "failed"; message: string; detail: string | null }
  | { state: "cancelled" };

export type RowStatus = "idle" | "converting" | "done" | "failed" | "cancelled";

export interface QueueFile {
  id: string;
  path: string;
  meta: FileMeta;
  target: string;
  status: RowStatus;
  pct: number;
  message: string;
  outputs: string[];
  jobId: number | null;
}

export type ViewId = "convert" | "history" | "settings";

export interface ToastAction {
  label: string;
  run: () => void;
}

export interface ToastItem {
  id: string;
  kind: "success" | "error" | "info";
  title: string;
  message?: string;
  actions?: ToastAction[];
  /** Sticky toasts never auto-dismiss (errors). */
  sticky?: boolean;
  /** Auto-dismiss delay in ms (default: success 10s, info 5s). */
  duration?: number;
}
