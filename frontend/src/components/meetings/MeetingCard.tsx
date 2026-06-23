import Link from "next/link";
import { Video, Clock, Users, Calendar } from "lucide-react";
import type { Meeting } from "@/lib/types";
import { formatDate, formatDuration } from "@/lib/utils";
import StatusBadge from "./StatusBadge";

interface MeetingCardProps {
  meeting: Meeting;
}

export default function MeetingCard({ meeting }: MeetingCardProps) {
  return (
    <Link href={`/meetings/${meeting.id}`}>
      <div className="card p-5 hover:shadow-md hover:border-blue-200 transition-all duration-200 cursor-pointer group">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
              <Video className="w-4 h-4 text-blue-600" />
            </div>
            <h3 className="font-semibold text-gray-900 text-sm truncate group-hover:text-blue-600 transition-colors">
              {meeting.title}
            </h3>
          </div>
          <StatusBadge status={meeting.status} />
        </div>

        {/* Summary */}
        {meeting.summary && (
          <p className="text-xs text-gray-500 mb-3 line-clamp-2 leading-relaxed">
            {meeting.summary}
          </p>
        )}

        {/* Topics */}
        {meeting.topics && meeting.topics.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {meeting.topics.slice(0, 4).map((topic) => (
              <span
                key={topic}
                className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
              >
                {topic}
              </span>
            ))}
            {meeting.topics.length > 4 && (
              <span className="px-2 py-0.5 bg-gray-100 text-gray-400 rounded text-xs">
                +{meeting.topics.length - 4}
              </span>
            )}
          </div>
        )}

        {/* Meta */}
        <div className="flex items-center gap-4 text-xs text-gray-400">
          {meeting.date && (
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {formatDate(meeting.date)}
            </span>
          )}
          {meeting.duration_seconds && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDuration(meeting.duration_seconds)}
            </span>
          )}
          {meeting.participants && meeting.participants.length > 0 && (
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {meeting.participants.length} speaker
              {meeting.participants.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
