import React from 'react';
import { Table, Download, Database, AlertCircle } from 'lucide-react';
import type { ExecutionResult } from '../types/api';

interface ResultTableProps {
  result?: ExecutionResult | null;
}

export const ResultTable: React.FC<ResultTableProps> = ({ result }) => {
  if (!result) return null;

  const { rows, columns, row_count, execution_time_ms, is_empty, is_truncated, error_message } =
    result;

  if (error_message) {
    return (
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-5 flex items-start space-x-3 text-rose-800">
        <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="font-semibold">Query execution error</p>
          <p className="mt-1 font-mono text-xs">{error_message}</p>
        </div>
      </div>
    );
  }

  if (is_empty || !rows || rows.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center space-y-2">
        <Database className="w-8 h-8 text-slate-300 mx-auto" />
        <p className="text-sm font-semibold text-slate-700">Zero records returned</p>
        <p className="text-xs text-slate-500">
          The query completed successfully ({execution_time_ms.toFixed(1)} ms), but found no matching records in the database.
        </p>
      </div>
    );
  }

  const exportCSV = () => {
    if (!columns || !rows) return;
    const headerLine = columns.join(',');
    const rowLines = rows.map((r) =>
      columns.map((c) => {
        const val = r[c];
        if (val === null || val === undefined) return '""';
        const strVal = String(val).replace(/"/g, '""');
        return `"${strVal}"`;
      }).join(',')
    );
    const csvContent = 'data:text/csv;charset=utf-8,' + [headerLine, ...rowLines].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `querypilot_export_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatCellValue = (colName: string, val: any) => {
    if (val === null || val === undefined) {
      return <span className="text-slate-400 italic font-mono text-xs">NULL</span>;
    }
    const lowerCol = colName.toLowerCase();
    if (typeof val === 'number') {
      if (lowerCol.includes('price') || lowerCol.includes('revenue') || lowerCol.includes('amount') || lowerCol.includes('total') || lowerCol.includes('spending')) {
        return <span className="font-mono text-slate-800">${val.toFixed(2)}</span>;
      }
      return <span className="font-mono text-slate-800">{val.toLocaleString()}</span>;
    }
    return <span className="text-slate-700">{String(val)}</span>;
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
      {/* Table Subtitle and Export Action */}
      <div className="px-5 py-3.5 bg-slate-50/70 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <Table className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-700">
            Query Results ({row_count} {row_count === 1 ? 'row' : 'rows'})
          </span>
          <span className="text-xs text-slate-400">• {execution_time_ms.toFixed(1)} ms</span>
          {is_truncated && (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">
              Truncated to safety limit
            </span>
          )}
        </div>

        <button
          onClick={exportCSV}
          className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-medium transition-colors shadow-xs"
        >
          <Download className="w-3.5 h-3.5 text-slate-500" />
          <span>Export CSV</span>
        </button>
      </div>

      {/* Table Content */}
      <div className="overflow-x-auto max-h-96 overflow-y-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-100/75 border-b border-slate-200 text-slate-600 font-semibold sticky top-0 z-10">
              {columns.map((col, idx) => (
                <th key={idx} className="py-2.5 px-4 font-mono uppercase tracking-wider text-[11px]">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row, rIdx) => (
              <tr
                key={rIdx}
                className="hover:bg-indigo-50/30 transition-colors"
              >
                {columns.map((col, cIdx) => (
                  <td key={cIdx} className="py-2.5 px-4 whitespace-nowrap">
                    {formatCellValue(col, row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
