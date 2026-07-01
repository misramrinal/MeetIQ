"use client";

import { useQuery } from "@tanstack/react-query";
import { Lightbulb, Loader2 } from "lucide-react";
import { decisionsApi } from "@/lib/api";
import { formatTime } from "@/lib/utils";
import Link from "next/link";
import PageHeader from "@/components/layout/PageHeader";

export default function DecisionsPage() {
  const { data: decisions = [], isLoading } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => decisionsApi.list(),
  });

  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto animate-fade-in">
      <PageHeader
        eyebrow="Outcomes"
        title="Decisions"
        subtitle={`${decisions.length} decision${decisions.length !== 1 ? "s" : ""} across all meetings`}
      />

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
        </div>
      ) : decisions.length === 0 ? (
        <div className="card p-12 text-center border-dashed">
          <div className="w-14 h-14 rounded-2xl bg-purple-500/10 ring-1 ring-purple-500/20 flex items-center justify-center mx-auto mb-4">
            <Lightbulb className="w-7 h-7 text-purple-400" />
          </div>
          <p className="text-fg font-semibold">No decisions extracted yet</p>
          <p className="text-muted text-sm mt-1">
            Upload and process a meeting to see decisions here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
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
                    {d.made_by && <span className="text-xs text-muted">{d.made_by}</span>}
                    {d.timestamp != null && (
                      <span className="text-xs text-subtle font-mono">at {formatTime(d.timestamp)}</span>
                    )}
                    {d.confidence > 0 && (
                      <span className="text-xs text-subtle">
                        {Math.round(d.confidence * 100)}% confidence
                      </span>
                    )}
                    <Link
                      href={`/meetings/${d.meeting_id}`}
                      className="text-xs text-accent hover:opacity-80 ml-auto"
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
