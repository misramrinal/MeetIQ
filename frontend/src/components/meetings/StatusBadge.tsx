import { cn } from "@/lib/utils";
import type { MeetingStatus } from "@/lib/types";
import { Clock, Loader2, CheckCircle2, XCircle } from "lucide-react";

const STATUS_CONFIG: Record<
  MeetingStatus,
  { label: string; className: string; icon: React.ElementType }
> = {
  pending: {
    label: "Pending",
    className: "bg-amber-500/10 text-amber-500 ring-1 ring-amber-500/20",
    icon: Clock,
  },
  processing: {
    label: "Processing",
    className: "bg-blue-500/10 text-blue-400 ring-1 ring-blue-500/20",
    icon: Loader2,
  },
  done: {
    label: "Done",
    className: "bg-emerald-500/10 text-emerald-500 ring-1 ring-emerald-500/20",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "bg-red-500/10 text-red-500 ring-1 ring-red-500/20",
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
    <span className={cn("badge", config.className, className)}>
      <Icon className={cn("w-3 h-3", status === "processing" && "animate-spin")} />
      {config.label}
    </span>
  );
}
