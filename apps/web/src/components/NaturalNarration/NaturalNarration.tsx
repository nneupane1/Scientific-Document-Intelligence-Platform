"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { documentsApi } from "@/lib/api";
import type {
  NarrationCapabilities,
  NarrationVoice,
  SdrElement,
} from "@/types/sdr";

type NarrationScope = "page" | "selection";

const SILENT_AUDIO_PRIMER =
  "data:audio/wav;base64,UklGRsQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";

export default function NaturalNarration({
  documentId,
  pageNumber,
  selected,
}: {
  documentId: string;
  pageNumber: number;
  selected: SdrElement | null;
}) {
  const [capabilities, setCapabilities] = useState<NarrationCapabilities | null>(null);
  const [voice, setVoice] = useState<NarrationVoice>("af_heart");
  const [loading, setLoading] = useState<NarrationScope | null>(null);
  const [readOnClick, setReadOnClick] = useState(true);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioLabel, setAudioLabel] = useState("");
  const [message, setMessage] = useState("Checking the neural voice service…");
  const audioRef = useRef<HTMLAudioElement>(null);
  const lastAutoTargetRef = useRef<string | null>(null);
  const requestSerialRef = useRef(0);

  useEffect(() => {
    let active = true;
    void documentsApi
      .narrationCapabilities()
      .then((result) => {
        if (!active) return;
        setCapabilities(result);
        setVoice(result.default_voice);
        setMessage(
          result.configured
            ? "Read on click is active. Select any document region to hear it."
            : "Install a local voice model or configure a voice provider.",
        );
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setMessage(reason instanceof Error ? reason.message : String(reason));
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(
    () => () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    },
    [audioUrl],
  );

  useEffect(() => {
    if (!audioUrl || !audioRef.current) return;
    void audioRef.current.play().catch(() => {
      setMessage("Narration is ready. Press play to hear it.");
    });
  }, [audioUrl]);

  useEffect(() => {
    function primeAudioFromClick() {
      const player = audioRef.current;
      if (!capabilities?.configured || !player) return;
      player.pause();
      if (audioUrl) return;
      player.currentTime = 0;
      void player.play().then(() => {
        player.pause();
        player.currentTime = 0;
      }).catch(() => undefined);
    }
    window.addEventListener("scidoc:narration-gesture", primeAudioFromClick);
    return () => window.removeEventListener("scidoc:narration-gesture", primeAudioFromClick);
  }, [audioUrl, capabilities?.configured]);

  const generate = useCallback(
    async (scope: NarrationScope, target = selected) => {
      if (!capabilities?.configured) return;
      const requestSerial = ++requestSerialRef.current;
      setLoading(scope);
      setMessage(
        scope === "selection"
          ? "Creating natural narration for the selected region…"
          : `Creating natural narration for page ${pageNumber}…`,
      );
      try {
        const blob = await documentsApi.narrate(documentId, {
          page_number: pageNumber,
          ...(scope === "selection" && target ? { element_id: target.id } : {}),
          voice,
        });
        if (requestSerial !== requestSerialRef.current) return;
        const nextUrl = URL.createObjectURL(blob);
        setAudioUrl(nextUrl);
        const label =
          scope === "selection" && target
            ? `${target.element_type.replaceAll("_", " ")} on page ${pageNumber}`
            : `page ${pageNumber}`;
        setAudioLabel(label);
        setMessage(`Natural narration for ${label} is ready.`);
      } catch (reason) {
        if (requestSerial !== requestSerialRef.current) return;
        setMessage(reason instanceof Error ? reason.message : String(reason));
      } finally {
        if (requestSerial === requestSerialRef.current) setLoading(null);
      }
    },
    [capabilities?.configured, documentId, pageNumber, selected, voice],
  );

  useEffect(() => {
    if (!readOnClick || !capabilities?.configured || !selected) return;
    const targetKey = `${pageNumber}:${selected.id}`;
    if (lastAutoTargetRef.current === targetKey) return;
    lastAutoTargetRef.current = targetKey;
    audioRef.current?.pause();
    setMessage(
      `Selected ${selected.element_type.replaceAll("_", " ")}. Preparing natural narration…`,
    );
    const timer = window.setTimeout(() => {
      void generate("selection", selected);
    }, 140);
    return () => window.clearTimeout(timer);
  }, [capabilities?.configured, generate, pageNumber, readOnClick, selected]);

  const selectionLabel = selected
    ? selected.element_type === "equation" || selected.element_type === "chemical_equation"
      ? "Listen to equation"
      : "Listen to selection"
    : "Select a region first";

  return (
    <section className="natural-narration" aria-labelledby="natural-narration-title">
      <div className="narration-identity">
        <div className={`voice-orb ${loading ? "is-speaking" : ""}`} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
        <div>
          <p className="eyebrow">
            {capabilities?.remote_processing ? "Optional neural audio" : "Private local audio"}
          </p>
          <h2 id="natural-narration-title">Natural narration</h2>
        </div>
        <span className="ai-voice-badge">
          {capabilities?.provider === "kokoro"
            ? "Local neural voice"
            : capabilities?.provider === "macos"
              ? "Mac system voice"
              : "AI-generated voice"}
        </span>
      </div>

      <div className="narration-actions">
        <label>
          <span>Voice</span>
          <select
            value={voice}
            onChange={(event) => setVoice(event.target.value as NarrationVoice)}
            disabled={!capabilities?.configured || loading !== null}
            aria-label="Natural narration voice"
          >
            {(capabilities?.voices ?? [
              { id: "af_heart" as const, label: "Heart — warm, natural American", recommended: true },
            ]).map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="narration-primary"
          onClick={() => void generate("page")}
          disabled={!capabilities?.configured || loading !== null}
        >
          {loading === "page" ? "Preparing page…" : "▶ Listen to page"}
        </button>
        <button
          type="button"
          className="narration-secondary"
          onClick={() => void generate("selection")}
          disabled={!capabilities?.configured || !selected || loading !== null}
        >
          {loading === "selection" ? "Preparing…" : selectionLabel}
        </button>
        <label className="narration-auto-toggle">
          <input
            type="checkbox"
            checked={readOnClick}
            onChange={(event) => {
              lastAutoTargetRef.current = null;
              setReadOnClick(event.target.checked);
              setMessage(
                event.target.checked
                  ? "Read on click is active. Select any document region to hear it."
                  : "Read on click is paused. Manual Listen controls remain available.",
              );
            }}
            disabled={!capabilities?.configured}
          />
          <span aria-hidden="true" />
          Read on click
        </label>
      </div>

      <div className="narration-output">
        <audio
          ref={audioRef}
          controls={audioUrl !== null}
          src={audioUrl ?? SILENT_AUDIO_PRIMER}
          className={audioUrl ? undefined : "narration-audio-primer"}
          aria-hidden={audioUrl ? undefined : true}
          aria-label={audioUrl ? `Natural AI narration for ${audioLabel}` : undefined}
        />
        {!audioUrl && (
          <div className="narration-placeholder" aria-hidden="true">
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
            <i />
          </div>
        )}
        <p className="narration-status" role="status" aria-live="polite">
          {message}
        </p>
        <p className="narration-privacy">
          {capabilities?.privacy_notice ??
            "Speech is generated locally; the PDF and narration text stay on this device."}
        </p>
      </div>
    </section>
  );
}
