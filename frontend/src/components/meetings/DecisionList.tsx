import { Lightbulb, User, Clock } from "lucide-react";
import type { Decision } from "@/lib/types";
import { formatTime } from "@/lib/utils";

interface DecisionListProps {
  decisions: Decision[];
  onSeek?: (time: number) => void;
}

export default function DecisionList({ decisions, onSeek }: DecisionListProps) {
  if (decisions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <Lightbulb className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No decisions extracted yet.</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      {decisions.map((d) => (
        <div
          key={d.id}
          className="card p-4 hover:border-blue-200 transition-colors"
        >
          <div className="flex items-start gap-3">
            <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <Lightbulb className="w-3.5 h-3.5 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-800 font-medium leading-relaxed">
                {d.text}
              </p>
              {d.context && (
                <p className="text-xs text-gray-500 mt-1 italic">{d.context}</p>
              )}
              <div className="flex items-center gap-3 mt-2">
                {d.made_by && (
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <User className="w-3 h-3" />
                    {d.made_by}
                  </span>
                )}
                {d.timestamp != null && (
                  <button
                    onClick={() => onSeek?.(d.timestamp!)}
                    className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 font-mono"
                  >
                    <Clock className="w-3 h-3" />
                    {formatTime(d.timestamp)}
                  </button>
                )}
                {d.confidence > 0 && (
                  <span className="text-xs text-gray-400">
                    {Math.round(d.confidence * 100)}% confidence
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
