import UploadZone from "@/components/upload/UploadZone";
import { Upload } from "lucide-react";

export default function UploadPage() {
  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
            <Upload className="w-4 h-4 text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Upload Meeting</h1>
        </div>
        <p className="text-gray-500 text-sm">
          Upload a meeting recording and MeetMind will automatically transcribe,
          extract decisions, action items, and make it searchable.
        </p>
      </div>

      <div className="card p-8">
        <UploadZone />
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4">
        {[
          { title: "Transcription", desc: "Speaker-attributed transcript with timestamps" },
          { title: "Knowledge Extraction", desc: "Decisions, action items, and topics" },
          { title: "Semantic Search", desc: "Ask questions across all your meetings" },
        ].map((f) => (
          <div key={f.title} className="card p-4">
            <p className="text-sm font-semibold text-gray-800 mb-1">{f.title}</p>
            <p className="text-xs text-gray-500">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
