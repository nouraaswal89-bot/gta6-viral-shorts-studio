"use client";

import React, { useMemo, useState } from "react";
import { Player } from "@remotion/player";
import {
  Archive,
  Download,
  Flame,
  Music2,
  Timer,
  Zap,
} from "lucide-react";
import type { JobState, ShortClipData } from "@/lib/types";
import { ViralShortComposition } from "@/remotion/ViralShortComposition";

interface ShortsGalleryPreviewProps {
  job: JobState;
}

export const ShortsGalleryPreview: React.FC<ShortsGalleryPreviewProps> = ({
  job,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [hookOverrides, setHookOverrides] = useState<Record<string, string>>({});

  const activeClipRaw: ShortClipData | undefined =
    job.clips[selectedIndex] || job.clips[0];

  const activeClip = useMemo(() => {
    if (!activeClipRaw) return undefined;
    const customHook = hookOverrides[activeClipRaw.clip_id];
    if (customHook === undefined) return activeClipRaw;
    return { ...activeClipRaw, hook_banner_text: customHook };
  }, [activeClipRaw, hookOverrides]);

  if (!activeClip) return null;

  const durationInFrames = Math.max(
    900,
    Math.round((activeClip.duration || 18) * (activeClip.fps || 60))
  );
  const dropCount = activeClip.beats.filter((b) => b.is_drop).length;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      {/* Compact Export Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-vice-border/80 bg-vice-panel/90 px-5 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
          <span className="font-display text-base font-black text-white">
            {job.clips.length} {job.clips.length === 1 ? "Short" : "Shorts"} Ready
          </span>
          <span className="font-mono text-xs text-slate-400">
            1080×1920 • 60fps
          </span>
        </div>

        <div className="flex items-center gap-2.5">
          {activeClip.rendered_mp4_url && (
            <a
              href={activeClip.rendered_mp4_url}
              download={`GTA6_Short_${activeClip.index}.mp4`}
              className="inline-flex items-center gap-1.5 rounded-xl border border-vice-cyan/45 bg-vice-cyan/10 px-3.5 py-2 text-xs font-bold text-vice-cyan transition hover:bg-vice-cyan/20"
            >
              <Download className="h-3.5 w-3.5" />
              MP4
            </a>
          )}

          {job.zip_download_url && (
            <a
              href={job.zip_download_url}
              download={`GTA6_Shorts_${job.job_id}.zip`}
              className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-vice-pink to-vice-cyan px-4 py-2 text-xs font-black uppercase tracking-wider text-white shadow-neon-pink transition hover:brightness-110"
            >
              <Archive className="h-3.5 w-3.5" />
              Download All (.ZIP)
            </a>
          )}
        </div>
      </div>

      {/* Clean 3-Column Studio Grid */}
      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        {/* Left: Compact Clip Switcher */}
        <div className="max-h-[680px] space-y-2 overflow-y-auto pr-1 lg:col-span-4">
          {job.clips.map((clip, idx) => {
            const isSelected = idx === selectedIndex;
            return (
              <div
                key={clip.clip_id}
                onClick={() => setSelectedIndex(idx)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") setSelectedIndex(idx);
                }}
                className={`flex cursor-pointer items-center justify-between gap-3 rounded-xl border p-3.5 transition ${
                  isSelected
                    ? "border-vice-pink bg-[#18152c] shadow-neon-pink"
                    : "border-vice-border/80 bg-vice-panel/70 hover:border-slate-500"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-vice-pink">
                      #{clip.index}
                    </span>
                    <span className="truncate text-sm font-bold text-white">
                      {clip.title}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-3 font-mono text-[11px] text-slate-400">
                    <span className="inline-flex items-center gap-1">
                      <Timer className="h-3 w-3 text-vice-cyan" />
                      {clip.duration.toFixed(0)}s
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Flame className="h-3 w-3 text-emerald-400" />
                      {clip.viral_score}
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Music2 className="h-3 w-3 text-vice-pink" />
                      {Math.round(clip.bpm)}
                    </span>
                  </div>
                </div>

                {clip.rendered_mp4_url && (
                  <a
                    href={clip.rendered_mp4_url}
                    onClick={(e) => e.stopPropagation()}
                    download={`GTA6_Short_${clip.index}.mp4`}
                    title="Download MP4"
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-vice-border bg-black/40 text-vice-cyan transition hover:border-vice-cyan"
                  >
                    <Download className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            );
          })}
        </div>

        {/* Center: Hero 9:16 Remotion Player */}
        <div className="flex flex-col items-center lg:col-span-4">
          <div className="w-full max-w-[350px] overflow-hidden rounded-[26px] border-2 border-vice-border bg-black p-1.5 shadow-[0_0_50px_rgba(255,46,147,0.16)]">
            <div className="overflow-hidden rounded-[20px]">
              <Player
                key={activeClip.clip_id}
                component={ViralShortComposition}
                inputProps={{ clip: activeClip }}
                durationInFrames={durationInFrames}
                fps={activeClip.fps || 60}
                compositionWidth={1080}
                compositionHeight={1920}
                style={{
                  width: "100%",
                  aspectRatio: "9 / 16",
                }}
                controls
                loop
                clickToPlay
                acknowledgeRemotionLicense
              />
            </div>
          </div>
        </div>

        {/* Right: Minimal Hook Editor & Stats */}
        <div className="space-y-4 lg:col-span-4">
          <div className="rounded-xl border border-vice-border/80 bg-vice-panel/90 p-4">
            <label
              htmlFor="hook-editor"
              className="text-xs font-bold uppercase tracking-wider text-slate-400"
            >
              Top Hook
            </label>
            <input
              id="hook-editor"
              type="text"
              value={activeClip.hook_banner_text}
              onChange={(e) =>
                setHookOverrides((prev) => ({
                  ...prev,
                  [activeClip.clip_id]: e.target.value,
                }))
              }
              className="mt-2 w-full rounded-lg border border-vice-border bg-[#090912] px-3 py-2 font-display text-xs font-bold uppercase text-white outline-none focus:border-vice-cyan"
            />
          </div>

          {/* 4 Clean Metric Tiles */}
          <div className="grid grid-cols-2 gap-2.5 font-mono text-xs">
            <div className="rounded-xl border border-vice-border/70 bg-vice-panel/80 p-3">
              <div className="text-[10px] text-slate-500">BPM</div>
              <div className="mt-0.5 font-bold text-white">
                {Math.round(activeClip.bpm)}
              </div>
            </div>
            <div className="rounded-xl border border-vice-border/70 bg-vice-panel/80 p-3">
              <div className="text-[10px] text-slate-500">DROPS</div>
              <div className="mt-0.5 font-bold text-vice-cyan">{dropCount}</div>
            </div>
            <div className="rounded-xl border border-vice-border/70 bg-vice-panel/80 p-3">
              <div className="text-[10px] text-slate-500">LENGTH</div>
              <div className="mt-0.5 font-bold text-white">
                {activeClip.duration.toFixed(1)}s
              </div>
            </div>
            <div className="rounded-xl border border-vice-border/70 bg-vice-panel/80 p-3">
              <div className="text-[10px] text-slate-500">WORDS</div>
              <div className="mt-0.5 font-bold text-vice-gold">
                {activeClip.captions.length}
              </div>
            </div>
          </div>

          {/* Compact VFX Pills */}
          {(activeClip.memes.length > 0 || activeClip.annotations.length > 0) && (
            <div className="rounded-xl border border-vice-border/80 bg-vice-panel/90 p-4">
              <div className="mb-2.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-400">
                <Zap className="h-3.5 w-3.5 text-vice-gold" />
                FX Cues
              </div>
              <div className="flex flex-wrap gap-1.5">
                {activeClip.annotations.map((ann, i) => (
                  <span
                    key={`ann-${i}`}
                    className="rounded-lg border border-vice-cyan/25 bg-vice-cyan/10 px-2.5 py-1 text-[11px] font-bold italic text-vice-cyan"
                  >
                    {ann.text}
                  </span>
                ))}
                {activeClip.memes.map((m) => (
                  <span
                    key={m.id}
                    className="rounded-lg border border-vice-pink/30 bg-vice-pink/10 px-2.5 py-1 font-mono text-[11px] font-semibold text-white"
                  >
                    {m.label} @{m.time.toFixed(0)}s
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
