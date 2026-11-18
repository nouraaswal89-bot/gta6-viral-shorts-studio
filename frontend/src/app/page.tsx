"use client";

import React, { useEffect, useRef, useState } from "react";
import { PipelineTracker } from "@/components/PipelineTracker";
import { ShortsGalleryPreview } from "@/components/ShortsGalleryPreview";
import { StudioHeader } from "@/components/StudioHeader";
import { UrlAndQuantityCard } from "@/components/UrlAndQuantityCard";
import {
  createPipelineJob,
  createUploadJob,
  fetchBackendHealth,
  subscribeToJobProgress,
} from "@/lib/api";
import type { BackendHealth, JobState, StylePreset } from "@/lib/types";

export default function HomePage() {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [job, setJob] = useState<JobState | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const unsubRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    let active = true;
    const pollHealth = async () => {
      const h = await fetchBackendHealth();
      if (active) setHealth(h);
    };
    pollHealth();
    const timer = setInterval(pollHealth, 30000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    return () => {
      if (unsubRef.current) unsubRef.current();
    };
  }, []);

  const handleStartJob = async (params: {
    url: string;
    numShorts: number;
    preset: StylePreset;
    enableFacecamPip: boolean;
    demoMode?: boolean;
  }) => {
    setErrorBanner(null);
    setIsSubmitting(true);
    if (unsubRef.current) {
      unsubRef.current();
      unsubRef.current = null;
    }

    try {
      const res = await createPipelineJob(params);
      setJob(res.job);
      unsubRef.current = subscribeToJobProgress(
        res.ws_url,
        res.job_id,
        (updated) => setJob(updated),
        (err) => setErrorBanner(err)
      );
    } catch (err) {
      setErrorBanner(
        err instanceof Error ? err.message : "Failed to start job."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUploadFile = async (params: {
    file: File;
    numShorts: number;
    preset: StylePreset;
    enableFacecamPip: boolean;
  }) => {
    setErrorBanner(null);
    setIsSubmitting(true);
    if (unsubRef.current) {
      unsubRef.current();
      unsubRef.current = null;
    }

    try {
      const res = await createUploadJob(params);
      setJob(res.job);
      unsubRef.current = subscribeToJobProgress(
        res.ws_url,
        res.job_id,
        (updated) => setJob(updated),
        (err) => setErrorBanner(err)
      );
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    if (unsubRef.current) {
      unsubRef.current();
      unsubRef.current = null;
    }
    setJob(null);
    setErrorBanner(null);
  };

  const showPreview = Boolean(
    job && job.status === "completed" && job.clips.length > 0
  );

  return (
    <div className="flex min-h-screen flex-col">
      <StudioHeader
        health={health}
        onReset={handleReset}
        showReset={Boolean(job)}
      />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        {errorBanner && (
          <div className="mx-auto mb-5 max-w-2xl rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-2.5 text-xs text-rose-200">
            {errorBanner}
          </div>
        )}

        {!job && (
          <UrlAndQuantityCard
            onStartJob={handleStartJob}
            onUploadFile={handleUploadFile}
            isSubmitting={isSubmitting}
            backendOnline={Boolean(health)}
          />
        )}

        {job && !showPreview && <PipelineTracker job={job} />}

        {job && showPreview && <ShortsGalleryPreview job={job} />}
      </main>
    </div>
  );
}
