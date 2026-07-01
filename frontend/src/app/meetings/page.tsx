"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Video, Upload, Search, Loader2 } from "lucide-react";
import { meetingsApi } from "@/lib/api";
import MeetingCard from "@/components/meetings/MeetingCard";
import PageHeader from "@/components/layout/PageHeader";
import { cn } from "@/lib/utils";
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
    refetchInterval: 5000,
  });

  const filtered = meetings.filter((m) => {
    const matchStatus = statusFilter === "all" || m.status === statusFilter;
    const matchSearch = m.title.toLowerCase().includes(search.toLowerCase());
    return matchStatus && matchSearch;
  });

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto animate-fade-in">
      <PageHeader
        eyebrow="Library"
        title="Meetings"
        subtitle={`${meetings.length} meeting${meetings.length !== 1 ? "s" : ""} total`}
        actions={
          <Link href="/upload" className="btn-primary">
            <Upload className="w-4 h-4" /> Upload Meeting
          </Link>
        }
      />

      {/* Filters */}
      <div className="flex flex-col md:flex-row md:items-center gap-3 mb-6">
        <div className="relative flex-1 md:max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-subtle" />
          <input
            type="text"
            className="input pl-9"
            placeholder="Search meetings…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-1 card-2 p-1 overflow-x-auto">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap",
                statusFilter === f.value
                  ? "bg-accent text-accent-fg shadow-sm"
                  : "text-muted hover:text-fg"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center border-dashed">
          <div className="w-14 h-14 rounded-2xl bg-blue-500/10 ring-1 ring-blue-500/20 flex items-center justify-center mx-auto mb-4">
            <Video className="w-7 h-7 text-blue-400" />
          </div>
          <p className="text-fg font-semibold">
            {search || statusFilter !== "all"
              ? "No meetings match your filters"
              : "No meetings yet"}
          </p>
          {!search && statusFilter === "all" && (
            <Link href="/upload" className="btn-primary mt-5">
              <Upload className="w-4 h-4" /> Upload your first meeting
            </Link>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {filtered.map((m) => (
            <MeetingCard key={m.id} meeting={m} />
          ))}
        </div>
      )}
    </div>
  );
}
