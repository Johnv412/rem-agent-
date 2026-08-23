import React, { useState, useEffect } from "react";
import {
  Code2,
  Copy,
  Check,
  Download,
  FileText,
  Folder,
  FolderOpen,
  Terminal,
  ExternalLink,
  Layers,
  Sparkles,
} from "lucide-react";
import { SourceFile } from "../types";

export const CodebaseViewer: React.FC = () => {
  const [files, setFiles] = useState<SourceFile[]>([]);
  const [selectedFileId, setSelectedFileId] = useState<string>("schemas");
  const [copied, setCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch("/api/files/source")
      .then((res) => res.json())
      .then((data) => {
        setFiles(data.files || []);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load source files:", err);
        setIsLoading(false);
      });
  }, []);

  const selectedFile = files.find((f) => f.id === selectedFileId) || files[0];

  const handleCopy = () => {
    if (selectedFile) {
      navigator.clipboard.writeText(selectedFile.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!selectedFile) return;
    const blob = new Blob([selectedFile.content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = selectedFile.name.split("/").pop() || "file.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Quickstart */}
      <div className="bg-slate-900 text-white p-6 rounded-2xl border border-slate-800 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-mono font-semibold border border-indigo-500/30">
              pip install remagent
            </span>
            <span className="text-xs text-slate-400">Python 3.11+ • Pydantic v2 • Zero Fake Imports</span>
          </div>
          <h2 className="text-xl font-bold text-white mt-2">Modular Python Package Structure</h2>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
            Ready to push to GitHub or integrate directly into Google Antigravity / Hermes Agent frameworks.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-auto">
          <div className="bg-slate-800/80 px-3.5 py-2 rounded-xl border border-slate-700 font-mono text-xs text-slate-300 flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>pip install remagent</span>
          </div>
        </div>
      </div>

      {/* Main File Explorer & Code Display */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Left Sidebar: File Tree (4 cols) */}
        <div className="lg:col-span-4 border-r border-slate-200/80 bg-slate-50/50 p-4 space-y-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 px-2">
            Package Tree (`remagent/`)
          </div>

          <div className="space-y-1 text-xs">
            {isLoading ? (
              <div className="p-4 text-center text-slate-400">Loading package files...</div>
            ) : (
              files.map((file) => {
                const isSelected = file.id === selectedFileId;
                return (
                  <button
                    key={file.id}
                    id={`file-tree-${file.id}`}
                    onClick={() => setSelectedFileId(file.id)}
                    className={`w-full text-left px-3 py-2 rounded-xl flex items-center justify-between font-mono transition-all ${
                      isSelected
                        ? "bg-slate-900 text-white font-semibold shadow-xs"
                        : "text-slate-700 hover:bg-slate-200/60"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <FileText className={`w-4 h-4 ${isSelected ? "text-indigo-400" : "text-slate-400"}`} />
                      <span className="truncate">{file.name}</span>
                    </div>
                    <span className={`text-[10px] uppercase font-sans ${isSelected ? "text-slate-400" : "text-slate-400"}`}>
                      {file.lang}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Code Display (8 cols) */}
        <div className="lg:col-span-8 flex flex-col h-[650px] bg-slate-950 text-slate-100">
          {/* Code Viewer Header */}
          <div className="px-5 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-indigo-400" />
              <span className="font-mono text-xs text-slate-200 font-semibold">{selectedFile?.name}</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                id="btn-copy-code"
                onClick={handleCopy}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Code</span>
                  </>
                )}
              </button>

              <button
                id="btn-download-file"
                onClick={handleDownload}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download</span>
              </button>
            </div>
          </div>

          {/* Code Content */}
          <div className="flex-1 overflow-auto p-5 font-mono text-xs leading-relaxed text-slate-200 whitespace-pre">
            {selectedFile?.content || "# Loading file content..."}
          </div>
        </div>
      </div>
    </div>
  );
};
