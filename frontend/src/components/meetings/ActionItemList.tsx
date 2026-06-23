"use client";

import { useState } from "react";
import { CheckSquare, User, Calendar, Clock, ChevronDown } from "lucide-react";
import type { ActionItem, ActionStatus } from "@/lib/types";
import { formatTime, formatDate, cn } from "@/lib/utils";
import { actionsApi } from "@/lib/api";
import { toast } from "sonner";

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

interface ActionItemListProps {
  items: ActionItem[];
  onSeek?: (time: number) => void;
  onUpdate?: (updated: ActionItem) => void;
}

export default function ActionItemList({
  items,
  onSeek,
  onUpdate,
}: ActionItemListProps) {
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
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <CheckSquare className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No action items extracted yet.</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      {items.map((item) => (
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
                  "text-sm text-gray-800 leading-relaxed",
                  item.status === "done" && "line-through text-gray-400"
                )}
              >
                {item.text}
              </p>

              <div className="flex flex-wrap items-center gap-3 mt-2">
                {item.owner && (
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <User className="w-3 h-3" />
                    {item.owner}
                  </span>
                )}
                {item.due_date && (
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <Calendar className="w-3 h-3" />
                    {formatDate(item.due_date)}
                  </span>
                )}
                {item.timestamp != null && (
                  <button
                    onClick={() => onSeek?.(item.timestamp!)}
                    className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 font-mono"
                  >
                    <Clock className="w-3 h-3" />
                    {formatTime(item.timestamp)}
                  </button>
                )}

                {/* Status selector */}
                <div className="relative ml-auto">
                  <select
                    value={item.status}
                    disabled={updating === item.id}
                    onChange={(e) =>
                      handleStatusChange(item, e.target.value as ActionStatus)
                    }
                    className={cn(
                      "text-xs px-2 py-1 rounded-full border font-medium appearance-none pr-6 cursor-pointer",
                      "focus:outline-none focus:ring-1 focus:ring-blue-400",
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
