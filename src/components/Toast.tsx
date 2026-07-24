import { CircleAlert, CircleCheck, Info, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect } from "react";
import { useApp } from "../lib/store";
import type { ToastItem } from "../lib/types";

const ICONS = {
  success: <CircleCheck size={17} className="shrink-0 text-accent" />,
  error: <CircleAlert size={17} className="shrink-0 text-danger" />,
  info: <Info size={17} className="shrink-0 text-ink-dim" />,
} as const;

function Toast({ toast }: { toast: ToastItem }) {
  const dismiss = useApp((s) => s.dismissToast);

  useEffect(() => {
    if (toast.sticky) return;
    const delay =
      toast.duration ?? (toast.kind === "success" ? 10_000 : 5_000);
    const timer = setTimeout(() => dismiss(toast.id), delay);
    return () => clearTimeout(timer);
  }, [toast, dismiss]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 48, scale: 0.97 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 24, scale: 0.97, transition: { duration: 0.15 } }}
      transition={{ type: "spring", stiffness: 420, damping: 32 }}
      className="pointer-events-auto w-[340px] rounded-card border border-hairline bg-raised/95 p-3.5 shadow-pop backdrop-blur-md"
    >
      <div className="flex items-start gap-2.5">
        <div className="mt-px">{ICONS[toast.kind]}</div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-medium text-ink">
            {toast.title}
          </p>
          {toast.message && (
            <p className="mt-0.5 break-words text-xs leading-snug text-ink-dim">
              {toast.message}
            </p>
          )}
          {toast.actions && toast.actions.length > 0 && (
            <div className="mt-2.5 flex gap-2">
              {toast.actions.map((action) => (
                <button
                  key={action.label}
                  type="button"
                  className="rounded-md bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent transition-colors hover:bg-accent hover:text-[#08110e]"
                  onClick={() => {
                    action.run();
                    dismiss(toast.id);
                  }}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          type="button"
          aria-label="Dismiss"
          className="-m-1 rounded-md p-1 text-ink-faint transition-colors hover:bg-white/[0.06] hover:text-ink"
          onClick={() => dismiss(toast.id)}
        >
          <X size={14} />
        </button>
      </div>
    </motion.div>
  );
}

export default function Toasts() {
  const toasts = useApp((s) => s.toasts);
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[70] flex flex-col items-end gap-2">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <Toast key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  );
}
