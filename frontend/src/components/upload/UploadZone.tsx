"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileVideo, FileAudio, X, CheckCircle2, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { meetingsApi } from "@/lib/api";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

const ACCEPTED = ".mp4,.mov,.webm,.mkv,.avi,.mp3,.wav,.m4a,.ogg,.flac";
const ACCEPTED_CHAT = ".json,.txt,.log";
const MAX_MB = 500;

export default function UploadZone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [chatFile, setChatFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleFile = (f: File) => {
    if (f.size > MAX_MB * 1024 * 1024) {
      toast.error(`File too large. Maximum size is ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    if (!title) {
      setTitle(f.name.replace(/\.[^.]+$/, ""));
    }
  };

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [title]
  );

  const handleSubmit = async () => {
    if (!file || !title.trim()) {
      toast.error("Please provide a title and select a file.");
      return;
    }
    setUploading(true);
    setProgress(0);
    try {
      const result = await meetingsApi.upload(title.trim(), file, setProgress);
      if (chatFile) {
        try {
          const chatResult = await meetingsApi.uploadChat(result.meeting_id, chatFile);
          toast.success(`Meeting uploaded! ${chatResult.inserted} chat messages attached.`);
        } catch {
          toast.warning("Meeting uploaded but chat log attachment failed.");
        }
      } else {
        toast.success("Meeting uploaded! Processing has started.");
      }
      router.push(`/meetings/${result.meeting_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      toast.error(msg);
      setUploading(false);
    }
  };

  const isVideo = file?.type.startsWith("video/");
  const isAudio = file?.type.startsWith("audio/");

  return (
    <div className="max-w-xl mx-auto space-y-5">
      {/* Title input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          Meeting Title <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          className="input"
          placeholder="e.g. Q3 Product Planning"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={uploading}
        />
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-xl p-10 text-center transition-all duration-200 cursor-pointer",
          dragging
            ? "border-blue-500 bg-blue-50"
            : file
            ? "border-green-400 bg-green-50"
            : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />

        {file ? (
          <div className="flex flex-col items-center gap-2">
            {isVideo ? (
              <FileVideo className="w-10 h-10 text-green-500" />
            ) : isAudio ? (
              <FileAudio className="w-10 h-10 text-green-500" />
            ) : (
              <CheckCircle2 className="w-10 h-10 text-green-500" />
            )}
            <p className="font-medium text-gray-800 text-sm">{file.name}</p>
            <p className="text-xs text-gray-500">
              {(file.size / 1024 / 1024).toFixed(1)} MB
            </p>
            {!uploading && (
              <button
                onClick={(e) => { e.stopPropagation(); setFile(null); }}
                className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 mt-1"
              >
                <X className="w-3 h-3" /> Remove
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 bg-blue-50 rounded-full flex items-center justify-center">
              <Upload className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <p className="font-medium text-gray-700 text-sm">
                Drop your meeting recording here
              </p>
              <p className="text-xs text-gray-400 mt-1">
                or click to browse — MP4, MOV, MP3, WAV and more (max {MAX_MB} MB)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Chat log (optional) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          Chat Log <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <div
          onClick={() => !uploading && chatInputRef.current?.click()}
          className={cn(
            "border border-dashed rounded-lg p-4 flex items-center gap-3 cursor-pointer transition-colors",
            chatFile
              ? "border-green-400 bg-green-50"
              : "border-gray-200 hover:border-blue-300 hover:bg-gray-50"
          )}
        >
          <input
            ref={chatInputRef}
            type="file"
            accept={ACCEPTED_CHAT}
            className="hidden"
            onChange={(e) => setChatFile(e.target.files?.[0] ?? null)}
          />
          <MessageSquare className={cn("w-5 h-5 flex-shrink-0", chatFile ? "text-green-500" : "text-gray-400")} />
          <div className="flex-1 min-w-0">
            {chatFile ? (
              <p className="text-sm text-gray-800 truncate">{chatFile.name}</p>
            ) : (
              <p className="text-sm text-gray-500">Attach Slack JSON, Zoom, or plain text chat log</p>
            )}
          </div>
          {chatFile && !uploading && (
            <button
              onClick={(e) => { e.stopPropagation(); setChatFile(null); }}
              className="text-red-400 hover:text-red-600 flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {uploading && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-gray-500">
            <span>{progress < 100 ? "Uploading…" : "Processing started…"}</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={!file || !title.trim() || uploading}
        className="btn-primary w-full flex items-center justify-center gap-2"
      >
        <Upload className="w-4 h-4" />
        {uploading ? "Uploading…" : "Upload and Process"}
      </button>
    </div>
  );
}
