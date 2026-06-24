"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import {
  ArrowLeft, RefreshCw, Trash2, Loader2,
  MessageSquare, Lightbulb, CheckSquare, FileText, Image as ImageIcon,
} from "lucide-react";
import { meetingsApi, decisionsApi, actionsApi } from "@/lib/api";
import StatusBadge from "@/components/meetings/StatusBadge";
import TranscriptView from "@/components/meetings/TranscriptView";
import DecisionList from "@/components/meetings/DecisionList";
import ActionItemList from "@/components/meetings/ActionItemList";
import MeetingSummary from "@/components/meetings/MeetingSummary";
import FrameGallery from "@/components/meetings/FrameGallery";
import { formatDate, formatDuration } from "@/lib/utils";
import { toast } from "sonner";
import type { ActionItem } from "@/lib/types";

// Dynamically import ReactPlayer to avoid SSR issues
const ReactPlayer = dynamic(() => import("react-player/lazy"), { ssr: false });

// The backend marks timeouts with a message like
// "Processing exceeded the 7200s time limit ...".
function isTimeoutError(message?: string | null): boolean {
  if (!message) return false;
  const m = message.toLowerCase();
  return m.includes("time limit") || m.includes("timed out") || m.includes("timeout");
}

const TABS = [
  { id: "transcript", label: "Transcript", icon: MessageSquare },
  { id: "decisions", label: "Decisions", icon: Lightbulb },
  { id: "actions", label: "Action Items", icon: CheckSquare },
  { id: "summary", label: "Summary", icon: FileText },
  { id: "frames", label: "Frames", icon: ImageIcon },
];

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const id = params.id as string;

  const [activeTab, setActiveTab] = useState("transcript");
  const [currentTime, setCurrentTime] = useState(0);
  const playerRef = useRef<{ seekTo: (t: number) => void } | null>(null);
  const prevStatusRef = useRef<string | null>(null);

  const { data: meeting, isLoading, isError } = useQuery({
    queryKey: ["meeting", id],
    queryFn: () => meetingsApi.get(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" || status === "pending" ? 3000 : false;
    },
  });

  const { data: transcript = [] } = useQuery({
    queryKey: ["transcript", id],
    queryFn: () => meetingsApi.getTranscript(id),
    enabled: meeting?.status === "done",
  });

  const { data: decisions = [] } = useQuery({
    queryKey: ["decisions", id],
    queryFn: () => decisionsApi.list(id),
    enabled: meeting?.status === "done",
  });

  const { data: actions = [], refetch: refetchActions } = useQuery({
    queryKey: ["actions", id],
    queryFn: () => actionsApi.list({ meeting_id: id }),
    enabled: meeting?.status === "done",
  });

  const { data: frames = [] } = useQuery({
    queryKey: ["frames", id],
    queryFn: () => meetingsApi.getFrames(id),
    enabled: meeting?.status === "done",
  });

  const { data: chatMessages = [] } = useQuery({
    queryKey: ["chat", id],
    queryFn: () => meetingsApi.getChat(id),
    enabled: meeting?.status === "done",
  });

  // Notify the user when processing finishes or fails (incl. timeouts) while
  // they're watching the page (status is polled every 3s above).
  useEffect(() => {
    if (!meeting) return;
    const prev = prevStatusRef.current;
    if (prev && prev !== meeting.status) {
      if (meeting.status === "done") {
        toast.success("Processing complete!");
      } else if (meeting.status === "failed") {
        if (isTimeoutError(meeting.error_message)) {
          toast.error(
            "Processing timed out. Try a shorter recording, a smaller Whisper model, or disabling diarization/OCR.",
            { duration: 10000 }
          );
        } else {
          toast.error(`Processing failed: ${meeting.error_message || "Unknown error"}`);
        }
      }
    }
    prevStatusRef.current = meeting.status;
  }, [meeting]);

  const handleSeek = useCallback((time: number) => {
    playerRef.current?.seekTo(time);
    setCurrentTime(time);
  }, []);

  const handleDelete = async () => {
    if (!confirm("Delete this meeting and all its data?")) return;
    try {
      await meetingsApi.delete(id);
      toast.success("Meeting deleted");
      queryClient.invalidateQueries({ queryKey: ["meetings"] });
      router.push("/meetings");
    } catch {
      toast.error("Failed to delete meeting");
    }
  };

  const handleActionUpdate = (updated: ActionItem) => {
    queryClient.setQueryData(["actions", id], (old: ActionItem[] = []) =>
      old.map((a) => (a.id === updated.id ? updated : a))
    );
    queryClient.invalidateQueries({ queryKey: ["actions"] });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400">
        <p>Could not load this meeting. Make sure the backend is running.</p>
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400">
        <p>Meeting not found.</p>
      </div>
    );
  }

  const recordingUrl = meetingsApi.getRecordingUrl(id);
  const isProcessing = meeting.status === "pending" || meeting.status === "processing";

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-200 bg-white">
        <button
          onClick={() => router.back()}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="font-semibold text-gray-900 truncate">{meeting.title}</h1>
          <div className="flex items-center gap-3 mt-0.5">
            <StatusBadge status={meeting.status} />
            {meeting.date && (
              <span className="text-xs text-gray-400">{formatDate(meeting.date)}</span>
            )}
            {meeting.duration_seconds && (
              <span className="text-xs text-gray-400">
                {formatDuration(meeting.duration_seconds)}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ["meeting", id] })}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleDelete}
            className="p-2 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50"
            title="Delete meeting"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Processing state */}
      {isProcessing && (
        <div className="flex items-center gap-3 px-6 py-4 bg-blue-50 border-b border-blue-100">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          <p className="text-sm text-blue-700">
            Processing your meeting… This may take a few minutes. The page will update automatically.
          </p>
        </div>
      )}

      {meeting.status === "failed" && (
        <div className="px-6 py-4 bg-red-50 border-b border-red-100">
          {isTimeoutError(meeting.error_message) ? (
            <div className="text-sm text-red-700">
              <p className="font-semibold">Processing timed out</p>
              <p className="mt-0.5">{meeting.error_message}</p>
              <p className="mt-1 text-red-600/80">
                Tip: upload a shorter recording, switch to a smaller Whisper model, or
                disable diarization/OCR to speed processing up.
              </p>
            </div>
          ) : (
            <p className="text-sm text-red-700">
              Processing failed: {meeting.error_message || "Unknown error"}
            </p>
          )}
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Video + Tabs */}
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Video player */}
          <div className="bg-black">
            <ReactPlayer
              ref={playerRef as React.RefObject<unknown>}
              url={recordingUrl}
              controls
              width="100%"
              height="280px"
              onProgress={({ playedSeconds }) => setCurrentTime(playedSeconds)}
              config={{
                file: { attributes: { crossOrigin: "anonymous" } },
              }}
            />
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200 bg-white px-4">
            {TABS.map(({ id: tabId, label, icon: Icon }) => (
              <button
                key={tabId}
                onClick={() => setActiveTab(tabId)}
                className={`flex items-center gap-1.5 px-4 py-3 text-xs font-medium border-b-2 transition-colors ${
                  activeTab === tabId
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
                {tabId === "transcript" && chatMessages.length > 0 && (
                  <span className="ml-1 bg-purple-100 text-purple-700 text-xs px-1.5 py-0.5 rounded-full">
                    {chatMessages.length}
                  </span>
                )}
                {tabId === "decisions" && decisions.length > 0 && (
                  <span className="ml-1 bg-blue-100 text-blue-700 text-xs px-1.5 py-0.5 rounded-full">
                    {decisions.length}
                  </span>
                )}
                {tabId === "actions" && actions.length > 0 && (
                  <span className="ml-1 bg-orange-100 text-orange-700 text-xs px-1.5 py-0.5 rounded-full">
                    {actions.filter((a) => a.status === "open").length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === "transcript" && (
              <TranscriptView
                segments={transcript}
                chatMessages={chatMessages}
                currentTime={currentTime}
                onSeek={handleSeek}
              />
            )}
            {activeTab === "decisions" && (
              <DecisionList decisions={decisions} onSeek={handleSeek} />
            )}
            {activeTab === "actions" && (
              <ActionItemList
                items={actions}
                onSeek={handleSeek}
                onUpdate={handleActionUpdate}
              />
            )}
            {activeTab === "summary" && <MeetingSummary meeting={meeting} />}
            {activeTab === "frames" && (
              <FrameGallery frames={frames} meetingId={id} onSeek={handleSeek} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
