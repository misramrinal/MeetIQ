"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Video, CheckSquare, Lightbulb, Upload, ArrowRight, Loader2 } from "lucide-react";
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
    {
      label: "Total Meetings",
      value: meetings.length,
      icon: Video,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      label: "Processed",
      value: doneMeetings,
      icon: Video,
      color: "text-green-600",
      bg: "bg-green-50",
    },
    {
      label: "Open Actions",
      value: openActions,
      icon: CheckSquare,
      color: "text-orange-600",
      bg: "bg-orange-50",
    },
    {
      label: "Decisions Made",
      value: decisions.length,
      icon: Lightbulb,
      color: "text-purple-600",
      bg: "bg-purple-50",
    },
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">
            Your meeting intelligence overview
          </p>
        </div>
        <Link href="/upload" className="btn-primary flex items-center gap-2">
          <Upload className="w-4 h-4" />
          Upload Meeting
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <div key={stat.label} className="card p-5">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 ${stat.bg} rounded-lg flex items-center justify-center`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                <p className="text-xs text-gray-500">{stat.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Meetings */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Recent Meetings</h2>
        <Link
          href="/meetings"
          className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
        >
          View all <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {loadingMeetings ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        </div>
      ) : recentMeetings.length === 0 ? (
        <div className="card p-12 text-center">
          <Video className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No meetings yet</p>
          <p className="text-gray-400 text-sm mt-1">
            Upload your first meeting recording to get started.
          </p>
          <Link href="/upload" className="btn-primary inline-flex items-center gap-2 mt-4">
            <Upload className="w-4 h-4" />
            Upload Meeting
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {recentMeetings.map((m) => (
            <MeetingCard key={m.id} meeting={m} />
          ))}
        </div>
      )}
    </div>
  );
}
