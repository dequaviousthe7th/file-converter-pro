import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Category } from "./types";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Category → brand hue (kept in sync with --color-cat-* tokens). */
export const CATEGORY_COLORS: Record<Category, string> = {
  Documents: "#6ea8fe",
  Images: "#34d399",
  Audio: "#c084fc",
  Video: "#fb923c",
  Data: "#fbbf24",
  Config: "#f472b6",
};

export const CATEGORY_ORDER: Category[] = [
  "Documents",
  "Images",
  "Audio",
  "Video",
  "Data",
  "Config",
];

/** Translucent chip background for a category color. */
export function categoryWash(color: string, pct = 14): string {
  return `color-mix(in srgb, ${color} ${pct}%, transparent)`;
}

export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  if (seconds < 1) return `${Math.max(1, Math.round(seconds * 1000))}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

export function extOf(path: string): string | null {
  const base = path.replace(/[\\/]+$/, "").split(/[\\/]/).pop() ?? "";
  const dot = base.lastIndexOf(".");
  if (dot <= 0 || dot === base.length - 1) return null;
  return base.slice(dot + 1).toLowerCase();
}

export function baseName(path: string): string {
  return path.replace(/[\\/]+$/, "").split(/[\\/]/).pop() ?? path;
}

export function errorMessage(e: unknown): string {
  if (typeof e === "string") return e;
  if (e instanceof Error) return e.message;
  try {
    return JSON.stringify(e);
  } catch {
    return String(e);
  }
}

export function historyOk(status: string): boolean {
  return /^(success|ok|done|completed)$/i.test(status);
}
