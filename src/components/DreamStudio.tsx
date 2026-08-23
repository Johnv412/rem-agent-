import React, { useState, useEffect } from "react";
import {
  Send,
  Sparkles,
  RotateCcw,
  Moon,
  Zap,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Layers,
  ArrowRight,
  TrendingDown,
  Clock,
  Terminal,
  Activity,
} from "lucide-react";
import { SystemState, RawTurn } from "../types";

interface DreamStudioProps {
  systemState: SystemState | null;
  onSendMessage: (msg: string) => Promise<void>;
  onTriggerDream: () => Promise<void>;
  onSeedScenario: (scenario: string) => Promise<void>;
  onReset: () => Promise<void>;
  isDreaming: boolean;
}

export const DreamStudio: React.FC<DreamStudioProps> = ({
  systemState,
  onSendMessage,
  onTriggerDream,
  onSeedScenario,
  onReset,
  isDreaming,
}) => {
  const [inputMessage, setInputMessage] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [daemonThreshold] = useState(30); // 30s idle threshold
  const [idleCounter, setIdleCounter] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      if (systemState) {
        setIdleCounter((prev) => prev + 1);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [systemState]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isSending) return;
    const msg = inputMessage;
    setInputMessage("");
    setIsSending(true);
    try {
      await onSendMessage(msg);
      setIdleCounter(0);
    } finally {
      setIsSending(false);
    }
  };

  const unconsolidatedTurns = systemState?.turns.filter((t) => !t.is_consolidated) || [];
  const activeFacts = systemState?.facts.filter((f) => f.is_active) || [];
  const activeRules = systemState?.rules.filter((r) => r.is_active) || [];
  const latestAudit = systemState?.audits?.[0];

  return (
    <div className="space-y-6">
      {/* Top Banner: Biological Sleep Concept & Daemon Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Zero-Vector Paradigm */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-md">
                Zero-Vector Memory
              </span>
              <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> No Drift
              </span>
            </div>
            <h3 className="font-semibold text-slate-900 text-base">Biological REM Sleep Model</h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Instead of saving noisy embeddings into a vector database, RemAgent logs raw episodic turns into an episodic buffer. When the agent is idle, the background Dream Daemon runs a 3-stage consolidation pass.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Deterministic Schema</span>
            <span className="font-mono font-medium text-slate-800">SQLite / Firestore</span>
          </div>
        </div>

        {/* Card 2: Daemon Idle & Sleep Tracker */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-700 bg-amber-50 px-2.5 py-1 rounded-md flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" /> Dream Daemon
              </span>
              <span className="text-xs font-mono text-slate-500">
                {isDreaming ? (
                  <span className="text-indigo-600 font-semibold animate-pulse">● Dreaming (REM)</span>
                ) : (
                  <span>Idle Timer: {idleCounter}s / {daemonThreshold}s</span>
                )}
              </span>
            </div>
            <h3 className="font-semibold text-slate-900 text-base">Autonomous Sleep Trigger</h3>
            <div className="mt-3">
              <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-1000 ${
                    isDreaming
                      ? "bg-indigo-600 w-full animate-pulse"
                      : "bg-amber-500"
                  }`}
                  style={{
                    width: isDreaming
                      ? "100%"
                      : `${Math.min(100, (idleCounter / daemonThreshold) * 100)}%`,
                  }}
                />
              </div>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              {isDreaming
                ? "Dream Synthesizer is consolidating facts and resolving contradictions..."
                : unconsolidatedTurns.length > 0
                ? `${unconsolidatedTurns.length} turns waiting in buffer. Triggers automatically on idle.`
                : "Queue is empty. Agent memory is completely consolidated."}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
            <button
              id="btn-force-dream-card"
              onClick={onTriggerDream}
              disabled={isDreaming || unconsolidatedTurns.length === 0}
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 disabled:text-slate-300 transition-colors flex items-center gap-1"
            >
              <Moon className="w-3.5 h-3.5" /> Force Immediate REM Pass
            </button>
          </div>
        </div>

        {/* Card 3: Memory Efficiency Metrics */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md flex items-center gap-1">
                <TrendingDown className="w-3.5 h-3.5" /> Token Efficiency
              </span>
              <span className="text-xs font-mono font-medium text-emerald-700">~82% Noise Pruned</span>
            </div>
            <h3 className="font-semibold text-slate-900 text-base">Zero Bloat Knowledge State</h3>
            <div className="grid grid-cols-2 gap-2 mt-3 text-center">
              <div className="bg-slate-50 p-2 rounded-xl border border-slate-100">
                <div className="text-lg font-bold text-slate-900">{activeFacts.length}</div>
                <div className="text-[11px] text-slate-500">Active Facts</div>
              </div>
              <div className="bg-slate-50 p-2 rounded-xl border border-slate-100">
                <div className="text-lg font-bold text-slate-900">{activeRules.length}</div>
                <div className="text-[11px] text-slate-500">Active Rules</div>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Lifetime Pruned Noise</span>
            <span className="font-mono font-bold text-slate-800">{systemState?.totalPrunedTurns || 0} turns</span>
          </div>
        </div>
      </div>

      {/* Main Interactive Grid: Left = Chat / Test Console, Right = Raw Turn Episodic Buffer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Interactive Agent Chat & Context Injection (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden flex flex-col h-[580px]">
            {/* Header */}
            <div className="px-5 py-3.5 bg-slate-50/80 border-b border-slate-200/80 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-semibold text-slate-900 text-sm">Interactive AI Agent</span>
                <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-200/70 text-slate-700 font-mono">
                  Zero-Vector Recall Enabled
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  id="btn-reset-demo"
                  onClick={onReset}
                  title="Reset Simulation to Initial Seed"
                  className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 rounded-lg transition-colors"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Recalled Memory Bar (Shows what the Agent recalled before answering) */}
            <div className="bg-indigo-50/70 px-4 py-2 border-b border-indigo-100 flex items-center justify-between text-xs text-indigo-900">
              <div className="flex items-center gap-2 truncate">
                <Zap className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                <span className="font-medium">Recalled Context:</span>
                <span className="truncate text-indigo-700">
                  {activeRules.length > 0
                    ? `[Rules: ${activeRules.slice(0, 2).map((r) => r.rule).join("; ")}]`
                    : "No active rules"}
                  {" • "}
                  {activeFacts.length > 0
                    ? `[Facts: ${activeFacts.slice(0, 2).map((f) => `${f.entity}.${f.attribute}=${f.value}`).join(", ")}]`
                    : "No active facts"}
                </span>
              </div>
            </div>

            {/* Chat History View */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {systemState?.turns.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
                  <Terminal className="w-10 h-10 mb-2 opacity-40 text-indigo-500" />
                  <p className="text-sm font-medium text-slate-600">No interaction history yet.</p>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm">
                    Type a message below or load a scenario to see how raw turns enter the episodic buffer and get consolidated during REM sleep.
                  </p>
                </div>
              ) : (
                systemState?.turns.map((turn) => {
                  const isUser = turn.role === "user";
                  const isTool = turn.role === "tool";
                  const isAssistant = turn.role === "assistant";

                  return (
                    <div
                      key={turn.turn_id}
                      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                    >
                      {!isUser && (
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 ${
                            isTool
                              ? "bg-amber-100 text-amber-800"
                              : "bg-indigo-600 text-white"
                          }`}
                        >
                          {isTool ? "TOOL" : "AI"}
                        </div>
                      )}

                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                          isUser
                            ? "bg-slate-900 text-white rounded-br-xs"
                            : isTool
                            ? "bg-amber-50 text-amber-900 border border-amber-200/70 font-mono text-[11px]"
                            : "bg-slate-100 text-slate-800 rounded-bl-xs border border-slate-200/60"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 mb-1 opacity-70 text-[10px]">
                          <span className="font-semibold uppercase tracking-wider">
                            {turn.role}
                          </span>
                          <span>
                            {new Date(turn.timestamp).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit",
                            })}
                          </span>
                        </div>
                        <div className="whitespace-pre-wrap">{turn.content}</div>

                        {/* Consolidation status pill */}
                        <div className="mt-2 pt-1 border-t border-black/5 flex items-center justify-between text-[10px]">
                          <span
                            className={`font-semibold flex items-center gap-1 ${
                              turn.is_consolidated ? "text-emerald-500" : "text-amber-500"
                            }`}
                          >
                            {turn.is_consolidated ? (
                              <>
                                <CheckCircle2 className="w-3 h-3" /> Consolidated (REM)
                              </>
                            ) : (
                              <>
                                <Moon className="w-3 h-3" /> In Raw Buffer
                              </>
                            )}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Quick Scenario Injectors */}
            <div className="px-4 py-2 bg-slate-50 border-t border-slate-200/80 flex items-center gap-2 overflow-x-auto text-xs">
              <span className="text-[11px] font-semibold text-slate-500 shrink-0">Scenarios:</span>
              <button
                id="btn-seed-contradiction"
                onClick={() => onSeedScenario("contradiction_override")}
                className="px-2.5 py-1 rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors shrink-0 flex items-center gap-1"
              >
                <AlertTriangle className="w-3 h-3 text-amber-500" />
                <span>DB Migration Contradiction</span>
              </button>
              <button
                id="btn-seed-noise"
                onClick={() => onSeedScenario("noisy_chaff")}
                className="px-2.5 py-1 rounded-md bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors shrink-0 flex items-center gap-1"
              >
                <TrendingDown className="w-3 h-3 text-emerald-500" />
                <span>Noisy Chit-Chat & Chaff</span>
              </button>
            </div>

            {/* Input Box */}
            <form onSubmit={handleSend} className="p-3 bg-white border-t border-slate-200">
              <div className="flex gap-2">
                <input
                  id="chat-input-field"
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Speak to agent or dictate an architectural directive..."
                  className="flex-1 px-4 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                />
                <button
                  id="btn-send-chat"
                  type="submit"
                  disabled={!inputMessage.trim() || isSending}
                  className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors"
                >
                  {isSending ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <span>Send</span>
                      <Send className="w-3.5 h-3.5" />
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Raw Episodic Queue & 3-Stage Consolidation Pipeline (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Episodic Turn Buffer Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden flex flex-col h-[580px]">
            <div className="px-5 py-3.5 bg-slate-50/80 border-b border-slate-200/80 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-600" />
                <span className="font-semibold text-slate-900 text-sm">
                  Unconsolidated Buffer ({unconsolidatedTurns.length})
                </span>
              </div>
              <button
                id="btn-trigger-dream-sidebar"
                onClick={onTriggerDream}
                disabled={isDreaming || unconsolidatedTurns.length === 0}
                className="text-xs px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-100 disabled:text-slate-400 text-white font-medium transition-all flex items-center gap-1"
              >
                <Sparkles className="w-3 h-3 text-amber-300" />
                <span>Sleep & Consolidate</span>
              </button>
            </div>

            {/* List of Pending Turns */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2.5 divide-y divide-slate-100">
              {unconsolidatedTurns.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2 opacity-80" />
                  <p className="text-sm font-semibold text-slate-700">Episodic Buffer Clean</p>
                  <p className="text-xs text-slate-400 mt-1">
                    All previous turns have been consolidated into high-signal entity facts and operational rules.
                  </p>
                </div>
              ) : (
                unconsolidatedTurns.map((turn, idx) => (
                  <div key={turn.turn_id} className="pt-2.5 first:pt-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                        Turn #{idx + 1} • {turn.role.toUpperCase()}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(turn.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 line-clamp-3 leading-relaxed">
                      {turn.content}
                    </p>
                    {turn.tool_calls && (
                      <div className="mt-1 text-[10px] font-mono text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200/50">
                        Tool Executed: {JSON.stringify(turn.tool_calls)}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Latest Consolidation Summary Footer */}
            {latestAudit && (
              <div className="p-4 bg-slate-900 text-white border-t border-slate-800 text-xs">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1 text-indigo-400 font-semibold text-[11px]">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Last REM Consolidation Pass</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">
                    {new Date(latestAudit.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed line-clamp-2">
                  {latestAudit.reasoning_summary}
                </p>
                <div className="mt-2 pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-400">
                  <span>+{latestAudit.added_facts.length} Facts Added</span>
                  <span>+{latestAudit.updated_rules.length} Rules Updated</span>
                  <span className="text-emerald-400 font-bold">
                    ~{latestAudit.estimated_token_savings} Tokens Saved
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
