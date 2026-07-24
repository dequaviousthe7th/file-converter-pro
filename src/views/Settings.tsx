import { openUrl } from "@tauri-apps/plugin-opener";
import {
  AudioLines,
  BellRing,
  FileText,
  Folder,
  ExternalLink,
  Image as ImageIcon,
  RotateCcw,
  ScrollText,
} from "lucide-react";
import { motion } from "motion/react";
import { useState, type CSSProperties, type ReactNode } from "react";
import logoUrl from "../assets/logo.png";
import Button from "../components/Button";
import Modal from "../components/Modal";
import * as ipc from "../lib/ipc";
import { DEFAULT_KNOBS, useApp } from "../lib/store";
import type { AfterConversion } from "../lib/types";
import { cn, errorMessage } from "../lib/utils";

const LICENSES = [
  { name: "ffmpeg", license: "GPL-2.0-or-later", role: "Audio, video & HEIC" },
  { name: "pandoc", license: "GPL-2.0-or-later", role: "Document conversion" },
  { name: "typst", license: "Apache-2.0", role: "PDF typesetting" },
  { name: "pdfium", license: "BSD-3-Clause", role: "PDF rendering & text" },
];

function Card({
  icon,
  title,
  description,
  children,
}: {
  icon: ReactNode;
  title: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <section className="rounded-card border border-hairline bg-surface p-5">
      <div className="flex items-start gap-3.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-ctl bg-accent-soft text-accent">
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-[14px] font-semibold text-ink">{title}</h2>
          {description && (
            <p className="mt-0.5 text-xs text-ink-dim">{description}</p>
          )}
          {children && <div className="mt-4">{children}</div>}
        </div>
      </div>
    </section>
  );
}

function Segmented<T extends string | number>({
  id,
  options,
  value,
  onChange,
  render,
}: {
  id: string;
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
  render?: (v: T) => string;
}) {
  return (
    <div className="inline-flex rounded-ctl border border-hairline bg-bg/60 p-0.5">
      {options.map((option) => {
        const active = option === value;
        return (
          <button
            key={String(option)}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option)}
            className={cn(
              "relative rounded-lg px-3.5 py-1.5 font-mono text-xs font-semibold transition-colors",
              active ? "text-accent" : "text-ink-faint hover:text-ink-dim",
            )}
          >
            {active && (
              <motion.span
                layoutId={`seg-${id}`}
                transition={{ type: "spring", stiffness: 500, damping: 38 }}
                className="absolute inset-0 rounded-lg border border-accent/30 bg-accent-soft"
              />
            )}
            <span className="relative">{render ? render(option) : String(option)}</span>
          </button>
        );
      })}
    </div>
  );
}

const AFTER_OPTIONS: {
  value: AfterConversion;
  label: string;
  hint: string;
}[] = [
  {
    value: "ask",
    label: "Ask",
    hint: "Show a toast with Open File / Open Folder actions",
  },
  {
    value: "open_folder",
    label: "Open folder",
    hint: "Reveal the output once the queue finishes",
  },
  {
    value: "notify",
    label: "Notify",
    hint: "Send a system notification per finished file",
  },
];

export default function SettingsView() {
  const settings = useApp((s) => s.settings);
  const updateSettings = useApp((s) => s.updateSettings);
  const pushToast = useApp((s) => s.pushToast);
  const [licensesOpen, setLicensesOpen] = useState(false);

  if (!settings) {
    return (
      <div className="flex h-full items-center justify-center text-[13px] text-ink-faint">
        Loading settings…
      </div>
    );
  }

  const changeOutputDir = async () => {
    try {
      const dir = await ipc.pickFolder();
      if (dir) updateSettings({ outputDir: dir });
    } catch (e) {
      pushToast({
        kind: "error",
        title: "Could not open folder picker",
        message: errorMessage(e),
        sticky: true,
      });
    }
  };

  const qualityFill = `${((settings.imageQuality - 10) / 90) * 100}%`;

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex max-w-2xl flex-col gap-3 px-6 py-6">
        <h1 className="px-1 text-[15px] font-semibold tracking-tight text-ink">
          Settings
        </h1>

        <Card
          icon={<Folder size={17} />}
          title="Output Folder"
          description="Converted files are written here, never overwriting originals."
        >
          <div className="flex items-center gap-3">
            <code className="min-w-0 flex-1 truncate rounded-ctl border border-hairline bg-bg/60 px-3 py-2 font-mono text-xs text-ink-dim">
              {settings.outputDir}
            </code>
            <Button variant="outline" onClick={() => void changeOutputDir()}>
              Change
            </Button>
          </div>
        </Card>

        <Card
          icon={<BellRing size={17} />}
          title="After Conversion"
          description="What happens when a file finishes."
        >
          <div className="flex flex-col gap-1">
            {AFTER_OPTIONS.map((option) => {
              const active = settings.afterConversion === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() =>
                    updateSettings({ afterConversion: option.value })
                  }
                  className={cn(
                    "flex items-center gap-3 rounded-ctl border px-3.5 py-2.5 text-left transition-colors",
                    active
                      ? "border-accent/35 bg-accent-soft"
                      : "border-transparent hover:bg-white/[0.04]",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                      active ? "border-accent" : "border-hairline-strong",
                    )}
                  >
                    {active && (
                      <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                    )}
                  </span>
                  <span className="min-w-0">
                    <span
                      className={cn(
                        "block text-[13px] font-medium",
                        active ? "text-ink" : "text-ink-dim",
                      )}
                    >
                      {option.label}
                    </span>
                    <span className="block text-xs text-ink-faint">
                      {option.hint}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </Card>

        <Card
          icon={<ImageIcon size={17} />}
          title="Image Quality"
          description="JPEG and WebP encode quality."
        >
          <div className="flex items-center gap-4">
            <input
              type="range"
              min={10}
              max={100}
              step={1}
              value={settings.imageQuality}
              aria-label="Image quality"
              className="fcp-range flex-1"
              style={{ "--fill": qualityFill } as CSSProperties}
              onChange={(e) =>
                updateSettings({ imageQuality: Number(e.target.value) })
              }
            />
            <span className="w-12 rounded-md bg-accent-soft py-1 text-center font-mono text-xs font-semibold text-accent">
              {settings.imageQuality}%
            </span>
          </div>
        </Card>

        <Card
          icon={<AudioLines size={17} />}
          title="Audio Bitrate"
          description="Applied to lossy audio targets (MP3, OGG, AAC, M4A, WMA)."
        >
          <Segmented
            id="bitrate"
            options={["128k", "192k", "256k", "320k"] as const}
            value={settings.audioBitrate}
            onChange={(audioBitrate) => updateSettings({ audioBitrate })}
          />
        </Card>

        <Card
          icon={<FileText size={17} />}
          title="PDF Render DPI"
          description="Resolution when rendering PDF pages to images."
        >
          <Segmented
            id="dpi"
            options={[96, 144, 300] as const}
            value={settings.pdfDpi}
            onChange={(pdfDpi) => updateSettings({ pdfDpi })}
            render={(v) => `${v} dpi`}
          />
        </Card>

        <Card
          icon={<RotateCcw size={17} />}
          title="Reset All"
          description="Restore conversion settings to their defaults. The output folder is kept."
        >
          <Button
            variant="outline"
            onClick={() => {
              updateSettings({ ...DEFAULT_KNOBS });
              pushToast({ kind: "info", title: "Settings restored to defaults" });
            }}
          >
            Reset to Defaults
          </Button>
        </Card>

        <section className="mt-2 rounded-card border border-hairline bg-surface p-5">
          <div className="flex items-center gap-3.5">
            <img
              src={logoUrl}
              alt=""
              draggable={false}
              className="h-9 w-9 select-none"
            />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h2 className="text-[14px] font-semibold text-ink">
                  File Converter Pro
                </h2>
                <span className="rounded-full bg-accent-soft px-2 py-0.5 font-mono text-[10px] font-bold text-accent">
                  v3.0.0
                </span>
              </div>
              <p className="mt-0.5 text-xs text-ink-faint">
                Every conversion runs locally. Nothing leaves your machine.
              </p>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 border-t border-hairline pt-4">
            <Button
              size="sm"
              variant="ghost"
              onClick={() =>
                void openUrl("https://github.com/dequaviousthe7th").catch(
                  () => undefined,
                )
              }
            >
              <ExternalLink size={13} />
              dequaviousthe7th
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setLicensesOpen(true)}
            >
              <ScrollText size={13} />
              Open Source Licenses
            </Button>
          </div>
        </section>
      </div>

      <Modal
        open={licensesOpen}
        onClose={() => setLicensesOpen(false)}
        title="Open Source Licenses"
      >
        <p className="text-xs leading-relaxed text-ink-dim">
          File Converter Pro bundles these excellent open source components as
          standalone tools:
        </p>
        <div className="mt-3 flex flex-col gap-2">
          {LICENSES.map((item) => (
            <div
              key={item.name}
              className="flex items-center justify-between gap-3 rounded-ctl border border-hairline bg-bg/50 px-3.5 py-2.5"
            >
              <div className="min-w-0">
                <p className="font-mono text-[13px] font-semibold text-ink">
                  {item.name}
                </p>
                <p className="text-xs text-ink-faint">{item.role}</p>
              </div>
              <span className="shrink-0 rounded-full bg-white/[0.05] px-2.5 py-1 font-mono text-[10px] text-ink-dim">
                {item.license}
              </span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs leading-relaxed text-ink-faint">
          Full license texts ship in the{" "}
          <code className="font-mono text-ink-dim">licenses/</code> directory of
          the installation.
        </p>
      </Modal>
    </div>
  );
}
