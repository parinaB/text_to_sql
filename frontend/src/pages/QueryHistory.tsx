import React, { useState } from 'react';
import type { QueryAPIResponse } from '../types/api';
import {
  History,
  Star,
  Play,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Search,
  Hash,
  Terminal,
  BookmarkCheck,
} from 'lucide-react';

interface QueryHistoryProps {
  history: QueryAPIResponse[];
  savedQueryIds: Set<string>;
  onToggleSave: (resp: QueryAPIResponse) => void;
  onRerunQuery: (question: string) => void;
  isSavedOnlyView?: boolean;
}

export const QueryHistory: React.FC<QueryHistoryProps> = ({
  history,
  savedQueryIds,
  onToggleSave,
  onRerunQuery,
  isSavedOnlyView = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const filteredQueries = history.filter((item) => {
    if (isSavedOnlyView && !savedQueryIds.has(item.request_id)) {
      return false;
    }
    if (statusFilter !== 'ALL' && item.validation_status !== statusFilter) {
      return false;
    }
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const matchQuestion = item.question.toLowerCase().includes(q);
      const matchSql = item.sql?.toLowerCase().includes(q) ?? false;
      const matchAnswer = item.answer.toLowerCase().includes(q);
      return matchQuestion || matchSql || matchAnswer;
    }
    return true;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle className="w-3 h-3 text-emerald-600" />
            <span>PASSED</span>
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3 h-3 text-rose-600" />
            <span>REJECTED</span>
          </span>
        );
      case 'UNSUPPORTED':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>UNSUPPORTED</span>
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto py-8 px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div className="flex items-center space-x-3">
          {isSavedOnlyView ? (
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-100">
              <BookmarkCheck className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center border border-indigo-100">
              <History className="w-5 h-5" />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {isSavedOnlyView ? 'Saved Queries' : 'Query History'}
            </h1>
            <p className="text-xs text-slate-500">
              {isSavedOnlyView
                ? 'Bookmarked high-priority business queries for quick reference and reruns.'
                : 'Complete audit log of natural language questions, AST validation statuses, and execution times.'}
            </p>
          </div>
        </div>

        <div className="text-xs text-slate-400 font-mono">
          Showing {filteredQueries.length} {filteredQueries.length === 1 ? 'record' : 'records'}
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search questions, SQL, or answers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-white rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center space-x-1.5 text-xs">
          {['ALL', 'PASSED', 'REJECTED', 'UNSUPPORTED'].map((filter) => (
            <button
              key={filter}
              onClick={() => setStatusFilter(filter)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                statusFilter === filter
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* History Items List */}
      {filteredQueries.length === 0 ? (
        <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-12 text-center space-y-2">
          {isSavedOnlyView ? (
            <>
              <Star className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-sm font-semibold text-slate-700">No saved queries yet</p>
              <p className="text-xs text-slate-500">
                Click the star icon on any query in the Workspace to bookmark it here.
              </p>
            </>
          ) : (
            <>
              <History className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-sm font-semibold text-slate-700">No queries in history</p>
              <p className="text-xs text-slate-500">
                Submit a question from the Query Workspace to start building your audit log.
              </p>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredQueries.map((item) => {
            const isSaved = savedQueryIds.has(item.request_id);
            return (
              <div
                key={item.request_id}
                className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3 shadow-xs hover:border-slate-300 transition-all"
              >
                {/* Header: Question & Metadata */}
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-slate-900 text-sm">
                        {item.question}
                      </span>
                      {getStatusBadge(item.validation_status)}
                    </div>
                    <div className="flex items-center space-x-3 text-[11px] text-slate-400 font-mono">
                      <span className="flex items-center space-x-1">
                        <Hash className="w-3 h-3" />
                        <span>{item.request_id}</span>
                      </span>
                      <span>•</span>
                      <span>{item.timestamp}</span>
                      <span>•</span>
                      <span className="flex items-center space-x-1">
                        <Clock className="w-3 h-3" />
                        <span>{item.total_time_ms.toFixed(1)} ms</span>
                      </span>
                    </div>
                  </div>

                  {/* Actions: Star & Rerun */}
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onToggleSave(item)}
                      className={`p-1.5 rounded-lg border transition-all ${
                        isSaved
                          ? 'bg-amber-50 border-amber-300 text-amber-600'
                          : 'bg-white border-slate-200 text-slate-400 hover:text-slate-600 hover:border-slate-300'
                      }`}
                      title={isSaved ? 'Remove from Saved' : 'Save Query'}
                    >
                      <Star className={`w-4 h-4 ${isSaved ? 'fill-amber-400' : ''}`} />
                    </button>

                    <button
                      onClick={() => onRerunQuery(item.question)}
                      className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition-all border border-indigo-100"
                    >
                      <Play className="w-3 h-3 fill-indigo-600" />
                      <span>Rerun</span>
                    </button>
                  </div>
                </div>

                {/* Answer Summary */}
                <div className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100 leading-relaxed">
                  <span className="font-semibold text-slate-700">Answer: </span>
                  {item.answer}
                </div>

                {/* SQL Snippet (if query had SQL) */}
                {item.sql && (
                  <div className="bg-navy-950 p-3 rounded-xl text-xs font-mono text-indigo-200 overflow-x-auto flex items-center justify-between">
                    <div className="flex items-center space-x-2 truncate">
                      <Terminal className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                      <span className="truncate">{item.sql}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
