"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  Video,
  CheckSquare,
  Lightbulb,
  Upload,
  ArrowRight,
  Loader2,
  Search,
  Sparkles,
} from "lucide-react";
import { meetingsApi, actionsApi, decisionsApi } from "@/lib/api";
import MeetingCard from "@/components/meetings/MeetingCard";

export default function DashboardPage() {
  const { data: meetings = [], isLoading: loadingMeetings } = useQuery({
    queryKey: ["meetings"],
    queryFn: () => meetingsApi.list(0, 20),
  });

  const { data: actions = [] } = useQuery({
    queryKey: ["actions"],
    queryFn: () => actionsApi.list(),
  });

  const { data: decisions = [] } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => decisionsApi.list(),
  });

  const doneMeetings = meetings.filter((m) => m.status === "done").length;
  const openActions = actions.filter((a) => a.status === "open").length;
  const recentMeetings = meetings.slice(0, 6);

  const stats = [
    { label: "Meetings", value: meetings.length, icon: Video, tint: "text-blue-400", ring: "ring-blue-500/20 bg-blue-500/10" },
    { label: "Processed", value: doneMeetings, icon: Sparkles, tint: "text-emerald-400", ring: "ring-emerald-500/20 bg-emerald-500/10" },
    { label: "Open Actions", value: openActions, icon: CheckSquare, tint: "text-amber-400", ring: "ring-amber-500/20 bg-amber-500/10" },
    { label: "Decisions", value: decisions.length, icon: Lightbulb, tint: "text-purple-400", ring: "ring-purple-500/20 bg-purple-500/10" },
  ];

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto animate-fade-in">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-3xl border border-line mb-8">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-blue-700 to-slate-900" />
        <div className="absolute inset-0 bg-[radial-gradient(40rem_20rem_at_100%_0%,rgba(34,211,238,0.35),transparent_60%)]" />
        <div className="relative px-6 md:px-10 py-10">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="max-w-2xl">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-cyan-100 backdrop-blur">
                <Sparkles className="w-3.5 h-3.5" /> MeetIQ workspace
              </span>
              <h1 className="mt-4 text-3xl md:text-4xl font-bold text-white tracking-tight">
                Turn meetings into searchable intelligence.
              </h1>
              <p className="mt-3 text-slate-200/90 text-sm md:text-base leading-relaxed">
                Upload recordings, auto-extract decisions and action items, and ask
                cited questions across every conversation.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Link
                href="/search"
                className="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2 text-sm font-semibold text-white backdrop-blur hover:bg-white/20 transition-colors"
              >
                <Search className="w-4 h-4" /> Search
              </Link>
              <Link
                href="/upload"
                className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-100 transition-colors shadow-lg"
              >
                <Upload className="w-4 h-4" /> Upload Meeting
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-10">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="card p-5 hover:-translate-y-0.5 hover:shadow-glow transition-all duration-200"
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="section-title">{stat.label}</p>
                <p className="text-3xl font-bold text-fg mt-2">{stat.value}</p>
              </div>
              <div className={`w-12 h-12 rounded-2xl ring-1 flex items-center justify-center ${stat.ring}`}>
                <stat.icon className={`w-5 h-5 ${stat.tint}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Meetings */}
      <div className="flex items-end justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-fg">Recent meetings</h2>
          <p className="text-sm text-muted">The latest recordings processed by MeetIQ.</p>
        </div>
        <Link
          href="/meetings"
          className="inline-flex items-center gap-1 text-sm font-semibold text-accent hover:opacity-80"
        >
          View all <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {loadingMeetings ? (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card p-5">
              <div className="skeleton h-5 w-2/3 mb-3" />
              <div className="skeleton h-3 w-full mb-2" />
              <div className="skeleton h-3 w-4/5" />
            </div>
          ))}
        </div>
      ) : recentMeetings.length === 0 ? (
        <div className="card p-12 text-center border-dashed">
          <div className="w-14 h-14 rounded-2xl bg-blue-500/10 ring-1 ring-blue-500/20 flex items-center justify-center mx-auto mb-4">
            <Video className="w-7 h-7 text-blue-400" />
          </div>
          <p className="text-fg font-semibold">No meetings yet</p>
          <p className="text-muted text-sm mt-1">
            Upload your first meeting recording to get started.
          </p>
          <Link href="/upload" className="btn-primary mt-5">
            <Upload className="w-4 h-4" /> Upload Meeting
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {recentMeetings.map((m) => (
            <MeetingCard key={m.id} meeting={m} />
          ))}
        </div>
      )}
    </div>
  );
}
