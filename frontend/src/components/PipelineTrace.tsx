import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  MinusCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Workflow,
  Clock,
} from 'lucide-react';
import type { PipelineStage } from '../types/api';

interface PipelineTraceProps {
  stages: PipelineStage[];
}

export const PipelineTrace: React.FC<PipelineTraceProps> = ({ stages }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!stages || stages.length === 0) return null;

  const getStatusIcon = (status: PipelineStage['status']) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />;
      case 'FAILED':
        return <XCircle className="w-4 h-4 text-rose-500 shrink-0" />;
      case 'SKIPPED':
        return <MinusCircle className="w-4 h-4 text-slate-400 shrink-0" />;
      case 'RUNNING':
        return <Loader2 className="w-4 h-4 text-indigo-500 animate-spin shrink-0" />;
      default:
        return <MinusCircle className="w-4 h-4 text-slate-400 shrink-0" />;
    }
  };

  const getStatusBadge = (status: PipelineStage['status']) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
            COMPLETED
          </span>
        );
      case 'FAILED':
        return (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
            FAILED
          </span>
        );
      case 'SKIPPED':
        return (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
            SKIPPED
          </span>
        );
      case 'RUNNING':
        return (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
            RUNNING
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
      {/* Accordion Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-3.5 bg-slate-50/70 hover:bg-slate-100/70 border-b border-slate-200/70 flex items-center justify-between text-left transition-colors"
      >
        <div className="flex items-center space-x-2.5">
          <Workflow className="w-4 h-4 text-indigo-600" />
          <span className="text-xs font-semibold text-slate-700">
            Explain the Process • Agent Pipeline Trace ({stages.length} Steps)
          </span>
        </div>

        <div className="flex items-center space-x-2 text-xs text-slate-500">
          <span className="text-[11px] text-slate-400">
            {isOpen ? 'Hide breakdown' : 'View execution breakdown'}
          </span>
          {isOpen ? (
            <ChevronUp className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          )}
        </div>
      </button>

      {/* Expanded Timeline Steps */}
      {isOpen && (
        <div className="p-5 bg-white space-y-4">
          <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {stages.map((stage, idx) => (
              <div key={idx} className="relative group">
                {/* Status Dot */}
                <div className="absolute -left-6 top-0.5 bg-white rounded-full ring-2 ring-white">
                  {getStatusIcon(stage.status)}
                </div>

                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-slate-800">{stage.label}</span>
                    {getStatusBadge(stage.status)}
                    {stage.duration_ms !== undefined && stage.duration_ms !== null && (
                      <span className="flex items-center space-x-1 text-[11px] text-slate-400">
                        <Clock className="w-3 h-3" />
                        <span>{stage.duration_ms.toFixed(1)} ms</span>
                      </span>
                    )}
                  </div>

                  {stage.details && (
                    <p className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100 leading-relaxed font-sans">
                      {stage.details}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
