"use client";

import React from "react";
import { Film, Plus } from "lucide-react";
import type { BackendHealth } from "@/lib/types";

interface StudioHeaderProps {
  health: BackendHealth | null;
  onReset?: () => void;
  showReset?: boolean;
}

export const StudioHeader: React.FC<StudioHeaderProps> = ({
  health,
  onReset,
  showReset,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-vice-border/60 bg-[#07070d]/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <button
          type="button"
          onClick={onReset}
          className="group flex items-center gap-2.5 text-left"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-vice-pink to-vice-cyan p-[1px]">
            <div className="flex h-full w-full items-center justify-center rounded-[7px] bg-[#0b0b15]">
              <Film className="h-4 w-4 text-vice-cyan" />
            </div>
          </div>
          <span className="font-display text-base font-black tracking-tight text-white">
            GTA6{" "}
            <span className="bg-gradient-to-r from-vice-pink to-vice-cyan bg-clip-text text-transparent">
              SHORTS
            </span>
          </span>
        </button>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-full border border-vice-border/80 bg-vice-panel px-2.5 py-1 text-[11px] font-medium text-slate-300">
            <span
              className={`h-2 w-2 rounded-full ${
                health ? "bg-emerald-400" : "bg-rose-500"
              }`}
            />
            {health ? "Ready" : "Offline"}
          </div>

          {showReset && onReset && (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1.5 rounded-lg border border-vice-border bg-vice-card px-3 py-1.5 text-xs font-semibold text-white transition hover:border-vice-cyan/60"
            >
              <Plus className="h-3.5 w-3.5 text-vice-cyan" />
              New
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
