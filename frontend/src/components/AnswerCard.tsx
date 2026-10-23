import React from 'react';
import {
  Sparkles,
  Clock,
  RotateCw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  Star,
  Hash,
} from 'lucide-react';
import type { QueryAPIResponse } from '../types/api';

interface AnswerCardProps {
  response: QueryAPIResponse;
  isSaved?: boolean;
  onToggleSave?: () => void;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({
  response,
  isSaved = false,
  onToggleSave,
}) => {
  const getBadge = () => {
    switch (response.validation_status) {
      case 'PASSED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
            <span>PASSED AST VALIDATION</span>
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3.5 h-3.5 text-rose-600" />
            <span>BLOCKED BY SECURITY POLICY</span>
          </span>
        );
      case 'UNSUPPORTED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            <span>OUT OF DOMAIN / UNSUPPORTED</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">
            <span>{response.validation_status}</span>
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm p-6 space-y-4">
      {/* Header bar: Badge, Request ID, Latency, Attempts, Star button */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-3">
          {getBadge()}
          <span className="text-xs font-mono text-slate-400 flex items-center space-x-1">
            <Hash className="w-3 h-3" />
            <span>{response.request_id}</span>
          </span>
        </div>

        <div className="flex items-center space-x-4 text-xs text-slate-500">
          <div className="flex items-center space-x-1">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>{response.total_time_ms.toFixed(1)} ms</span>
          </div>

          <div className="flex items-center space-x-1">
            <RotateCw className="w-3.5 h-3.5 text-slate-400" />
            <span>
              {response.attempts} {response.attempts === 1 ? 'attempt' : 'attempts'}
            </span>
          </div>

          {onToggleSave && (
            <button
              onClick={onToggleSave}
              className={`p-1.5 rounded-lg border transition-all ${
                isSaved
                  ? 'bg-amber-50 border-amber-300 text-amber-600'
                  : 'bg-white border-slate-200 text-slate-400 hover:text-slate-600 hover:border-slate-300'
              }`}
              title={isSaved ? 'Remove from Saved Queries' : 'Save Query'}
            >
              <Star className={`w-4 h-4 ${isSaved ? 'fill-amber-400' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Main Grounded Answer */}
      <div className="space-y-2">
        <div className="flex items-center space-x-2 text-xs font-semibold uppercase tracking-wider text-indigo-600">
          <Sparkles className="w-4 h-4 text-indigo-500" />
          <span>Grounded Business Answer</span>
        </div>
        <div className="text-base text-slate-800 leading-relaxed font-normal bg-slate-50/70 p-4 rounded-xl border border-slate-100">
          {response.answer}
        </div>
      </div>

      {/* Assumptions Applied (if any) */}
      {response.assumptions && response.assumptions.length > 0 && (
        <div className="pt-2">
          <div className="flex items-start space-x-2 text-xs text-slate-600 bg-slate-100/60 p-3 rounded-lg border border-slate-200/60">
            <Info className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-700">Assumptions applied: </span>
              <ul className="list-disc list-inside mt-1 space-y-0.5 text-slate-600">
                {response.assumptions.map((assump, idx) => (
                  <li key={idx}>{assump}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
