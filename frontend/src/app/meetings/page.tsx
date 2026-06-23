"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Video, Upload, Search, Loader2 } from "lucide-react";
import { meetingsApi } from "@/lib/api";
import MeetingCard from "@/components/meetings/MeetingCard";
import type { MeetingStatus } from "@/lib/types";

const STATUS_FILTERS: { label: string; value: MeetingStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Done", value: "done" },
  { label: "Processing", value: "processing" },
  { label: "Pending", value: "pending" },
  { label: "Failed", value: "failed" },
];

export default function MeetingsPage() {
  const [statusFilter, setStatusFilter] = useState<MeetingStatus | "all">("all");
  const [search, setSearch] = useState("");

  const { data: meetings = [], isLoading } = useQuery({
    queryKey: ["meetings"],
    queryFn: () => meetingsApi.list(0, 100),
    refetchInterval: 5000, // poll every 5s to catch processing updates
  });

  const filtered = meetings.filter((m) => {
    const matchStatus = statusFilter === "all" || m.status === statusFilter;
    const matchSearch = m.title.toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Meetings</h1>
          <p className="text-gray-500 text-sm mt-1">
            {meetings.length} meeting{meetings.length !== 1 ? "s" : ""} total
          </p>
        </div>
        <Link href="/upload" className="btn-primary flex items-center gap-2">
          <Upload className="w-4 h-4" />
          Upload Meeting
        </Link>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            className="input pl-9"
            placeholder="Search meetings…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Status tabs */}
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                statusFilter === f.value
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <Video className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">
            {search || statusFilter !== "all" ? "No meetings match your filters" : "No meetings yet"}
          </p>
          {!search && statusFilter === "all" && (
            <Link href="/upload" className="btn-primary inline-flex items-center gap-2 mt-4">
              <Upload className="w-4 h-4" />
              Upload your first meeting
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {filtered.map((m) => (
            <MeetingCard key={m.id} meeting={m} />
          ))}
        </div>
      )}
    </div>
  );
}
