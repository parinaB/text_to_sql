import React, { useState } from 'react';
import {
  Code,
  Copy,
  Check,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Terminal,
} from 'lucide-react';

interface SqlPanelProps {
  sql?: string | null;
  parameters?: Record<string, any>;
  validationStatus: string;
}

export const SqlPanel: React.FC<SqlPanelProps> = ({
  sql,
  parameters = {},
  validationStatus,
}) => {
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  const handleCopy = () => {
    if (!sql) return;
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasParams = Object.keys(parameters).length > 0;

  if (!sql) {
    return (
      <div className="bg-slate-50 border border-dashed border-slate-200 rounded-2xl p-5 text-center text-sm text-slate-500">
        <Code className="w-5 h-5 mx-auto mb-1 text-slate-400" />
        No SQL query was executed for this inquiry.
      </div>
    );
  }

  return (
    <div className="bg-navy-950 border border-navy-800 rounded-2xl overflow-hidden shadow-md">
      {/* Top Header Bar */}
      <div className="px-5 py-3.5 bg-navy-900 border-b border-navy-800 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-indigo-400" />
          <span className="text-xs font-semibold text-slate-200 font-mono">
            Generated ANSI SQLite
          </span>
          {validationStatus === 'PASSED' && (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span>AST Verified</span>
            </span>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-navy-800 hover:bg-navy-700 text-slate-300 hover:text-white text-xs transition-colors border border-navy-700 active:scale-95"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400 font-medium">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy SQL</span>
              </>
            )}
          </button>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 rounded bg-navy-800 hover:bg-navy-700 text-slate-400 hover:text-slate-200 text-xs transition-colors border border-navy-700"
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Code Display Area */}
      {isExpanded && (
        <div className="p-5 font-mono text-sm leading-relaxed text-slate-200 overflow-x-auto">
          <pre className="text-indigo-200 font-mono whitespace-pre-wrap selection:bg-indigo-600 selection:text-white">
            {sql}
          </pre>

          {/* Bound Parameter Chips */}
          {hasParams && (
            <div className="mt-4 pt-3 border-t border-navy-800 flex items-center flex-wrap gap-2 text-xs">
              <span className="text-slate-400 text-[11px] font-sans font-semibold uppercase tracking-wider">
                Bound Parameters:
              </span>
              {Object.entries(parameters).map(([key, val]) => (
                <span
                  key={key}
                  className="bg-navy-900 px-2.5 py-1 rounded border border-navy-700 text-slate-300 font-mono text-[11px]"
                >
                  <span className="text-indigo-400 font-semibold">{key}: </span>
                  <span className="text-emerald-300">{JSON.stringify(val)}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
