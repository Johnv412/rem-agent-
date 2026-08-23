import React, { useState } from "react";
import {
  Database,
  Shield,
  CheckCircle,
  AlertCircle,
  FileCheck,
  History,
  TrendingDown,
  Sparkles,
  GitCommit,
  Tag,
  ArrowRight,
  Filter,
} from "lucide-react";
import { SystemState, Fact, OperationalRule } from "../types";

interface MemoryGraphViewProps {
  systemState: SystemState | null;
}

export const MemoryGraphView: React.FC<MemoryGraphViewProps> = ({ systemState }) => {
  const [selectedEntity, setSelectedEntity] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const facts = systemState?.facts || [];
  const rules = systemState?.rules || [];
  const audits = systemState?.audits || [];

  const entities: string[] = Array.from(new Set(facts.map((f) => String(f.entity))));
  const categories: string[] = Array.from(new Set(rules.map((r) => String(r.category))));

  const filteredFacts = facts.filter((f) => {
    if (selectedEntity === "all") return true;
    return f.entity.toLowerCase() === selectedEntity.toLowerCase();
  });

  const filteredRules = rules.filter((r) => {
    if (selectedCategory === "all") return true;
    return r.category.toLowerCase() === selectedCategory.toLowerCase();
  });

  const activeFacts = filteredFacts.filter((f) => f.is_active);
  const supersededFacts = filteredFacts.filter((f) => !f.is_active);

  return (
    <div className="space-y-6">
      {/* Top Banner Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Facts</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{facts.filter((f) => f.is_active).length}</div>
          <div className="text-[11px] text-emerald-600 font-medium mt-1">Zero-Vector Structured Store</div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Operational Rules</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{rules.filter((r) => r.is_active).length}</div>
          <div className="text-[11px] text-indigo-600 font-medium mt-1">Durable Heuristics & Directives</div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Superseded Facts</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{facts.filter((f) => !f.is_active).length}</div>
          <div className="text-[11px] text-amber-600 font-medium mt-1">Contradictions Resolved</div>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Dream Cycles Executed</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{audits.length}</div>
          <div className="text-[11px] text-purple-600 font-medium mt-1">Autonomous REM Passes</div>
        </div>
      </div>

      {/* Main 2-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Entity Knowledge Graph & Facts (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
              <div>
                <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                  <Database className="w-4 h-4 text-emerald-600" />
                  <span>Structured Entity Facts</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Discrete, attributed key-value ground truth extracted without vector embeddings
                </p>
              </div>

              {/* Entity Filter Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto text-xs">
                <button
                  id="filter-entity-all"
                  onClick={() => setSelectedEntity("all")}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                    selectedEntity === "all"
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  All ({facts.length})
                </button>
                {entities.map((ent) => (
                  <button
                    key={ent}
                    id={`filter-entity-${ent.toLowerCase()}`}
                    onClick={() => setSelectedEntity(ent)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                      selectedEntity.toLowerCase() === ent.toLowerCase()
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {ent}
                  </button>
                ))}
              </div>
            </div>

            {/* Active Facts List */}
            <div className="mt-4 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Active Ground-Truth Facts ({activeFacts.length})
              </h4>

              {activeFacts.length === 0 ? (
                <div className="p-6 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl">
                  No active facts matching filter.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {activeFacts.map((fact) => (
                    <div
                      key={fact.id}
                      className="p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/80 hover:border-indigo-200 hover:bg-indigo-50/20 transition-all flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                          <span className="font-mono font-bold px-1.5 py-0.5 rounded bg-white text-indigo-700 border border-slate-200">
                            {fact.entity}
                          </span>
                          <span className="font-mono text-emerald-600 font-semibold">
                            {(fact.confidence * 100).toFixed(0)}% conf
                          </span>
                        </div>
                        <div className="font-mono text-xs font-semibold text-slate-900 mt-1">
                          {fact.attribute}
                        </div>
                        <div className="text-xs text-slate-700 font-medium mt-1 bg-white p-2 rounded-lg border border-slate-200/60 break-words">
                          {typeof fact.value === "object" ? JSON.stringify(fact.value) : String(fact.value)}
                        </div>
                      </div>
                      <div className="mt-3 pt-2 border-t border-slate-200/50 flex items-center justify-between text-[10px] text-slate-400">
                        <span>ID: {fact.id.substring(0, 10)}</span>
                        <span>{new Date(fact.timestamp).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Superseded Facts / Contradiction History */}
              {supersededFacts.length > 0 && (
                <div className="mt-6 pt-4 border-t border-slate-200">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-700 flex items-center gap-1 mb-2">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Superseded Contradictions ({supersededFacts.length})</span>
                  </h4>
                  <div className="space-y-2">
                    {supersededFacts.map((sFact) => (
                      <div
                        key={sFact.id}
                        className="p-3 rounded-xl bg-amber-50/50 border border-amber-200/60 text-xs text-slate-600 flex items-center justify-between opacity-85"
                      >
                        <div>
                          <div className="flex items-center gap-1.5 text-[11px]">
                            <span className="font-mono font-semibold text-amber-900">{sFact.entity}.{sFact.attribute}</span>
                            <span className="line-through text-slate-400">{String(sFact.value)}</span>
                          </div>
                          <div className="text-[10px] text-amber-700 mt-0.5">
                            Status: Deprecated during REM sleep • Reason: User mandate updated
                          </div>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                          SUPERSEDED
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Operational Rules & Directives (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                  <Shield className="w-4 h-4 text-indigo-600" />
                  <span>Operational Directives</span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Consolidated task heuristics and unbreakable user preferences
                </p>
              </div>
            </div>

            {/* Rules List */}
            <div className="mt-4 space-y-3">
              {filteredRules.length === 0 ? (
                <div className="p-6 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl">
                  No operational rules synthesized yet.
                </div>
              ) : (
                filteredRules.map((rule) => {
                  const isP1 = rule.priority === 1;
                  const isP2 = rule.priority === 2;

                  return (
                    <div
                      key={rule.id}
                      className={`p-3.5 rounded-xl border transition-all ${
                        isP1
                          ? "bg-rose-50/50 border-rose-200/80"
                          : isP2
                          ? "bg-indigo-50/40 border-indigo-200/70"
                          : "bg-slate-50/70 border-slate-200/70"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span
                          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                            isP1
                              ? "bg-rose-100 text-rose-800"
                              : "bg-indigo-100 text-indigo-800"
                          }`}
                        >
                          {rule.category.replace("_", " ")}
                        </span>
                        <span
                          className={`text-[10px] font-bold font-mono px-1.5 py-0.2 rounded ${
                            isP1 ? "text-rose-700 bg-rose-100" : "text-slate-600 bg-slate-200"
                          }`}
                        >
                          Priority P{rule.priority}
                        </span>
                      </div>

                      <div className="text-xs font-bold text-slate-900 leading-snug">
                        {rule.rule}
                      </div>

                      <p className="text-[11px] text-slate-600 mt-1.5 leading-relaxed bg-white/70 p-2 rounded-lg border border-black/5">
                        <span className="font-semibold text-slate-700">Rationale:</span> {rule.rationale}
                      </p>

                      <div className="mt-2 text-[10px] text-slate-400 flex items-center justify-between">
                        <span>Updated: {new Date(rule.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                        <span className="text-emerald-600 font-semibold">Active in System Prompt</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Consolidation Audit Trail */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5">
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2 mb-3">
              <History className="w-4 h-4 text-purple-600" />
              <span>Consolidation Audit Trail</span>
            </h3>

            {audits.length === 0 ? (
              <p className="text-xs text-slate-400">No dream cycles run yet.</p>
            ) : (
              <div className="space-y-2.5 max-h-60 overflow-y-auto">
                {audits.map((audit) => (
                  <div
                    key={audit.run_id}
                    className="p-3 bg-slate-50 rounded-xl border border-slate-200/60 text-xs"
                  >
                    <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1 font-mono">
                      <span>{audit.run_id}</span>
                      <span>{new Date(audit.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-slate-700 text-[11px] leading-relaxed line-clamp-2">
                      {audit.reasoning_summary}
                    </p>
                    <div className="mt-2 pt-1.5 border-t border-slate-200/60 flex items-center justify-between text-[10px]">
                      <span className="text-slate-500">{audit.consolidated_turn_ids.length} turns processed</span>
                      <span className="text-emerald-600 font-bold">~{audit.estimated_token_savings} tokens saved</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
