import { cn } from "@/lib/utils";
import type { MeetingStatus } from "@/lib/types";
import { Clock, Loader2, CheckCircle2, XCircle } from "lucide-react";

const STATUS_CONFIG: Record<
  MeetingStatus,
  { label: string; className: string; icon: React.ElementType }
> = {
  pending: {
    label: "Pending",
    className: "bg-yellow-50 text-yellow-700 border border-yellow-200",
    icon: Clock,
  },
  processing: {
    label: "Processing",
    className: "bg-blue-50 text-blue-700 border border-blue-200",
    icon: Loader2,
  },
  done: {
    label: "Done",
    className: "bg-green-50 text-green-700 border border-green-200",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "bg-red-50 text-red-700 border border-red-200",
    icon: XCircle,
  },
};

interface StatusBadgeProps {
  status: MeetingStatus;
  className?: string;
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  const Icon = config.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
        config.className,
        className
      )}
    >
      <Icon
        className={cn("w-3 h-3", status === "processing" && "animate-spin")}
      />
      {config.label}
    </span>
  );
}
