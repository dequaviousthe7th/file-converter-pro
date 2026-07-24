/** Typed wrappers for every Tauri command in the IPC contract. */

import { Channel, invoke } from "@tauri-apps/api/core";
import type {
  FileMeta,
  FormatInfo,
  HistoryRecord,
  JobEvent,
  Settings,
} from "./types";

export function getFormats(): Promise<FormatInfo[]> {
  return invoke<FormatInfo[]>("get_formats");
}

export function probeFile(path: string): Promise<FileMeta> {
  return invoke<FileMeta>("probe_file", { path });
}

/** Starts a conversion job; `onEvent` receives streamed JobEvents.
 *  Resolves with the jobId (settings are read backend-side). */
export function startJob(
  input: string,
  target: string,
  onEvent: (event: JobEvent) => void,
): Promise<number> {
  const channel = new Channel<JobEvent>();
  channel.onmessage = onEvent;
  return invoke<number>("start_job", { input, target, onEvent: channel });
}

export function cancelJob(jobId: number): Promise<void> {
  return invoke<void>("cancel_job", { jobId });
}

export function cancelAll(): Promise<void> {
  return invoke<void>("cancel_all");
}

export function getSettings(): Promise<Settings> {
  return invoke<Settings>("get_settings");
}

export function setSettings(s: Settings): Promise<void> {
  return invoke<void>("set_settings", { s });
}

export function getHistory(limit: number): Promise<HistoryRecord[]> {
  return invoke<HistoryRecord[]>("get_history", { limit });
}

export function clearHistory(): Promise<void> {
  return invoke<void>("clear_history");
}

export function openPath(path: string): Promise<void> {
  return invoke<void>("open_path", { path });
}

export function revealPath(path: string): Promise<void> {
  return invoke<void>("reveal_path", { path });
}

export function pickFiles(): Promise<string[]> {
  return invoke<string[]>("pick_files");
}

export function pickFolder(): Promise<string | null> {
  return invoke<string | null>("pick_folder");
}
