"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckSquare, Loader2, Filter } from "lucide-react";
import { actionsApi } from "@/lib/api";
import { formatDate, formatTime, cn } from "@/lib/utils";
import { toast } from "sonner";
import Link from "next/link";
import type { ActionItem, ActionStatus } from "@/lib/types";

const STATUS_STYLES: Record<ActionStatus, string> = {
  open: "bg-yellow-50 text-yellow-700 border-yellow-200",
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  done: "bg-green-50 text-green-700 border-green-200",
  cancelled: "bg-gray-50 text-gray-500 border-gray-200",
};

const STATUS_LABELS: Record<ActionStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  done: "Done",
  cancelled: "Cancelled",
};

export default function ActionsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<ActionStatus | "all">("all");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [updating, setUpdating] = useState<string | null>(null);

  const { data: actions = [], isLoading } = useQuery({
    queryKey: ["actions"],
    queryFn: () => actionsApi.list(),
  });

  const owners = Array.from(new Set(actions.map((a) => a.owner).filter(Boolean))) as string[];

  const filtered = actions.filter((a) => {
    const matchStatus = statusFilter === "all" || a.status === statusFilter;
    const matchOwner = !ownerFilter || a.owner === ownerFilter;
    return matchStatus && matchOwner;
  });

  const handleStatusChange = async (item: ActionItem, newStatus: ActionStatus) => {
    setUpdating(item.id);
    try {
      const updated = await actionsApi.update(item.id, { status: newStatus });
      queryClient.setQueryData(["actions"], (old: ActionItem[] = []) =>
        old.map((a) => (a.id === updated.id ? updated : a))
      );
      toast.success("Updated");
    } catch {
      toast.error("Failed to update");
    } finally {
      setUpdating(null);
    }
  };

  const openCount = actions.filter((a) => a.status === "open").length;
  const doneCount = actions.filter((a) => a.status === "done").length;

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Action Items</h1>
        <p className="text-gray-500 text-sm">
          {openCount} open · {doneCount} done · {actions.length} total
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        <Filter className="w-4 h-4 text-gray-400" />

        {/* Status filter */}
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          {(["all", "open", "in_progress", "done", "cancelled"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors capitalize",
                statusFilter === s
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              )}
            >
              {s === "all" ? "All" : STATUS_LABELS[s as ActionStatus]}
            </button>
          ))}
        </div>

        {/* Owner filter */}
        {owners.length > 0 && (
          <select
            value={ownerFilter}
            onChange={(e) => setOwnerFilter(e.target.value)}
            className="input w-auto text-xs"
          >
            <option value="">All owners</option>
            {owners.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        )}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <CheckSquare className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No action items found</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((item) => (
            <div
              key={item.id}
              className={cn(
                "card p-4 transition-opacity",
                item.status === "done" && "opacity-60"
              )}
            >
              <div className="flex items-start gap-3">
                <CheckSquare
                  className={cn(
                    "w-4 h-4 flex-shrink-0 mt-0.5",
                    item.status === "done" ? "text-green-500" : "text-gray-400"
                  )}
                />
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "text-sm text-gray-800",
                      item.status === "done" && "line-through text-gray-400"
                    )}
                  >
                    {item.text}
                  </p>
                  <div className="flex flex-wrap items-center gap-3 mt-2">
                    {item.owner && (
                      <span className="text-xs text-gray-500">{item.owner}</span>
                    )}
                    {item.due_date && (
                      <span className="text-xs text-gray-400">{formatDate(item.due_date)}</span>
                    )}
                    <Link
                      href={`/meetings/${item.meeting_id}`}
                      className="text-xs text-blue-500 hover:text-blue-700"
                    >
                      View meeting →
                    </Link>
                  </div>
                </div>

                {/* Status selector */}
                <select
                  value={item.status}
                  disabled={updating === item.id}
                  onChange={(e) => handleStatusChange(item, e.target.value as ActionStatus)}
                  className={cn(
                    "text-xs px-2 py-1 rounded-full border font-medium appearance-none cursor-pointer",
                    "focus:outline-none",
                    STATUS_STYLES[item.status]
                  )}
                >
                  {Object.entries(STATUS_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
