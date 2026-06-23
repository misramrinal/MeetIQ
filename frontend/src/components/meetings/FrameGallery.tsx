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
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <ImageIcon className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No frames extracted.</p>
        <p className="text-xs mt-1">This may be an audio-only recording.</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="grid grid-cols-3 gap-3">
        {frames.map((frame) => (
          <div
            key={frame.id}
            onClick={() => setSelected(frame)}
            className="group relative cursor-pointer rounded-lg overflow-hidden border border-gray-200 hover:border-blue-400 transition-colors bg-gray-100"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={meetingsApi.getFrameImageUrl(meetingId, frame.id)}
              alt={`Frame at ${formatTime(frame.timestamp)}`}
              className="w-full aspect-video object-cover"
              loading="lazy"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
              <span className="text-white text-xs font-mono">
                {formatTime(frame.timestamp)}
              </span>
            </div>
            {frame.ocr_text && (
              <div className="absolute top-1 right-1">
                <span className="bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded">
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
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="bg-white rounded-xl overflow-hidden max-w-3xl w-full shadow-2xl"
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
                  className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  <Clock className="w-4 h-4" />
                  Jump to {formatTime(selected.timestamp)} in video
                </button>
                <button
                  onClick={() => setSelected(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              {selected.ocr_text && (
                <div className="bg-gray-50 rounded-lg p-3 mt-2">
                  <p className="text-xs text-gray-500 font-medium mb-1">OCR Text</p>
                  <p className="text-sm text-gray-700">{selected.ocr_text}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
