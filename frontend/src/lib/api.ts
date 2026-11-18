import type {
  BackendHealth,
  CreateJobResponse,
  JobState,
  StylePreset,
  ValidateUrlResponse,
} from "./types";

export function getBackendUrl(): string {
  const configured = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "");
  if (configured) return configured;
  if (typeof window !== "undefined") {
    return window.location.origin.replace(/\/$/, "");
  }
  return "http://localhost:8000";
}

const YOUTUBE_PATTERN =
  /^(https?:\/\/)?(www\.|m\.)?(youtube\.com\/(watch\?v=|live\/|shorts\/|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/;

export function isLikelyYouTubeUrl(url: string): boolean {
  const trimmed = url.trim();
  if (!trimmed) return false;
  return YOUTUBE_PATTERN.test(trimmed) || /[?&]v=[A-Za-z0-9_-]{11}/.test(trimmed);
}

export async function fetchBackendHealth(): Promise<BackendHealth | null> {
  try {
    const res = await fetch(`${getBackendUrl()}/api/health`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as BackendHealth;
  } catch {
    return null;
  }
}

export async function validateYouTubeUrl(
  url: string
): Promise<ValidateUrlResponse> {
  const res = await fetch(`${getBackendUrl()}/api/validate-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    return { valid: false, error: `Validation failed (${res.status})` };
  }
  return (await res.json()) as ValidateUrlResponse;
}

export async function createPipelineJob(params: {
  url: string;
  numShorts: number;
  preset: StylePreset;
  enableFacecamPip: boolean;
  demoMode?: boolean;
}): Promise<CreateJobResponse> {
  const res = await fetch(`${getBackendUrl()}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: params.url,
      num_shorts: params.numShorts,
      preset: params.preset,
      enable_facecam_pip: params.enableFacecamPip,
      demo_mode: Boolean(params.demoMode),
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Failed to create job (${res.status})`);
  }
  return (await res.json()) as CreateJobResponse;
}

export async function createUploadJob(params: {
  file: File;
  numShorts: number;
  preset: StylePreset;
  enableFacecamPip: boolean;
}): Promise<CreateJobResponse> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("num_shorts", String(params.numShorts));
  form.append("preset", params.preset);
  form.append("enable_facecam_pip", String(params.enableFacecamPip));

  const res = await fetch(`${getBackendUrl()}/api/jobs/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Upload failed (${res.status})`);
  }
  return (await res.json()) as CreateJobResponse;
}

export async function fetchJobState(jobId: string): Promise<JobState> {
  const res = await fetch(`${getBackendUrl()}/api/jobs/${jobId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Unable to fetch job ${jobId}`);
  }
  return (await res.json()) as JobState;
}

export function subscribeToJobProgress(
  wsUrl: string,
  jobId: string,
  onUpdate: (job: JobState) => void,
  onError?: (err: string) => void
): () => void {
  let closed = false;
  let ws: WebSocket | null = null;
  let pollTimer: ReturnType<typeof setInterval> | null = null;

  const startPollingFallback = () => {
    if (pollTimer || closed) return;
    pollTimer = setInterval(async () => {
      if (closed) return;
      try {
        const job = await fetchJobState(jobId);
        onUpdate(job);
        if (job.status === "completed" || job.status === "failed") {
          if (pollTimer) clearInterval(pollTimer);
        }
      } catch {
        // Keep polling transiently
      }
    }, 1500);
  };

  // Ensure ws:// upgrades to wss:// automatically on HTTPS deployments (e.g., Railway)
  let resolvedWsUrl = wsUrl;
  if (typeof window !== "undefined") {
    const base = getBackendUrl();
    const wsBase = base.replace(/^https:/, "wss:").replace(/^http:/, "ws:");
    resolvedWsUrl = `${wsBase}/ws/jobs/${jobId}`;
  }

  try {
    ws = new WebSocket(resolvedWsUrl);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "job_update" && data.job) {
          onUpdate(data.job as JobState);
        } else if (data.type === "error" && onError) {
          onError(data.message || "WebSocket error");
        }
      } catch {
        // Ignore non-JSON frames
      }
    };
    ws.onerror = () => startPollingFallback();
    ws.onclose = () => {
      if (!closed) startPollingFallback();
    };
  } catch {
    startPollingFallback();
  }

  return () => {
    closed = true;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
    if (pollTimer) {
      clearInterval(pollTimer);
    }
  };
}
