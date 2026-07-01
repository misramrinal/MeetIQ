"use client";

import { useState } from "react";
import { Image as ImageIcon, X, Clock } from "lucide-react";
import type { VideoFrame } from "@/lib/types";
import { formatTime } from "@/lib/utils";
import { meetingsApi } from "@/lib/api";

interface FrameGalleryProps {
  frames: VideoFrame[];
  meetingId: string;
  onSeek?: (time: number) => void;
}

export default function FrameGallery({ frames, meetingId, onSeek }: FrameGalleryProps) {
  const [selected, setSelected] = useState<VideoFrame | null>(null);

  if (frames.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-subtle">
        <ImageIcon className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No frames extracted.</p>
        <p className="text-xs mt-1">This may be an audio-only recording.</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {frames.map((frame) => (
          <div
            key={frame.id}
            onClick={() => setSelected(frame)}
            className="group relative cursor-pointer rounded-xl overflow-hidden border border-line hover:border-accent/50 transition-colors bg-panel-2"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={meetingsApi.getFrameImageUrl(meetingId, frame.id)}
              alt={`Frame at ${formatTime(frame.timestamp)}`}
              className="w-full aspect-video object-cover"
              loading="lazy"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-2">
              <span className="text-white text-xs font-mono">{formatTime(frame.timestamp)}</span>
            </div>
            {frame.ocr_text && (
              <div className="absolute top-1.5 right-1.5">
                <span className="bg-accent text-accent-fg text-xs px-1.5 py-0.5 rounded-md font-medium">
                  Text
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {selected && (
        <div
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="card overflow-hidden max-w-3xl w-full shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={meetingsApi.getFrameImageUrl(meetingId, selected.id)}
              alt={`Frame at ${formatTime(selected.timestamp)}`}
              className="w-full"
            />
            <div className="p-4">
              <div className="flex items-center justify-between mb-2">
                <button
                  onClick={() => {
                    onSeek?.(selected.timestamp);
                    setSelected(null);
                  }}
                  className="flex items-center gap-1.5 text-sm text-accent hover:opacity-80 font-medium"
                >
                  <Clock className="w-4 h-4" />
                  Jump to {formatTime(selected.timestamp)} in video
                </button>
                <button
                  onClick={() => setSelected(null)}
                  className="text-muted hover:text-fg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              {selected.ocr_text && (
                <div className="card-2 p-3 mt-2">
                  <p className="section-title mb-1">OCR Text</p>
                  <p className="text-sm text-muted">{selected.ocr_text}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
