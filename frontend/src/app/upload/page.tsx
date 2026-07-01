import UploadZone from "@/components/upload/UploadZone";
import { Upload, FileText, Sparkles, Search } from "lucide-react";

const FEATURES = [
  { title: "Transcription", desc: "Speaker-attributed transcript with timestamps", icon: FileText, tint: "text-blue-400 bg-blue-500/10 ring-blue-500/20" },
  { title: "Knowledge Extraction", desc: "Decisions, action items, and topics", icon: Sparkles, tint: "text-purple-400 bg-purple-500/10 ring-purple-500/20" },
  { title: "Semantic Search", desc: "Ask questions across all your meetings", icon: Search, tint: "text-cyan-400 bg-cyan-500/10 ring-cyan-500/20" },
];

export default function UploadPage() {
  return (
    <div className="p-6 md:p-8 max-w-4xl mx-auto animate-fade-in">
      <div className="mb-8 flex items-center gap-4">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center shadow-glow">
          <Upload className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="section-title mb-1">Ingest</p>
          <h1 className="text-2xl font-bold text-fg tracking-tight">Upload meeting</h1>
        </div>
      </div>

      <p className="text-muted text-sm max-w-2xl mb-6">
        Upload a meeting recording and MeetIQ will automatically transcribe, extract
        decisions, action items, and make it fully searchable.
      </p>

      <div className="card p-6 md:p-8">
        <UploadZone />
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        {FEATURES.map((f) => (
          <div key={f.title} className="card p-5">
            <div className={`w-10 h-10 rounded-xl ring-1 flex items-center justify-center mb-3 ${f.tint}`}>
              <f.icon className="w-5 h-5" />
            </div>
            <p className="text-sm font-semibold text-fg mb-1">{f.title}</p>
            <p className="text-xs text-muted leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
