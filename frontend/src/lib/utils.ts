import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format seconds as M:SS (e.g. 148.2 → "2:28") */
export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Format seconds as H:MM:SS for long durations */
export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

/** Format ISO date string as "Jun 20, 2026" */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

/** Consistent speaker color based on speaker name */
const SPEAKER_COLORS = [
  "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/20",
  "bg-purple-500/15 text-purple-400 ring-1 ring-purple-500/20",
  "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/20",
  "bg-orange-500/15 text-orange-400 ring-1 ring-orange-500/20",
  "bg-pink-500/15 text-pink-400 ring-1 ring-pink-500/20",
  "bg-teal-500/15 text-teal-400 ring-1 ring-teal-500/20",
  "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/20",
  "bg-red-500/15 text-red-400 ring-1 ring-red-500/20",
];

const speakerColorCache: Record<string, string> = {};
let colorIndex = 0;

export function getSpeakerColor(speaker: string): string {
  if (!speakerColorCache[speaker]) {
    speakerColorCache[speaker] = SPEAKER_COLORS[colorIndex % SPEAKER_COLORS.length];
    colorIndex++;
  }
  return speakerColorCache[speaker];
}

/** Get initials from a speaker name */
export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

/** Build the backend API URL for a recording stream */
export function getRecordingUrl(meetingId: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${base}/api/v1/meetings/${meetingId}/recording`;
}

/** Build the backend API URL for a frame image */
export function getFrameImageUrl(meetingId: string, frameId: string): string {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${base}/api/v1/meetings/${meetingId}/frames/${frameId}/image`;
}

/** Truncate text to maxLen with ellipsis */
export function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + "…";
}
