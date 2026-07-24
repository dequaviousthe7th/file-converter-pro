import { AnimatePresence, MotionConfig, motion } from "motion/react";
import { useEffect } from "react";
import Nav from "./components/Nav";
import Titlebar from "./components/Titlebar";
import Toasts from "./components/Toast";
import { useApp } from "./lib/store";
import Convert from "./views/Convert";
import History from "./views/History";
import SettingsView from "./views/Settings";

export default function App() {
  const view = useApp((s) => s.view);
  const init = useApp((s) => s.init);

  useEffect(() => {
    void init();
  }, [init]);

  return (
    <MotionConfig reducedMotion="user">
      <div className="relative flex h-screen flex-col overflow-hidden bg-bg text-ink">
        {/* atmosphere */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-0"
          style={{
            background:
              "radial-gradient(900px 420px at 30% -10%, rgba(0,212,170,0.05), transparent 60%), radial-gradient(700px 380px at 95% 110%, rgba(110,168,254,0.04), transparent 60%)",
          }}
        />
        <div
          aria-hidden
          className="fcp-noise pointer-events-none absolute inset-0 z-0 opacity-[0.035] mix-blend-overlay"
        />

        <Titlebar />
        <div className="relative z-10 flex min-h-0 flex-1">
          <Nav />
          <main className="relative min-w-0 flex-1 overflow-hidden">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={view}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.16, ease: "easeOut" }}
                className="h-full"
              >
                {view === "convert" ? (
                  <Convert />
                ) : view === "history" ? (
                  <History />
                ) : (
                  <SettingsView />
                )}
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
        <Toasts />
      </div>
    </MotionConfig>
  );
}
