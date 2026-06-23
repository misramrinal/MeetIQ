"use client";

import { useQuery } from "@tanstack/react-query";
import { Lightbulb, Loader2 } from "lucide-react";
import { decisionsApi } from "@/lib/api";
import { formatTime, formatDate } from "@/lib/utils";
import Link from "next/link";

export default function DecisionsPage() {
  const { data: decisions = [], isLoading } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => decisionsApi.list(),
  });

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Decisions</h1>
        <p className="text-gray-500 text-sm">
          {decisions.length} decision{decisions.length !== 1 ? "s" : ""} across all meetings
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
        </div>
      ) : decisions.length === 0 ? (
        <div className="card p-12 text-center">
          <Lightbulb className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No decisions extracted yet</p>
          <p className="text-gray-400 text-sm mt-1">
            Upload and process a meeting to see decisions here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {decisions.map((d) => (
            <div key={d.id} className="card p-4 hover:border-blue-200 transition-colors">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Lightbulb className="w-3.5 h-3.5 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-800 font-medium leading-relaxed">{d.text}</p>
                  {d.context && (
                    <p className="text-xs text-gray-500 mt-1 italic">{d.context}</p>
                  )}
                  <div className="flex items-center gap-3 mt-2">
                    {d.made_by && (
                      <span className="text-xs text-gray-500">{d.made_by}</span>
                    )}
                    {d.timestamp != null && (
                      <span className="text-xs text-gray-400 font-mono">
                        at {formatTime(d.timestamp)}
                      </span>
                    )}
                    {d.confidence > 0 && (
                      <span className="text-xs text-gray-400">
                        {Math.round(d.confidence * 100)}% confidence
                      </span>
                    )}
                    <Link
                      href={`/meetings/${d.meeting_id}`}
                      className="text-xs text-blue-500 hover:text-blue-700 ml-auto"
                    >
                      View meeting →
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
