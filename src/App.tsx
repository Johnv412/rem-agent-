/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { DreamStudio } from "./components/DreamStudio";
import { MemoryGraphView } from "./components/MemoryGraphView";
import { BenchmarkLab } from "./components/BenchmarkLab";
import { CodebaseViewer } from "./components/CodebaseViewer";
import { SystemState } from "./types";
import { Moon, Sparkles, AlertCircle, CheckCircle, Database } from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState<"studio" | "memory" | "benchmark" | "code">("studio");
  const [systemState, setSystemState] = useState<SystemState | null>(null);
  const [isDreaming, setIsDreaming] = useState(false);
  const [notification, setNotification] = useState<{ message: string; type: "success" | "info" | "warning" } | null>(null);

  const fetchState = async () => {
    try {
      const res = await fetch("/api/state");
      if (res.ok) {
        const data = await res.json();
        setSystemState(data);
        setIsDreaming(data.isDreaming);
      }
    } catch (e) {
      console.error("Error fetching state:", e);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 3000);
    return () => clearInterval(interval);
  }, []);

  const showNotification = (message: string, type: "success" | "info" | "warning" = "success") => {
    setNotification({ message, type });
    setTimeout(() => {
      setNotification(null);
    }, 4000);
  };

  const handleSendMessage = async (msg: string) => {
    try {
      const res = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      if (res.ok) {
        await fetchState();
      }
    } catch (e: any) {
      console.error("Failed to send message:", e);
    }
  };

  const handleTriggerDream = async () => {
    setIsDreaming(true);
    try {
      const res = await fetch("/api/dream/consolidate", {
        method: "POST",
      });
      const data = await res.json();
      if (res.ok) {
        if (data.status === "skipped") {
          showNotification(data.message || "Queue is already consolidated.", "info");
        } else {
          showNotification(
            `✨ REM Consolidation Complete! Added ${data.activeFactsCount} facts, pruned ${data.result?.pruned_noise_count || 0} noise items.`,
            "success"
          );
        }
        await fetchState();
      } else {
        showNotification(data.error || "Dream consolidation failed.", "warning");
      }
    } catch (e: any) {
      console.error("Consolidation error:", e);
      showNotification("Failed to execute consolidation cycle.", "warning");
    } finally {
      setIsDreaming(false);
    }
  };

  const handleSeedScenario = async (scenario: string) => {
    try {
      const res = await fetch("/api/turns/seed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario }),
      });
      if (res.ok) {
        showNotification(`Loaded '${scenario.replace("_", " ")}' scenario into buffer.`, "info");
        await fetchState();
      }
    } catch (e: any) {
      console.error("Seed error:", e);
    }
  };

  const handleReset = async () => {
    try {
      const res = await fetch("/api/memory/reset", {
        method: "POST",
      });
      if (res.ok) {
        showNotification("Simulation state reset to default.", "info");
        await fetchState();
      }
    } catch (e: any) {
      console.error("Reset error:", e);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-indigo-100 selection:text-indigo-900">
      {/* Toast Notification Banner */}
      {notification && (
        <div className="fixed bottom-5 right-5 z-50 animate-in fade-in slide-in-from-bottom-5 duration-300">
          <div
            className={`px-4 py-3 rounded-xl shadow-lg border text-xs font-semibold flex items-center gap-2 ${
              notification.type === "success"
                ? "bg-slate-900 text-white border-slate-800"
                : notification.type === "warning"
                ? "bg-amber-50 text-amber-900 border-amber-200"
                : "bg-indigo-50 text-indigo-900 border-indigo-200"
            }`}
          >
            {notification.type === "success" && <CheckCircle className="w-4 h-4 text-emerald-400" />}
            {notification.type === "warning" && <AlertCircle className="w-4 h-4 text-amber-500" />}
            {notification.type === "info" && <Sparkles className="w-4 h-4 text-indigo-500" />}
            <span>{notification.message}</span>
          </div>
        </div>
      )}

      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemState={systemState}
        onTriggerDream={handleTriggerDream}
        isDreaming={isDreaming}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "studio" && (
          <DreamStudio
            systemState={systemState}
            onSendMessage={handleSendMessage}
            onTriggerDream={handleTriggerDream}
            onSeedScenario={handleSeedScenario}
            onReset={handleReset}
            isDreaming={isDreaming}
          />
        )}

        {activeTab === "memory" && (
          <MemoryGraphView systemState={systemState} />
        )}

        {activeTab === "benchmark" && (
          <BenchmarkLab />
        )}

        {activeTab === "code" && (
          <CodebaseViewer />
        )}
      </main>

      {/* Minimal Footer */}
      <footer className="border-t border-slate-200/80 bg-white/70 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2 font-medium text-slate-700">
            <Moon className="w-3.5 h-3.5 text-indigo-600" />
            <span>RemAgent • Zero-Vector Biological Sleep Memory</span>
          </div>
          <div className="flex items-center gap-4 text-slate-500 text-[11px]">
            <span>dreamengine.dev</span>
            <span>remagent.dev</span>
            <span className="font-mono text-slate-400">v1.0.0 (Apache-2.0)</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
