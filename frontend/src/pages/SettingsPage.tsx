import React from 'react';
import type { SystemStatus } from '../types/api';
import {
  Settings as SettingsIcon,
  ShieldCheck,
  Cpu,
  Database,
  Lock,
  Layers,
} from 'lucide-react';

interface SettingsPageProps {
  status: SystemStatus | null;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ status }) => {
  return (
    <div className="w-full max-w-4xl mx-auto py-8 px-6 space-y-8">
      {/* Header */}
      <div className="border-b border-slate-200 pb-5">
        <div className="flex items-center space-x-2">
          <SettingsIcon className="w-5 h-5 text-indigo-600" />
          <h1 className="text-2xl font-bold text-slate-900">System & Agent Settings</h1>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Architectural boundaries, security enforcement rules, and model provider configuration.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Model Providers Card */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4 shadow-xs">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
            <Cpu className="w-4 h-4 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
              Inference & Embeddings
            </h2>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">LLM Provider</span>
              <span className="font-mono text-slate-800 uppercase font-semibold">
                {status?.llm_provider || 'ollama'}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Active LLM Model</span>
              <span className="font-mono text-indigo-600 font-semibold">
                {status?.llm_model || 'llama3:8b'}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Embedding Provider</span>
              <span className="font-mono text-slate-800 uppercase font-semibold">
                {status?.embedding_provider || 'ollama'}
              </span>
            </div>

            <div className="flex items-center justify-between py-2">
              <span className="text-slate-500 font-medium">Embedding Model</span>
              <span className="font-mono text-indigo-600 font-semibold">
                {status?.embedding_model || 'nomic-embed-text'}
              </span>
            </div>
          </div>
        </div>

        {/* Database & Runtime Limits */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4 shadow-xs">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
            <Database className="w-4 h-4 text-indigo-600" />
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
              Database & Execution Limits
            </h2>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Target Database</span>
              <span className="font-mono text-slate-800 font-semibold">
                {status?.database_path || 'business.db'}
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Query Timeout</span>
              <span className="font-mono text-slate-800 font-semibold">
                {status?.query_timeout_seconds ?? 5.0} seconds
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 font-medium">Max Result Rows</span>
              <span className="font-mono text-slate-800 font-semibold">
                {status?.max_result_rows ?? 100} rows
              </span>
            </div>

            <div className="flex items-center justify-between py-2">
              <span className="text-slate-500 font-medium">Self-Healing Retries</span>
              <span className="font-mono text-slate-800 font-semibold">3 attempts max</span>
            </div>
          </div>
        </div>
      </div>

      {/* Security Boundaries & Safe Isolation */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4 shadow-xs">
        <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
            Enterprise Security Architecture
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-1.5">
            <div className="flex items-center space-x-1.5 font-semibold text-slate-800">
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              <span>Table Allowlist</span>
            </div>
            <p className="text-slate-500 leading-relaxed text-[11px]">
              Only `customers`, `products`, `orders`, and `order_items` are accessible. All system tables (`sqlite_master`, credentials) are strictly rejected.
            </p>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-1.5">
            <div className="flex items-center space-x-1.5 font-semibold text-slate-800">
              <Lock className="w-3.5 h-3.5 text-rose-600" />
              <span>Read-Only SQLite URI</span>
            </div>
            <p className="text-slate-500 leading-relaxed text-[11px]">
              Connections are opened strictly via `file:business.db?mode=ro`. The SQLite filesystem driver physically prevents writes.
            </p>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-1.5">
            <div className="flex items-center space-x-1.5 font-semibold text-slate-800">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Deterministic AST Parsing</span>
            </div>
            <p className="text-slate-500 leading-relaxed text-[11px]">
              All queries are validated through sqlglot. Multi-statement queries, DDL, DML, and dangerous functions (`eval`, `load_extension`) are blocked.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
