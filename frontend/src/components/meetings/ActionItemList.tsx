"use client";

import { useState } from "react";
import { CheckSquare, User, Calendar, Clock, ChevronDown } from "lucide-react";
import type { ActionItem, ActionStatus } from "@/lib/types";
import { formatTime, formatDate, cn } from "@/lib/utils";
import { actionsApi } from "@/lib/api";
import { toast } from "sonner";

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

interface ActionItemListProps {
  items: ActionItem[];
  onSeek?: (time: number) => void;
  onUpdate?: (updated: ActionItem) => void;
}

export default function ActionItemList({ items, onSeek, onUpdate }: ActionItemListProps) {
  const [updating, setUpdating] = useState<string | null>(null);

  const handleStatusChange = async (item: ActionItem, newStatus: ActionStatus) => {
    setUpdating(item.id);
    try {
      const updated = await actionsApi.update(item.id, { status: newStatus });
      onUpdate?.(updated);
      toast.success("Action item updated");
    } catch {
      toast.error("Failed to update action item");
    } finally {
      setUpdating(null);
    }
  };

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-subtle">
        <CheckSquare className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No action items extracted yet.</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3 max-w-3xl mx-auto">
      {items.map((item) => (
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
                  "text-sm text-fg leading-relaxed",
                  item.status === "done" && "line-through text-subtle"
                )}
              >
                {item.text}
              </p>

              <div className="flex flex-wrap items-center gap-3 mt-2">
                {item.owner && (
                  <span className="flex items-center gap-1 text-xs text-muted">
                    <User className="w-3 h-3" />
                    {item.owner}
                  </span>
                )}
                {item.due_date && (
                  <span className="flex items-center gap-1 text-xs text-muted">
                    <Calendar className="w-3 h-3" />
                    {formatDate(item.due_date)}
                  </span>
                )}
                {item.timestamp != null && (
                  <button
                    onClick={() => onSeek?.(item.timestamp!)}
                    className="flex items-center gap-1 text-xs text-accent hover:opacity-80 font-mono"
                  >
                    <Clock className="w-3 h-3" />
                    {formatTime(item.timestamp)}
                  </button>
                )}

                <div className="relative ml-auto">
                  <select
                    value={item.status}
                    disabled={updating === item.id}
                    onChange={(e) => handleStatusChange(item, e.target.value as ActionStatus)}
                    className={cn(
                      "text-xs px-2.5 py-1 rounded-full font-medium appearance-none pr-6 cursor-pointer focus:outline-none",
                      STATUS_STYLES[item.status]
                    )}
                  >
                    {Object.entries(STATUS_LABELS).map(([val, label]) => (
                      <option key={val} value={val}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="w-3 h-3 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-current opacity-60" />
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
