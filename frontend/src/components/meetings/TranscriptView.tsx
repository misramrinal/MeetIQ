"use client";

import { useRef, useEffect } from "react";
import { MessageSquare } from "lucide-react";
import type { TranscriptSegment, ChatMessage } from "@/lib/types";
import { formatTime, getSpeakerColor, getInitials, cn } from "@/lib/utils";

type Entry =
  | { kind: "segment"; data: TranscriptSegment }
  | { kind: "chat"; data: ChatMessage };

interface TranscriptViewProps {
  segments: TranscriptSegment[];
  chatMessages?: ChatMessage[];
  currentTime?: number;
  onSeek?: (time: number) => void;
}

export default function TranscriptView({
  segments,
  chatMessages = [],
  currentTime = 0,
  onSeek,
}: TranscriptViewProps) {
  const activeRef = useRef<HTMLDivElement>(null);

  const entries: Entry[] = [
    ...segments.map((s) => ({ kind: "segment" as const, data: s })),
    ...chatMessages.map((c) => ({ kind: "chat" as const, data: c })),
  ].sort((a, b) => {
    const tA = a.kind === "segment" ? a.data.start_time : a.data.timestamp ?? Infinity;
    const tB = b.kind === "segment" ? b.data.start_time : b.data.timestamp ?? Infinity;
    return tA - tB;
  });

  const activeIndex = entries.findIndex(
    (e) => e.kind === "segment" && e.data.start_time <= currentTime && currentTime < e.data.end_time
  );

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeIndex]);

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-subtle">
        <MessageSquare className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No transcript available yet.</p>
        <p className="text-xs mt-1">Processing may still be in progress.</p>
      </div>
    );
  }

  return (
    <div className="space-y-1 p-4 max-w-3xl mx-auto">
      {entries.map((entry, i) => {
        if (entry.kind === "segment") {
          const seg = entry.data;
          const isActive = i === activeIndex;
          return (
            <div
              key={`seg-${seg.id}`}
              ref={isActive ? activeRef : undefined}
              onClick={() => onSeek?.(seg.start_time)}
              className={cn(
                "flex gap-3 p-3 rounded-xl transition-all duration-150",
                onSeek && "cursor-pointer",
                isActive ? "bg-accent/10 ring-1 ring-accent/30" : "hover:bg-panel-2"
              )}
            >
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 mt-0.5",
                  getSpeakerColor(seg.speaker)
                )}
              >
                {getInitials(seg.speaker)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-semibold text-fg">{seg.speaker}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSeek?.(seg.start_time);
                    }}
                    className="text-xs text-accent hover:opacity-80 font-mono tabular-nums"
                  >
                    {formatTime(seg.start_time)}
                  </button>
                </div>
                <p
                  className={cn(
                    "text-sm leading-relaxed",
                    isActive ? "text-fg font-medium" : "text-muted"
                  )}
                >
                  {seg.text}
                </p>
              </div>
            </div>
          );
        }

        const msg = entry.data;
        return (
          <div
            key={`chat-${msg.id}`}
            className="flex gap-3 p-3 rounded-xl bg-purple-500/10 ring-1 ring-purple-500/20"
          >
            <div className="w-7 h-7 rounded-full bg-purple-500/15 flex items-center justify-center flex-shrink-0 mt-0.5">
              <MessageSquare className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs font-semibold text-purple-400">{msg.sender || "Chat"}</span>
                {msg.timestamp != null && (
                  <button
                    onClick={() => onSeek?.(msg.timestamp!)}
                    className="text-xs text-purple-400/80 hover:text-purple-400 font-mono tabular-nums"
                  >
                    {formatTime(msg.timestamp)}
                  </button>
                )}
                {msg.platform && (
                  <span className="text-xs text-subtle capitalize">{msg.platform}</span>
                )}
              </div>
              <p className="text-sm text-muted leading-relaxed">{msg.text}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
