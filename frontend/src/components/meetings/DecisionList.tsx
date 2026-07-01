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
      <div className="flex flex-col items-center justify-center py-16 text-subtle">
        <Lightbulb className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No decisions extracted yet.</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3 max-w-3xl mx-auto">
      {decisions.map((d) => (
        <div key={d.id} className="card p-4 hover:border-accent/40 transition-colors">
          <div className="flex items-start gap-3">
            <div className="w-7 h-7 bg-purple-500/10 ring-1 ring-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
              <Lightbulb className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-fg font-medium leading-relaxed">{d.text}</p>
              {d.context && <p className="text-xs text-muted mt-1 italic">{d.context}</p>}
              <div className="flex flex-wrap items-center gap-3 mt-2">
                {d.made_by && (
                  <span className="flex items-center gap-1 text-xs text-muted">
                    <User className="w-3 h-3" />
                    {d.made_by}
                  </span>
                )}
                {d.timestamp != null && (
                  <button
                    onClick={() => onSeek?.(d.timestamp!)}
                    className="flex items-center gap-1 text-xs text-accent hover:opacity-80 font-mono"
                  >
                    <Clock className="w-3 h-3" />
                    {formatTime(d.timestamp)}
                  </button>
                )}
                {d.confidence > 0 && (
                  <span className="text-xs text-subtle">
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
