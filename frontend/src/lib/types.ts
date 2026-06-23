// ── Meeting ──────────────────────────────────────────────────────────────

export type MeetingStatus = "pending" | "processing" | "done" | "failed";

export interface Meeting {
  id: string;
  title: string;
  date: string | null;
  duration_seconds: number | null;
  status: MeetingStatus;
  error_message: string | null;
  summary: string | null;
  participants: string[];
  topics: string[];
  unresolved: string[];
  entities: Array<{ name: string; type: string; mentions: number }>;
  created_at: string;
  processed_at: string | null;
}

export interface MeetingStatus_ {
  meeting_id: string;
  status: MeetingStatus;
  error_message: string | null;
}

export interface UploadResponse {
  meeting_id: string;
  status: string;
  message: string;
}

// ── Transcript ───────────────────────────────────────────────────────────

export interface TranscriptSegment {
  id: string;
  meeting_id: string;
  speaker: string;
  text: string;
  start_time: number;
  end_time: number;
  confidence: number | null;
}

// ── Decision ─────────────────────────────────────────────────────────────

export interface Decision {
  id: string;
  meeting_id: string;
  text: string;
  made_by: string | null;
  timestamp: number | null;
  confidence: number;
  context: string | null;
}

// ── Action Item ──────────────────────────────────────────────────────────

export type ActionStatus = "open" | "in_progress" | "done" | "cancelled";

export interface ActionItem {
  id: string;
  meeting_id: string;
  text: string;
  owner: string | null;
  due_date: string | null;
  timestamp: number | null;
  status: ActionStatus;
}

// ── Video Frame ──────────────────────────────────────────────────────────

export interface VideoFrame {
  id: string;
  meeting_id: string;
  timestamp: number;
  frame_path: string;
  ocr_text: string | null;
  scene_type: string | null;
}

// ── Chat Message ─────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  meeting_id: string;
  sender: string | null;
  text: string;
  timestamp: number | null;
  platform: string | null;
}

// ── Search ───────────────────────────────────────────────────────────────

export interface SearchSource {
  type: "transcript" | "frame";
  meeting_id: string | null;
  meeting_title: string | null;
  speaker: string | null;
  text: string | null;
  start_time: number | null;
  end_time: number | null;
  frame_id: string | null;
  frame_path: string | null;
  timestamp: number | null;
  ocr_text: string | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  answer: string;
  sources: SearchSource[];
}

export interface VisualSearchResponse {
  query: string;
  frames: SearchSource[];
}
