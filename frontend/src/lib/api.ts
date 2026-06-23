import axios from "axios";
import type {
  Meeting,
  TranscriptSegment,
  Decision,
  ActionItem,
  VideoFrame,
  ChatMessage,
  UploadResponse,
  SearchResponse,
  VisualSearchResponse,
} from "./types";

// Always call the backend directly — bypasses Next.js proxy issues
const BACKEND_URL =
  typeof window !== "undefined"
    ? (window.__NEXT_DATA__?.props?.pageProps?.backendUrl ||
       process.env.NEXT_PUBLIC_API_URL ||
       "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000");

const API_BASE = `${BACKEND_URL}/api/v1`;

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

// ── Meetings ─────────────────────────────────────────────────────────────

export const meetingsApi = {
  list: (skip = 0, limit = 50): Promise<Meeting[]> =>
    api.get("/meetings/", { params: { skip, limit } }).then((r) => r.data),

  get: (id: string): Promise<Meeting> =>
    api.get(`/meetings/${id}`).then((r) => r.data),

  getStatus: (id: string) =>
    api.get(`/meetings/${id}/status`).then((r) => r.data),

  upload: (
    title: string,
    file: File,
    onProgress?: (pct: number) => void
  ): Promise<UploadResponse> => {
    const form = new FormData();
    form.append("title", title);
    form.append("file", file);
    return api
      .post("/meetings/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300000, // 5 minutes for large files
        onUploadProgress: (e) => {
          if (onProgress && e.total) {
            onProgress(Math.round((e.loaded * 100) / e.total));
          }
        },
      })
      .then((r) => r.data);
  },

  delete: (id: string): Promise<void> =>
    api.delete(`/meetings/${id}`).then(() => undefined),

  getTranscript: (id: string): Promise<TranscriptSegment[]> =>
    api.get(`/meetings/${id}/transcript`).then((r) => r.data),

  getFrames: (id: string): Promise<VideoFrame[]> =>
    api.get(`/meetings/${id}/frames`).then((r) => r.data),

  getRecordingUrl: (id: string): string =>
    `${BACKEND_URL}/api/v1/meetings/${id}/recording`,

  getFrameImageUrl: (meetingId: string, frameId: string): string =>
    `${BACKEND_URL}/api/v1/meetings/${meetingId}/frames/${frameId}/image`,

  getChat: (id: string): Promise<ChatMessage[]> =>
    api.get(`/meetings/${id}/chat`).then((r) => r.data),

  uploadChat: (id: string, file: File): Promise<{ inserted: number }> => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post(`/meetings/${id}/chat`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
};

// ── Search ───────────────────────────────────────────────────────────────

export const searchApi = {
  text: (query: string, topK = 5): Promise<SearchResponse> =>
    api.post("/search/", null, { params: { query, top_k: topK } }).then((r) => r.data),

  visual: (query: string, topK = 5): Promise<VisualSearchResponse> =>
    api.post("/search/visual", null, { params: { query, top_k: topK } }).then((r) => r.data),
};

// ── Decisions ────────────────────────────────────────────────────────────

export const decisionsApi = {
  list: (meetingId?: string, madeBy?: string): Promise<Decision[]> =>
    api
      .get("/decisions/", { params: { meeting_id: meetingId, made_by: madeBy } })
      .then((r) => r.data),
};

// ── Action Items ─────────────────────────────────────────────────────────

export const actionsApi = {
  list: (params?: {
    owner?: string;
    status?: string;
    meeting_id?: string;
  }): Promise<ActionItem[]> =>
    api.get("/actions/", { params }).then((r) => r.data),

  update: (
    id: string,
    payload: { status?: string; owner?: string; due_date?: string }
  ): Promise<ActionItem> =>
    api.patch(`/actions/${id}`, payload).then((r) => r.data),
};
