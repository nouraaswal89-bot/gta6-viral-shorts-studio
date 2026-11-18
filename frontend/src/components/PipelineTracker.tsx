"use client";

import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Loader2,
  Terminal,
} from "lucide-react";
import type { JobState, PipelineStageId } from "@/lib/types";

interface PipelineTrackerProps {
  job: JobState;
}

const SHORT_STAGE_LABELS: Record<PipelineStageId, string> = {
  ingest: "Stream Ingest",
  ai_director: "AI Clip Select",
  music: "Auto Music",
  beats_captions: "Beats & Captions",
  enhance_fx: "8K HDR & VFX",
  render: "Render 60fps MP4",
};

export const PipelineTracker: React.FC<PipelineTrackerProps> = ({ job }) => {
  return (
    <div className="mx-auto max-w-2xl space-y-5 pt-4">
      {/* Compact Master Progress */}
      <div className="rounded-2xl border border-vice-border/80 bg-vice-panel/95 p-5 shadow-2xl">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h2 className="truncate font-display text-lg font-black text-white">
              {job.stream_metadata?.title || "Processing..."}
            </h2>
            <div className="mt-1 flex items-center gap-2 font-mono text-[11px] text-slate-400">
              <span>{job.num_shorts} Shorts</span>
              <span>•</span>
              <span className="uppercase">{job.status}</span>
            </div>
          </div>

          <div className="font-display text-3xl font-black text-vice-cyan">
            {Math.round(job.overall_progress)}%
          </div>
        </div>

        <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-[#090912]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-vice-pink to-vice-cyan transition-all duration-500"
            style={{
              width: `${Math.min(100, Math.max(3, job.overall_progress))}%`,
            }}
          />
        </div>

        {job.error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-200">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
            <span className="truncate font-mono">{job.error}</span>
          </div>
        )}
      </div>

      {/* Minimal 6-Stage Grid */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {job.stages.map((stage) => {
          const isRunning = stage.status === "running";
          const isDone = stage.status === "completed";
          const isFailed = stage.status === "failed";

          return (
            <div
              key={stage.id}
              className={`rounded-xl border p-3.5 transition ${
                isRunning
                  ? "border-vice-cyan/70 bg-[#14172b] shadow-neon-cyan"
                  : isDone
                  ? "border-emerald-500/35 bg-emerald-950/15"
                  : isFailed
                  ? "border-rose-500/50 bg-rose-950/20"
                  : "border-vice-border/60 bg-vice-panel/60 opacity-60"
              }`}
            >
              <div className="flex items-center justify-between">
                {isDone ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : isRunning ? (
                  <Loader2 className="h-4 w-4 animate-spin text-vice-cyan" />
                ) : isFailed ? (
                  <AlertTriangle className="h-4 w-4 text-rose-400" />
                ) : (
                  <Circle className="h-4 w-4 text-slate-600" />
                )}
                <span className="font-mono text-[11px] font-bold text-slate-300">
                  {Math.round(stage.progress)}%
                </span>
              </div>

              <div className="mt-2.5 text-xs font-bold text-white">
                {SHORT_STAGE_LABELS[stage.id] || stage.label}
              </div>

              <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-black/40">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${
                    isDone
                      ? "bg-emerald-400"
                      : isFailed
                      ? "bg-rose-500"
                      : "bg-gradient-to-r from-vice-pink to-vice-cyan"
                  }`}
                  style={{ width: `${stage.progress}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Collapsible Minimal Logs */}
      {job.logs.length > 0 && (
        <details className="rounded-xl border border-vice-border/70 bg-[#090912] px-4 py-3">
          <summary className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white">
            <Terminal className="h-3.5 w-3.5 text-vice-cyan" />
            Logs ({job.logs.length})
          </summary>
          <div className="mt-3 max-h-36 space-y-1 overflow-y-auto font-mono text-[11px]">
            {job.logs
              .slice()
              .reverse()
              .map((entry, idx) => (
                <div key={`${entry.timestamp}-${idx}`} className="flex gap-2">
                  <span className="shrink-0 text-slate-500">
                    {entry.timestamp}
                  </span>
                  <span
                    className={
                      entry.level === "error"
                        ? "text-rose-400"
                        : entry.level === "success"
                        ? "text-emerald-300"
                        : "text-slate-300"
                    }
                  >
                    {entry.message}
                  </span>
                </div>
              ))}
          </div>
        </details>
      )}
    </div>
  );
};
