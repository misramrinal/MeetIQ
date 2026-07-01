import { FileText, HelpCircle, Tag, Users } from "lucide-react";
import type { Meeting } from "@/lib/types";

const ENTITY_COLORS: Record<string, string> = {
  PERSON: "bg-sky-500/10 text-sky-400 ring-1 ring-sky-500/20",
  ORG: "bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20",
  PRODUCT: "bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20",
  TECHNOLOGY: "bg-indigo-500/10 text-indigo-400 ring-1 ring-indigo-500/20",
};

interface MeetingSummaryProps {
  meeting: Meeting;
}

export default function MeetingSummary({ meeting }: MeetingSummaryProps) {
  const hasSummary = !!meeting.summary?.trim();
  const hasTopics = meeting.topics?.length > 0;
  const hasUnresolved = meeting.unresolved?.length > 0;
  const hasParticipants = meeting.participants?.length > 0;
  const hasEntities = meeting.entities?.length > 0;

  if (!hasSummary && !hasTopics && !hasUnresolved) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-subtle">
        <FileText className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No summary available yet.</p>
        <p className="text-xs mt-1">Processing may still be in progress.</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4 max-w-3xl mx-auto">
      {hasSummary && (
        <div className="card p-5 border-l-4 border-l-accent">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-accent" />
            <h3 className="text-sm font-semibold text-fg">Summary</h3>
          </div>
          <p className="text-sm text-muted leading-relaxed">{meeting.summary}</p>
        </div>
      )}

      {hasParticipants && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-fg mb-3">Participants</h3>
          <div className="flex flex-wrap gap-2">
            {meeting.participants.map((p) => (
              <span
                key={p}
                className="px-3 py-1 bg-blue-500/10 text-blue-400 ring-1 ring-blue-500/20 rounded-full text-xs font-medium"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {hasTopics && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Tag className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-fg">Topics Discussed</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {meeting.topics.map((topic) => (
              <span
                key={topic}
                className="px-3 py-1 bg-purple-500/10 text-purple-400 ring-1 ring-purple-500/20 rounded-full text-xs font-medium"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {hasEntities && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-teal-400" />
            <h3 className="text-sm font-semibold text-fg">Key Entities</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {meeting.entities.map((ent, i) => (
              <span
                key={i}
                className={`px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 ${
                  ENTITY_COLORS[ent.type] ?? "bg-panel-2 text-muted ring-1 ring-line"
                }`}
              >
                <span className="opacity-60 text-[10px] uppercase tracking-wide">{ent.type}</span>
                {ent.name}
                {ent.mentions > 1 && <span className="opacity-50 text-[10px]">×{ent.mentions}</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {hasUnresolved && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <HelpCircle className="w-4 h-4 text-orange-400" />
            <h3 className="text-sm font-semibold text-fg">Unresolved Questions</h3>
          </div>
          <ul className="space-y-2">
            {meeting.unresolved.map((q, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-muted">
                <span className="text-orange-400 mt-0.5">?</span>
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
