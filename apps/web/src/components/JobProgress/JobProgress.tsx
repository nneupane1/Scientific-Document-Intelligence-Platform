"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import type { Job } from "@/types/sdr";

export default function JobProgress({ jobId, onComplete }: { jobId: string; onComplete?: () => void }) {
  const [job, setJob] = useState<Job | null>(null);
  useEffect(() => {
    const events = new EventSource(`${API_URL}/api/jobs/${jobId}/events`);
    events.addEventListener("progress", (event) => {
      const next = JSON.parse((event as MessageEvent).data) as Job; setJob(next);
      if (["completed", "failed", "cancelled"].includes(next.status)) { events.close(); onComplete?.(); }
    });
    return () => events.close();
  }, [jobId, onComplete]);
  if (!job) return <p className="job-message">Queued…</p>;
  return <div className="job-progress" aria-live="polite"><div><strong>{job.stage}</strong><span>{job.pages_completed} / {job.pages_total} pages</span></div><div className="progress-track"><span style={{ width: `${job.progress * 100}%` }} /></div>{job.error && <p className="error">{job.error}</p>}</div>;
}
