"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckSquare, Loader2, Filter } from "lucide-react";
import { actionsApi } from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import { toast } from "sonner";
import Link from "next/link";
import PageHeader from "@/components/layout/PageHeader";
import type { ActionItem, ActionStatus } from "@/lib/types";

const STATUS_STYLES: Record<ActionStatus, string> = {
  open: "bg-amber-500/10 text-amber-500 ring-1 ring-amber-500/20",
  in_progress: "bg-blue-500/10 text-blue-400 ring-1 ring-blue-500/20",
  done: "bg-emerald-500/10 text-emerald-500 ring-1 ring-emerald-500/20",
  cancelled: "bg-panel-2 text-subtle ring-1 ring-line",
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
    <div className="p-6 md:p-8 max-w-4xl mx-auto animate-fade-in">
      <PageHeader
        eyebrow="Tracker"
        title="Action Items"
        subtitle={`${openCount} open · ${doneCount} done · ${actions.length} total`}
      />

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <Filter className="w-4 h-4 text-subtle" />
        <div className="flex items-center gap-1 card-2 p-1 overflow-x-auto">
          {(["all", "open", "in_progress", "done", "cancelled"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap",
                statusFilter === s ? "bg-accent text-accent-fg shadow-sm" : "text-muted hover:text-fg"
              )}
            >
              {s === "all" ? "All" : STATUS_LABELS[s as ActionStatus]}
            </button>
          ))}
        </div>
        {owners.length > 0 && (
          <select
            value={ownerFilter}
            onChange={(e) => setOwnerFilter(e.target.value)}
            className="input w-auto text-xs"
          >
            <option value="">All owners</option>
            {owners.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center border-dashed">
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 ring-1 ring-amber-500/20 flex items-center justify-center mx-auto mb-4">
            <CheckSquare className="w-7 h-7 text-amber-400" />
          </div>
          <p className="text-fg font-semibold">No action items found</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((item) => (
            <div
              key={item.id}
              className={cn("card p-4 transition-opacity", item.status === "done" && "opacity-60")}
            >
              <div className="flex items-start gap-3">
                <CheckSquare
                  className={cn(
                    "w-4 h-4 flex-shrink-0 mt-0.5",
                    item.status === "done" ? "text-emerald-500" : "text-subtle"
                  )}
                />
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "text-sm text-fg",
                      item.status === "done" && "line-through text-subtle"
                    )}
                  >
                    {item.text}
                  </p>
                  <div className="flex flex-wrap items-center gap-3 mt-2">
                    {item.owner && <span className="text-xs text-muted">{item.owner}</span>}
                    {item.due_date && (
                      <span className="text-xs text-subtle">{formatDate(item.due_date)}</span>
                    )}
                    <Link
                      href={`/meetings/${item.meeting_id}`}
                      className="text-xs text-accent hover:opacity-80"
                    >
                      View meeting →
                    </Link>
                  </div>
                </div>

                <select
                  value={item.status}
                  disabled={updating === item.id}
                  onChange={(e) => handleStatusChange(item, e.target.value as ActionStatus)}
                  className={cn(
                    "text-xs px-2.5 py-1 rounded-full font-medium appearance-none cursor-pointer focus:outline-none",
                    STATUS_STYLES[item.status]
                  )}
                >
                  {Object.entries(STATUS_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>
                      {label}
                    </option>
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
