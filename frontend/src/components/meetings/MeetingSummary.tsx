import { FileText, HelpCircle, Tag, Users } from "lucide-react";
import type { Meeting } from "@/lib/types";

const ENTITY_COLORS: Record<string, string> = {
  PERSON: "bg-sky-50 text-sky-700",
  ORG: "bg-green-50 text-green-700",
  PRODUCT: "bg-amber-50 text-amber-700",
  TECHNOLOGY: "bg-indigo-50 text-indigo-700",
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
      <div className="flex flex-col items-center justify-center py-16 text-gray-400">
        <FileText className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">No summary available yet.</p>
        <p className="text-xs mt-1">Processing may still be in progress.</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-5">
      {hasSummary && (
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-gray-800">Summary</h3>
          </div>
          <p className="text-sm text-gray-600 leading-relaxed">{meeting.summary}</p>
        </div>
      )}

      {hasParticipants && (
        <div className="card p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3">Participants</h3>
          <div className="flex flex-wrap gap-2">
            {meeting.participants.map((p) => (
              <span key={p} className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      {hasTopics && (
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Tag className="w-4 h-4 text-purple-600" />
            <h3 className="text-sm font-semibold text-gray-800">Topics Discussed</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {meeting.topics.map((topic) => (
              <span key={topic} className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-xs font-medium">
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {hasEntities && (
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-teal-600" />
            <h3 className="text-sm font-semibold text-gray-800">Key Entities</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {meeting.entities.map((ent, i) => (
              <span
                key={i}
                className={`px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 ${ENTITY_COLORS[ent.type] ?? "bg-gray-50 text-gray-700"}`}
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
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-3">
            <HelpCircle className="w-4 h-4 text-orange-500" />
            <h3 className="text-sm font-semibold text-gray-800">Unresolved Questions</h3>
          </div>
          <ul className="space-y-2">
            {meeting.unresolved.map((q, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
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
