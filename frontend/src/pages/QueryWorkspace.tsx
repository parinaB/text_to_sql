import React from 'react';
import { QueryInput } from '../components/QueryInput';
import { AnswerCard } from '../components/AnswerCard';
import { SqlPanel } from '../components/SqlPanel';
import { ResultTable } from '../components/ResultTable';
import { PipelineTrace } from '../components/PipelineTrace';
import type { QueryAPIResponse } from '../types/api';
import { Database, ShieldCheck, Zap, Bot } from 'lucide-react';

interface QueryWorkspaceProps {
  currentResponse: QueryAPIResponse | null;
  isLoading: boolean;
  onSubmitQuestion: (question: string) => void;
  savedQueryIds: Set<string>;
  onToggleSave: (resp: QueryAPIResponse) => void;
  error: string | null;
}

export const QueryWorkspace: React.FC<QueryWorkspaceProps> = ({
  currentResponse,
  isLoading,
  onSubmitQuestion,
  savedQueryIds,
  onToggleSave,
  error,
}) => {
  return (
    <div className="w-full max-w-5xl mx-auto py-8 px-6 space-y-8">
      {/* Header Banner */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-semibold mb-1">
          <Bot className="w-3.5 h-3.5" />
          <span>Autonomous Self-Verifying Agent</span>
        </div>
        <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight sm:text-4xl">
          Ask your data anything.
        </h1>
        <p className="text-base text-slate-500 max-w-2xl mx-auto">
          Turn natural-language business questions into safe, executable SQL with zero hallucinations and continuous AST verification.
        </p>
      </div>

      {/* Query Input Box */}
      <QueryInput
        onSubmit={onSubmitQuestion}
        isLoading={isLoading}
        initialQuestion={currentResponse?.question}
      />

      {/* Error Banner (if API or network failed) */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl text-sm flex items-center space-x-3">
          <div className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 space-y-4 animate-pulse">
          <div className="flex items-center justify-between">
            <div className="h-6 w-36 bg-slate-200 rounded-full" />
            <div className="h-4 w-24 bg-slate-200 rounded" />
          </div>
          <div className="space-y-2">
            <div className="h-4 w-full bg-slate-200 rounded" />
            <div className="h-4 w-4/5 bg-slate-200 rounded" />
          </div>
          <div className="h-28 w-full bg-slate-100 rounded-xl" />
        </div>
      )}

      {/* Results View */}
      {currentResponse && !isLoading && (
        <div className="space-y-6 animate-fadeIn">
          {/* Grounded Plain-English Answer */}
          <AnswerCard
            response={currentResponse}
            isSaved={savedQueryIds.has(currentResponse.request_id)}
            onToggleSave={() => onToggleSave(currentResponse)}
          />

          {/* Tabular Results (if execution succeeded and returned rows) */}
          {currentResponse.execution_result && (
            <ResultTable result={currentResponse.execution_result} />
          )}

          {/* Generated SQL Code Panel */}
          {currentResponse.sql && (
            <SqlPanel
              sql={currentResponse.sql}
              parameters={currentResponse.parameters}
              validationStatus={currentResponse.validation_status}
            />
          )}

          {/* Honest Pipeline Execution Trace */}
          <PipelineTrace stages={currentResponse.pipeline_stages} />
        </div>
      )}

      {/* Default Feature Highlights (when no query has been submitted yet) */}
      {!currentResponse && !isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-6 text-left">
          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-800">AST Policy Guard</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Every query is parsed into an abstract syntax tree. Mutating statements (`DROP`, `DELETE`, `UPDATE`) are rejected before execution.
            </p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Database className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-800">Live Schema Introspection</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Dynamically reads SQLite catalog for columns, data types, primary & foreign keys to construct context without stale hardcoding.
            </p>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-2">
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Zap className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-800">Continuous Self-Healing</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              If an initial query encounters syntax or validation issues, the agent feeds errors back into the LLM for immediate autonomous correction.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
