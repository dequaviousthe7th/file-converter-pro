import { getCurrentWindow } from "@tauri-apps/api/window";
import { Copy, Minus, Square, X } from "lucide-react";
import { useEffect, useState } from "react";
import logoUrl from "../assets/logo.png";
import { cn } from "../lib/utils";

const CONTROL =
  "flex h-full w-[46px] items-center justify-center text-ink-dim transition-colors duration-100 hover:bg-white/[0.06] hover:text-ink";

export default function Titlebar() {
  const [maximized, setMaximized] = useState(false);

  useEffect(() => {
    const win = getCurrentWindow();
    let unlisten: (() => void) | undefined;
    let alive = true;
    void win.isMaximized().then((m) => alive && setMaximized(m));
    void win
      .onResized(() => {
        void win.isMaximized().then((m) => alive && setMaximized(m));
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

  const win = () => getCurrentWindow();

  return (
    <header
      data-tauri-drag-region
      className="relative z-50 flex h-10 shrink-0 items-center border-b border-hairline bg-surface/80"
    >
      <div
        data-tauri-drag-region
        className="flex h-full items-center gap-2.5 pl-3.5"
      >
        <img
          src={logoUrl}
          alt=""
          draggable={false}
          className="pointer-events-none h-[18px] w-[18px] select-none"
        />
        <span
          data-tauri-drag-region
          className="text-[13px] font-medium tracking-wide text-ink-dim"
        >
          File Converter Pro
        </span>
      </div>
      <div data-tauri-drag-region className="h-full flex-1" />
      <div className="flex h-full items-stretch">
        <button
          type="button"
          aria-label="Minimize"
          className={CONTROL}
          onClick={() => void win().minimize()}
        >
          <Minus size={15} strokeWidth={1.5} />
        </button>
        <button
          type="button"
          aria-label={maximized ? "Restore" : "Maximize"}
          className={CONTROL}
          onClick={() => void win().toggleMaximize()}
        >
          {maximized ? (
            <Copy size={13} strokeWidth={1.5} className="-scale-x-100" />
          ) : (
            <Square size={12.5} strokeWidth={1.5} />
          )}
        </button>
        <button
          type="button"
          aria-label="Close"
          className={cn(CONTROL, "hover:bg-[#e81123] hover:text-white")}
          onClick={() => void win().close()}
        >
          <X size={16} strokeWidth={1.5} />
        </button>
      </div>
    </header>
  );
}
