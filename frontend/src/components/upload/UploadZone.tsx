"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, FileVideo, FileAudio, X, CheckCircle2, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { getApiErrorMessage, meetingsApi } from "@/lib/api";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

const ACCEPTED = ".mp4,.mov,.webm,.mkv,.avi,.mp3,.wav,.m4a,.ogg,.flac";
const ACCEPTED_CHAT = ".json,.txt,.log,.csv";
const MAX_MB = 2048;
const MAX_LABEL = MAX_MB >= 1024 ? `${(MAX_MB / 1024).toFixed(0)} GB` : `${MAX_MB} MB`;

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
      const sizeLabel = (f.size / 1024 / 1024 / 1024).toFixed(2);
      toast.error(`File too large (${sizeLabel} GB). Maximum upload size is ${MAX_LABEL}.`);
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
        } catch (err: unknown) {
          toast.warning(`Meeting uploaded but chat log attachment failed: ${getApiErrorMessage(err)}`);
        }
      } else {
        toast.success("Meeting uploaded! Processing has started.");
      }
      router.push(`/meetings/${result.meeting_id}`);
    } catch (err: unknown) {
      toast.error(getApiErrorMessage(err, "Upload failed"));
      setUploading(false);
    }
  };

  const isVideo = file?.type.startsWith("video/");
  const isAudio = file?.type.startsWith("audio/");

  return (
    <div className="max-w-xl mx-auto space-y-5">
      {/* Title */}
      <div>
        <label className="block text-sm font-medium text-fg mb-1.5">
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
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 cursor-pointer",
          dragging
            ? "border-accent bg-accent/5 scale-[1.01]"
            : file
            ? "border-emerald-500/50 bg-emerald-500/5"
            : "border-line hover:border-accent/60 hover:bg-panel-2"
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
              <FileVideo className="w-10 h-10 text-emerald-400" />
            ) : isAudio ? (
              <FileAudio className="w-10 h-10 text-emerald-400" />
            ) : (
              <CheckCircle2 className="w-10 h-10 text-emerald-400" />
            )}
            <p className="font-medium text-fg text-sm">{file.name}</p>
            <p className="text-xs text-muted">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
            {!uploading && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                }}
                className="flex items-center gap-1 text-xs text-red-500 hover:text-red-400 mt-1"
              >
                <X className="w-3 h-3" /> Remove
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 bg-gradient-to-br from-blue-500/15 to-cyan-500/15 ring-1 ring-blue-500/20 rounded-2xl flex items-center justify-center">
              <Upload className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <p className="font-semibold text-fg text-sm">Drop your meeting recording here</p>
              <p className="text-xs text-subtle mt-1">
                or click to browse — MP4, MOV, MP3, WAV and more (max {MAX_LABEL})
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Chat log (optional) */}
      <div>
        <label className="block text-sm font-medium text-fg mb-1.5">
          Chat Log <span className="text-subtle font-normal">(optional)</span>
        </label>
        <div
          onClick={() => !uploading && chatInputRef.current?.click()}
          className={cn(
            "border border-dashed rounded-xl p-4 flex items-center gap-3 cursor-pointer transition-colors",
            chatFile
              ? "border-emerald-500/50 bg-emerald-500/5"
              : "border-line hover:border-accent/50 hover:bg-panel-2"
          )}
        >
          <input
            ref={chatInputRef}
            type="file"
            accept={ACCEPTED_CHAT}
            className="hidden"
            onChange={(e) => setChatFile(e.target.files?.[0] ?? null)}
          />
          <MessageSquare
            className={cn("w-5 h-5 flex-shrink-0", chatFile ? "text-emerald-400" : "text-subtle")}
          />
          <div className="flex-1 min-w-0">
            {chatFile ? (
              <p className="text-sm text-fg truncate">{chatFile.name}</p>
            ) : (
              <p className="text-sm text-muted">Attach Slack JSON, Zoom, or plain text chat log</p>
            )}
          </div>
          {chatFile && !uploading && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setChatFile(null);
              }}
              className="text-red-500 hover:text-red-400 flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress */}
      {uploading && (
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-muted">
            <span>{progress < 100 ? "Uploading…" : "Processing started…"}</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-panel-2 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-blue-600 to-cyan-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={!file || !title.trim() || uploading}
        className="btn-primary w-full"
      >
        <Upload className="w-4 h-4" />
        {uploading ? "Uploading…" : "Upload and Process"}
      </button>
    </div>
  );
}
