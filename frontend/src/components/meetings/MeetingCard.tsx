import Link from "next/link";
import { Video, Clock, Users, Calendar, ArrowUpRight } from "lucide-react";
import type { Meeting } from "@/lib/types";
import { formatDate, formatDuration } from "@/lib/utils";
import StatusBadge from "./StatusBadge";

interface MeetingCardProps {
  meeting: Meeting;
}

export default function MeetingCard({ meeting }: MeetingCardProps) {
  return (
    <Link href={`/meetings/${meeting.id}`} className="block group">
      <div className="card p-5 h-full hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-glow transition-all duration-200">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-500/15 to-cyan-500/15 ring-1 ring-blue-500/20 flex items-center justify-center flex-shrink-0">
              <Video className="w-4 h-4 text-blue-400" />
            </div>
            <h3 className="font-semibold text-fg text-sm truncate group-hover:text-accent transition-colors">
              {meeting.title}
            </h3>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <StatusBadge status={meeting.status} />
            <ArrowUpRight className="w-4 h-4 text-subtle opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>

        {meeting.summary && (
          <p className="text-sm text-muted mb-4 line-clamp-2 leading-relaxed">
            {meeting.summary}
          </p>
        )}

        {meeting.topics && meeting.topics.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {meeting.topics.slice(0, 4).map((topic) => (
              <span key={topic} className="chip">
                {topic}
              </span>
            ))}
            {meeting.topics.length > 4 && (
              <span className="chip text-subtle">+{meeting.topics.length - 4}</span>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-4 border-t border-line pt-3 text-xs text-subtle">
          {meeting.date && (
            <span className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              {formatDate(meeting.date)}
            </span>
          )}
          {meeting.duration_seconds != null && (
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              {formatDuration(meeting.duration_seconds)}
            </span>
          )}
          {meeting.participants && meeting.participants.length > 0 && (
            <span className="flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5" />
              {meeting.participants.length} speaker
              {meeting.participants.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
