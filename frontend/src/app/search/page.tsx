"use client";

import { useState } from "react";
import { Search, Image as ImageIcon, MessageSquare, Loader2, ExternalLink } from "lucide-react";
import { searchApi, meetingsApi } from "@/lib/api";
import { formatTime, cn } from "@/lib/utils";
import { toast } from "sonner";
import Link from "next/link";
import type { SearchResponse, VisualSearchResponse } from "@/lib/types";

type SearchMode = "text" | "visual";

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
        const r = await searchApi.text(query.trim());
        setTextResult(r);
      } else {
        const r = await searchApi.visual(query.trim());
        setVisualResult(r);
      }
    } catch {
      toast.error("Search failed. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Search</h1>
        <p className="text-gray-500 text-sm">
          Ask questions across all your meetings or search for visual content.
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 w-fit mb-5">
        <button
          onClick={() => setMode("text")}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-colors",
            mode === "text" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
          )}
        >
          <MessageSquare className="w-4 h-4" />
          Text Search
        </button>
        <button
          onClick={() => setMode("visual")}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-colors",
            mode === "visual" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
          )}
        >
          <ImageIcon className="w-4 h-4" />
          Visual Search
        </button>
      </div>

      {/* Search input */}
      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            className="input pl-9 text-sm"
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
        <button
          onClick={handleSearch}
          disabled={!query.trim() || loading}
          className="btn-primary flex items-center gap-2 px-5"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
      </div>

      {/* Text search result */}
      {textResult && (
        <div className="space-y-4 animate-fade-in">
          {/* Answer */}
          <div className="card p-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Answer</p>
            <p className="text-gray-800 leading-relaxed">{textResult.answer}</p>
          </div>

          {/* Sources */}
          {textResult.sources.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Sources</p>
              {textResult.sources.map((src, i) => (
                <div key={i} className="card p-4 hover:border-blue-200 transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        {src.speaker && (
                          <span className="text-xs font-semibold text-blue-600">{src.speaker}</span>
                        )}
                        {src.start_time != null && (
                          <span className="text-xs text-gray-400 font-mono">
                            at {formatTime(src.start_time)}
                          </span>
                        )}
                        <span className="text-xs text-gray-300">
                          {(src.score * 100).toFixed(0)}% match
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 leading-relaxed">{src.text}</p>
                      {src.meeting_title && (
                        <p className="text-xs text-gray-400 mt-1">{src.meeting_title}</p>
                      )}
                    </div>
                    {src.meeting_id && (
                      <Link
                        href={`/meetings/${src.meeting_id}`}
                        className="text-gray-400 hover:text-blue-500 flex-shrink-0"
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

      {/* Visual search result */}
      {visualResult && (
        <div className="space-y-4 animate-fade-in">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            {visualResult.frames.length} frame{visualResult.frames.length !== 1 ? "s" : ""} found
          </p>
          {visualResult.frames.length === 0 ? (
            <div className="card p-8 text-center text-gray-400">
              <ImageIcon className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No matching frames found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {visualResult.frames.map((frame, i) => (
                <div key={i} className="card overflow-hidden hover:border-blue-200 transition-colors">
                  {frame.meeting_id && (frame.frame_id || frame.frame_path) && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={
                        frame.meeting_id && frame.frame_id
                          ? meetingsApi.getFrameImageUrl(frame.meeting_id, frame.frame_id)
                          : undefined
                      }
                      alt={`Frame at ${frame.timestamp != null ? formatTime(frame.timestamp) : "?"}`}
                      className="w-full aspect-video object-cover bg-gray-100"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                  )}
                  <div className="p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono text-gray-500">
                        {frame.timestamp != null ? formatTime(frame.timestamp) : "-"}
                      </span>
                      <span className="text-xs text-gray-400">
                        {(frame.score * 100).toFixed(0)}% match
                      </span>
                    </div>
                    {frame.ocr_text && (
                      <p className="text-xs text-gray-600 line-clamp-2">{frame.ocr_text}</p>
                    )}
                    {frame.meeting_id && (
                      <Link
                        href={`/meetings/${frame.meeting_id}`}
                        className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 mt-2"
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
        <div className="text-center py-16 text-gray-400">
          <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm font-medium">Ask anything about your meetings</p>
          <p className="text-xs mt-1">
            {mode === "text"
              ? "e.g. What database did we decide to use? or Who is responsible for the API docs?"
              : "e.g. database schema diagram or code editor with Python"}
          </p>
        </div>
      )}
    </div>
  );
}
