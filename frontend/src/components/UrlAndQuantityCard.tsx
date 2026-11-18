"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  Link2,
  Loader2,
  Play,
  Radio,
  Sparkles,
  Upload,
  UserSquare2,
  Wand2,
} from "lucide-react";
import { isLikelyYouTubeUrl, validateYouTubeUrl } from "@/lib/api";
import type { StreamMetadata, StylePreset } from "@/lib/types";

interface UrlAndQuantityCardProps {
  onStartJob: (params: {
    url: string;
    numShorts: number;
    preset: StylePreset;
    enableFacecamPip: boolean;
    demoMode?: boolean;
  }) => void;
  onUploadFile: (params: {
    file: File;
    numShorts: number;
    preset: StylePreset;
    enableFacecamPip: boolean;
  }) => void;
  isSubmitting: boolean;
  backendOnline: boolean;
}

const QUICK_COUNTS = [1, 3, 5, 10];

const MINIMAL_PRESETS: {
  id: StylePreset;
  label: string;
  accent: string;
}[] = [
  { id: "strykeditz_phonk", label: "Phonk Hype", accent: "from-vice-pink to-vice-cyan" },
  { id: "firefly_cinematic", label: "Cinematic 8K", accent: "from-vice-sunset to-vice-pink" },
  { id: "chaotic_meme", label: "GTA Meme", accent: "from-vice-gold to-vice-pink" },
];

export const UrlAndQuantityCard: React.FC<UrlAndQuantityCardProps> = ({
  onStartJob,
  onUploadFile,
  isSubmitting,
  backendOnline,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [url, setUrl] = useState("");
  const [validating, setValidating] = useState(false);
  const [metadata, setMetadata] = useState<StreamMetadata | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [numShorts, setNumShorts] = useState<number>(3);
  const [customCount, setCustomCount] = useState<string>("");
  const [isCustomMode, setIsCustomMode] = useState(false);
  const [preset, setPreset] = useState<StylePreset>("strykeditz_phonk");
  const [enableFacecamPip, setEnableFacecamPip] = useState(true);

  const urlLooksValid = isLikelyYouTubeUrl(url);

  useEffect(() => {
    setValidationError(null);
    if (!urlLooksValid) {
      setMetadata(null);
      return;
    }
    if (!backendOnline) return;

    let cancelled = false;
    const timer = setTimeout(async () => {
      setValidating(true);
      try {
        const res = await validateYouTubeUrl(url.trim());
        if (cancelled) return;
        if (res.valid && res.metadata) {
          setMetadata(res.metadata);
          setValidationError(null);
        } else {
          setMetadata(null);
          setValidationError(res.error || "Stream not found");
        }
      } catch {
        if (!cancelled) setValidationError("Validator offline");
      } finally {
        if (!cancelled) setValidating(false);
      }
    }, 450);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [url, urlLooksValid, backendOnline]);

  const effectiveCount = isCustomMode
    ? Math.max(1, Math.min(20, Number(customCount) || 1))
    : numShorts;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlLooksValid || isSubmitting) return;
    onStartJob({
      url: url.trim(),
      numShorts: effectiveCount,
      preset,
      enableFacecamPip,
      demoMode: false,
    });
  };

  const handleLaunchDemo = () => {
    if (isSubmitting) return;
    onStartJob({
      url: url.trim() || "https://www.youtube.com/watch?v=QdBZY2fkU-0",
      numShorts: effectiveCount,
      preset,
      enableFacecamPip,
      demoMode: true,
    });
  };

  return (
    <div className="mx-auto max-w-2xl pt-6 sm:pt-12">
      <div className="mb-8 text-center">
        <h1 className="font-display text-3xl font-black tracking-tight text-white sm:text-4xl">
          GTA 6{" "}
          <span className="bg-gradient-to-r from-vice-pink via-vice-sunset to-vice-cyan bg-clip-text text-transparent">
            Viral Shorts
          </span>
        </h1>
      </div>

      <form
        onSubmit={handleSubmit}
        className="overflow-hidden rounded-2xl border border-vice-border/80 bg-vice-panel/90 shadow-2xl backdrop-blur-xl"
      >
        {/* URL Input */}
        <div className="p-5 sm:p-6">
          <div className="relative">
            <Link2 className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              id="yt-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste YouTube Live or VOD URL"
              className="w-full rounded-xl border border-vice-border bg-[#090912] py-3.5 pl-11 pr-11 font-mono text-sm text-white placeholder-slate-500 outline-none transition focus:border-vice-cyan focus:ring-2 focus:ring-vice-cyan/20"
            />
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
              {validating ? (
                <Loader2 className="h-4 w-4 animate-spin text-vice-cyan" />
              ) : urlLooksValid ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : null}
            </div>
          </div>

          {metadata && (
            <div className="mt-3 flex items-center gap-3 rounded-xl border border-emerald-500/25 bg-emerald-500/5 p-2.5">
              {metadata.thumbnail && (
                <img
                  src={metadata.thumbnail}
                  alt={metadata.title}
                  className="h-11 w-20 shrink-0 rounded-lg object-cover"
                />
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-white">
                  {metadata.title}
                </p>
                <div className="mt-0.5 flex items-center gap-2 text-[11px] text-slate-400">
                  {metadata.is_live ? (
                    <span className="inline-flex items-center gap-1 font-bold text-rose-400">
                      <Radio className="h-3 w-3 animate-pulse" />
                      LIVE
                    </span>
                  ) : (
                    <span className="font-mono text-vice-cyan">
                      {metadata.max_resolution}
                    </span>
                  )}
                  <span className="truncate">{metadata.channel}</span>
                </div>
              </div>
            </div>
          )}

          {validationError && (
            <p className="mt-2 text-xs text-amber-300">{validationError}</p>
          )}
        </div>

        {/* Controls Panel */}
        <div className="space-y-5 border-t border-vice-border/60 bg-[#0b0b15]/80 p-5 sm:p-6">
          {/* Quantity Selector */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
              <span>How many Shorts?</span>
              <span className="font-mono text-[11px] text-slate-500">
                15–30s • 9:16
              </span>
            </div>

            <div className="grid grid-cols-5 gap-2">
              {QUICK_COUNTS.map((count) => {
                const active = !isCustomMode && numShorts === count;
                return (
                  <button
                    key={count}
                    type="button"
                    onClick={() => {
                      setIsCustomMode(false);
                      setNumShorts(count);
                    }}
                    className={`rounded-xl border py-2.5 font-display text-base font-black transition ${
                      active
                        ? "border-vice-cyan bg-vice-cyan/15 text-white shadow-neon-cyan"
                        : "border-vice-border bg-vice-card text-slate-300 hover:border-slate-500 hover:text-white"
                    }`}
                  >
                    {count}
                  </button>
                );
              })}

              <input
                type="number"
                min={1}
                max={20}
                value={customCount}
                onFocus={() => setIsCustomMode(true)}
                onChange={(e) => {
                  setIsCustomMode(true);
                  setCustomCount(e.target.value);
                }}
                placeholder="Custom"
                aria-label="Custom number of Shorts"
                className={`rounded-xl border bg-vice-card px-2 py-2.5 text-center font-mono text-xs font-bold text-white placeholder-slate-500 outline-none transition ${
                  isCustomMode
                    ? "border-vice-pink bg-vice-pink/15 shadow-neon-pink"
                    : "border-vice-border hover:border-slate-500"
                }`}
              />
            </div>
          </div>

          {/* Style Presets */}
          <div className="space-y-2.5">
            <div className="text-xs font-semibold text-slate-300">Style</div>
            <div className="grid grid-cols-3 gap-2">
              {MINIMAL_PRESETS.map((opt) => {
                const selected = preset === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setPreset(opt.id)}
                    className={`relative overflow-hidden rounded-xl border px-3 py-3 text-center transition ${
                      selected
                        ? "border-vice-pink bg-[#19162d] text-white shadow-neon-pink"
                        : "border-vice-border bg-vice-card/80 text-slate-300 hover:border-slate-500 hover:text-white"
                    }`}
                  >
                    <div
                      className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${opt.accent} ${
                        selected ? "opacity-100" : "opacity-30"
                      }`}
                    />
                    <span className="inline-flex items-center gap-1.5 text-xs font-bold">
                      <Sparkles className="h-3 w-3 text-vice-cyan" />
                      {opt.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Footer Row: Facecam Toggle + Actions */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <button
              type="button"
              onClick={() => setEnableFacecamPip((v) => !v)}
              className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition ${
                enableFacecamPip
                  ? "border-vice-cyan/50 bg-vice-cyan/10 text-vice-cyan"
                  : "border-vice-border bg-vice-card text-slate-400"
              }`}
            >
              <UserSquare2 className="h-3.5 w-3.5" />
              Facecam PiP
            </button>

            <div className="flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="video/mp4,video/webm,video/quicktime,video/x-matroska"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    onUploadFile({
                      file,
                      numShorts: effectiveCount,
                      preset,
                      enableFacecamPip,
                    });
                    e.target.value = "";
                  }
                }}
              />
              <button
                type="button"
                disabled={isSubmitting || !backendOnline}
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-1.5 rounded-xl border border-vice-border bg-vice-card px-3.5 py-2.5 text-xs font-bold text-slate-200 transition hover:border-vice-cyan/60 hover:text-white disabled:opacity-40"
              >
                <Upload className="h-3.5 w-3.5 text-vice-cyan" />
                Upload
              </button>

              <button
                type="button"
                disabled={isSubmitting || !backendOnline}
                onClick={handleLaunchDemo}
                className="inline-flex items-center gap-1.5 rounded-xl border border-vice-border bg-vice-card px-3.5 py-2.5 text-xs font-bold text-slate-200 transition hover:border-vice-cyan/60 hover:text-white disabled:opacity-40"
              >
                <Play className="h-3.5 w-3.5 fill-current text-vice-cyan" />
                Demo
              </button>

              <button
                type="submit"
                disabled={!urlLooksValid || isSubmitting || !backendOnline}
                className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-vice-pink to-vice-cyan px-5 py-2.5 text-xs font-black uppercase tracking-wider text-white shadow-neon-pink transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-35"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Wand2 className="h-4 w-4" />
                )}
                Generate ({effectiveCount})
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
