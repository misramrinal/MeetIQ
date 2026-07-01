"use client";

import { useState } from "react";
import { Search, Image as ImageIcon, MessageSquare, Loader2, ExternalLink, Sparkles } from "lucide-react";
import { searchApi, meetingsApi } from "@/lib/api";
import { formatTime, cn } from "@/lib/utils";
import { toast } from "sonner";
import Link from "next/link";
import type { SearchResponse, VisualSearchResponse } from "@/lib/types";

type SearchMode = "text" | "visual";

const sourceLabel = (type: string) => {
  switch (type) {
    case "action_item":
      return "Action item";
    case "decision":
      return "Decision";
    case "chat":
      return "Chat";
    case "frame":
      return "Frame";
    default:
      return "Transcript";
  }
};

const resultStatusLabel = (result: SearchResponse) => {
  if (result.status === "answered") return `${Math.round(result.confidence * 100)}% confidence`;
  if (result.status === "non_search") return "Ready for a meeting question";
  if (result.status === "llm_error") return "Answer generation failed";
  return "No matching evidence";
};

export default function SearchPage() {
  const [mode, setMode] = useState<SearchMode>("text");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [textResult, setTextResult] = useState<SearchResponse | null>(null);
  const [visualResult, setVisualResult] = useState<VisualSearchResponse | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setTextResult(null);
    setVisualResult(null);
    try {
      if (mode === "text") {
        setTextResult(await searchApi.text(query.trim()));
      } else {
        setVisualResult(await searchApi.visual(query.trim()));
      }
    } catch {
      toast.error("Search failed. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-5xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="relative overflow-hidden rounded-3xl border border-line mb-8">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 to-blue-900/80" />
        <div className="absolute inset-0 bg-[radial-gradient(30rem_16rem_at_0%_0%,rgba(34,211,238,0.25),transparent_60%)]" />
        <div className="relative px-6 md:px-8 py-8">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-cyan-100">
            <Sparkles className="w-3.5 h-3.5" /> Ask MeetIQ
          </span>
          <h1 className="mt-3 text-2xl md:text-3xl font-bold text-white tracking-tight">
            Search meeting memory
          </h1>
          <p className="mt-2 text-slate-200/90 text-sm max-w-2xl">
            Ask cited questions across transcripts, decisions, action items, chats, and visual frames.
          </p>
        </div>
      </div>

      {/* Mode toggle */}
      <div className="flex items-center gap-1 card-2 p-1 w-fit mb-5">
        <button
          onClick={() => setMode("text")}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            mode === "text" ? "bg-accent text-accent-fg shadow-sm" : "text-muted hover:text-fg"
          )}
        >
          <MessageSquare className="w-4 h-4" /> Text Search
        </button>
        <button
          onClick={() => setMode("visual")}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            mode === "visual" ? "bg-accent text-accent-fg shadow-sm" : "text-muted hover:text-fg"
          )}
        >
          <ImageIcon className="w-4 h-4" /> Visual Search
        </button>
      </div>

      {/* Input */}
      <div className="flex flex-col sm:flex-row gap-2 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-subtle" />
          <input
            type="text"
            className="input pl-9"
            placeholder={
              mode === "text"
                ? "What did we decide about the database?"
                : "database schema diagram, code editor, whiteboard..."
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>
        <button onClick={handleSearch} disabled={!query.trim() || loading} className="btn-primary px-5">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
      </div>

      {/* Text result */}
      {textResult && (
        <div className="space-y-4 animate-slide-up">
          <div className="card p-6 border-l-4 border-l-accent">
            <div className="flex items-center justify-between gap-3 mb-2">
              <p className="section-title text-accent">Answer</p>
              <span className="text-xs text-subtle">{resultStatusLabel(textResult)}</span>
            </div>
            <p className="text-fg leading-relaxed">{textResult.answer}</p>
          </div>

          {textResult.sources.length > 0 && (
            <div className="space-y-2">
              <p className="section-title">Sources</p>
              {textResult.sources.map((src, i) => (
                <div key={i} className="card p-4 hover:border-accent/40 transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="chip">{sourceLabel(src.type)}</span>
                        {src.speaker && (
                          <span className="text-xs font-semibold text-accent">{src.speaker}</span>
                        )}
                        {src.start_time != null && (
                          <span className="text-xs text-subtle font-mono">
                            at {formatTime(src.start_time)}
                          </span>
                        )}
                        <span className="text-xs text-subtle">
                          {(src.score * 100).toFixed(0)}% match
                        </span>
                      </div>
                      <p className="text-sm text-muted leading-relaxed">{src.text}</p>
                      {src.type === "action_item" && (
                        <p className="text-xs text-subtle mt-1">
                          {src.owner ? `Owner: ${src.owner}` : "Owner: unassigned"}
                          {src.due_date ? ` · Due: ${src.due_date}` : ""}
                          {src.status ? ` · Status: ${src.status}` : ""}
                        </p>
                      )}
                      {src.type === "decision" && src.made_by && (
                        <p className="text-xs text-subtle mt-1">Made by: {src.made_by}</p>
                      )}
                      {src.meeting_title && (
                        <p className="text-xs text-subtle mt-1">{src.meeting_title}</p>
                      )}
                    </div>
                    {src.meeting_id && (
                      <Link
                        href={`/meetings/${src.meeting_id}`}
                        className="text-subtle hover:text-accent flex-shrink-0"
                        title="Open meeting"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Visual result */}
      {visualResult && (
        <div className="space-y-4 animate-slide-up">
          <p className="section-title">
            {visualResult.frames.length} frame{visualResult.frames.length !== 1 ? "s" : ""} found
          </p>
          {visualResult.frames.length === 0 ? (
            <div className="card p-8 text-center text-subtle">
              <ImageIcon className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No matching frames found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {visualResult.frames.map((frame, i) => (
                <div key={i} className="card overflow-hidden hover:border-accent/40 transition-colors">
                  {frame.meeting_id && frame.frame_id && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={meetingsApi.getFrameImageUrl(frame.meeting_id, frame.frame_id)}
                      alt={`Frame at ${frame.timestamp != null ? formatTime(frame.timestamp) : "?"}`}
                      className="w-full aspect-video object-cover bg-panel-2"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  )}
                  <div className="p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono text-subtle">
                        {frame.timestamp != null ? formatTime(frame.timestamp) : "-"}
                      </span>
                      <span className="text-xs text-subtle">
                        {(frame.score * 100).toFixed(0)}% match
                      </span>
                    </div>
                    {frame.ocr_text && (
                      <p className="text-xs text-muted line-clamp-2">{frame.ocr_text}</p>
                    )}
                    {frame.meeting_id && (
                      <Link
                        href={`/meetings/${frame.meeting_id}`}
                        className="flex items-center gap-1 text-xs text-accent hover:opacity-80 mt-2"
                      >
                        <ExternalLink className="w-3 h-3" />
                        {frame.meeting_title || "Open meeting"}
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!textResult && !visualResult && !loading && (
        <div className="card p-12 text-center border-dashed">
          <div className="w-14 h-14 rounded-2xl bg-accent/10 ring-1 ring-accent/20 flex items-center justify-center mx-auto mb-4">
            <Search className="w-7 h-7 text-accent" />
          </div>
          <p className="text-fg font-semibold">Ask anything about your meetings</p>
          <p className="text-subtle text-xs mt-1 max-w-md mx-auto">
            {mode === "text"
              ? "e.g. What database did we decide to use? or Who is responsible for the API docs?"
              : "e.g. database schema diagram or code editor with Python"}
          </p>
        </div>
      )}
    </div>
  );
}
