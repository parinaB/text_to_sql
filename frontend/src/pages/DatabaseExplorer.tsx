import React, { useState, useEffect } from 'react';
import { fetchDatabaseSchema } from '../services/api';
import type { DatabaseSchemaResponse, SchemaTable } from '../types/api';
import {
  Database,
  Key,
  Link2,
  Table as TableIcon,
  Search,
  Loader2,
  Sparkles,
  RefreshCw,
  Layers,
} from 'lucide-react';

interface DatabaseExplorerProps {
  onAskAboutTable: (tableName: string) => void;
}

export const DatabaseExplorer: React.FC<DatabaseExplorerProps> = ({ onAskAboutTable }) => {
  const [data, setData] = useState<DatabaseSchemaResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [searchFilter, setSearchFilter] = useState('');

  const loadSchema = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await fetchDatabaseSchema();
      setData(res);
      if (res.tables && res.tables.length > 0) {
        setSelectedTable(res.tables[0].name);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to inspect database schema');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSchema();
  }, []);

  const currentTable: SchemaTable | undefined = data?.tables.find(
    (t) => t.name.toLowerCase() === selectedTable.toLowerCase()
  );

  const filteredTables = data?.tables.filter((t) => {
    if (!searchFilter.trim()) return true;
    const matchName = t.name.toLowerCase().includes(searchFilter.toLowerCase());
    const matchCol = t.columns.some((c) =>
      c.name.toLowerCase().includes(searchFilter.toLowerCase())
    );
    return matchName || matchCol;
  });

  return (
    <div className="w-full max-w-6xl mx-auto py-8 px-6 space-y-6">
      {/* Title & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <Database className="w-5 h-5 text-indigo-600" />
            <h1 className="text-2xl font-bold text-slate-900">Database Explorer</h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
              {data?.database_name || 'business.db'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time SQLite catalog inspection, active constraints, column types, and live row previews.
          </p>
        </div>

        <button
          onClick={loadSchema}
          disabled={isLoading}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-medium transition-all shadow-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Catalog</span>
        </button>
      </div>

      {/* Loading & Error States */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center p-12 space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-sm text-slate-500">Inspecting database catalog and relations...</p>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 p-4 rounded-xl text-rose-800 text-sm">
          {error}
        </div>
      )}

      {/* Main Explorer View */}
      {data && !isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Left Column: Tables List */}
          <div className="md:col-span-1 space-y-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter tables & columns..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-white rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
              />
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-2 space-y-1">
              <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                Approved Tables ({data.tables.length})
              </div>
              {filteredTables?.map((tbl) => {
                const isSelected = tbl.name.toLowerCase() === selectedTable.toLowerCase();
                return (
                  <button
                    key={tbl.name}
                    onClick={() => setSelectedTable(tbl.name)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all text-left ${
                      isSelected
                        ? 'bg-indigo-50 text-indigo-700 font-semibold border border-indigo-100 shadow-xs'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex items-center space-x-2 truncate">
                      <TableIcon className={`w-4 h-4 ${isSelected ? 'text-indigo-600' : 'text-slate-400'}`} />
                      <span className="truncate">{tbl.name}</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 shrink-0">
                      {tbl.row_count} rows
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Table Details & Live 5-Row Preview */}
          <div className="md:col-span-3 space-y-6">
            {currentTable ? (
              <>
                {/* Table Header Card */}
                <div className="bg-white rounded-2xl border border-slate-200 p-5 flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <h2 className="text-xl font-bold text-slate-900 font-mono">
                        {currentTable.name}
                      </h2>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                        {currentTable.row_count} records
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Primary Key: {currentTable.primary_keys.join(', ') || 'None declared'}
                    </p>
                  </div>

                  <button
                    onClick={() => onAskAboutTable(currentTable.name)}
                    className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-sm shadow-indigo-600/20 active:scale-95"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Ask Question About {currentTable.name}</span>
                  </button>
                </div>

                {/* Columns & Data Types */}
                <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
                  <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center space-x-2">
                    <Layers className="w-4 h-4 text-slate-500" />
                    <span className="text-xs font-semibold text-slate-700">
                      Columns & Schema Attributes ({currentTable.columns.length})
                    </span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="bg-slate-100/60 border-b border-slate-200 text-slate-600 font-semibold">
                          <th className="py-2.5 px-4 font-mono">Column</th>
                          <th className="py-2.5 px-4">Data Type</th>
                          <th className="py-2.5 px-4">Nullable</th>
                          <th className="py-2.5 px-4">Key Constraint</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {currentTable.columns.map((col) => (
                          <tr key={col.name} className="hover:bg-slate-50">
                            <td className="py-2 px-4 font-mono font-medium text-slate-900 flex items-center space-x-1.5">
                              {col.is_primary_key && <Key className="w-3.5 h-3.5 text-amber-500" />}
                              <span>{col.name}</span>
                            </td>
                            <td className="py-2 px-4 font-mono text-indigo-600 font-semibold">
                              {col.data_type}
                            </td>
                            <td className="py-2 px-4 text-slate-500">
                              {col.is_nullable ? 'YES' : 'NO'}
                            </td>
                            <td className="py-2 px-4">
                              {col.is_primary_key ? (
                                <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                                  PRIMARY KEY
                                </span>
                              ) : (
                                <span className="text-slate-400">—</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Foreign Keys (if any) */}
                {currentTable.foreign_keys.length > 0 && (
                  <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
                    <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center space-x-2">
                      <Link2 className="w-4 h-4 text-indigo-500" />
                      <span className="text-xs font-semibold text-slate-700">
                        Foreign Key Relationships ({currentTable.foreign_keys.length})
                      </span>
                    </div>
                    <div className="p-4 space-y-2">
                      {currentTable.foreign_keys.map((fk, idx) => (
                        <div
                          key={idx}
                          className="flex items-center space-x-2 text-xs bg-indigo-50/50 p-2.5 rounded-lg border border-indigo-100 text-slate-700 font-mono"
                        >
                          <span className="font-semibold text-indigo-700">{fk.column}</span>
                          <span className="text-slate-400">→</span>
                          <span className="font-semibold text-slate-900">
                            {fk.target_table}.{fk.target_column}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Live Sample Preview (first 5 rows) */}
                <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
                  <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <TableIcon className="w-4 h-4 text-slate-500" />
                      <span className="text-xs font-semibold text-slate-700">
                        Live 5-Row Data Preview
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400">Read-only sample from SQLite</span>
                  </div>

                  <div className="overflow-x-auto">
                    {currentTable.sample_rows.length > 0 ? (
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-slate-100/60 border-b border-slate-200 text-slate-600 font-semibold">
                            {Object.keys(currentTable.sample_rows[0]).map((col) => (
                              <th key={col} className="py-2.5 px-4 font-mono text-[11px]">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                          {currentTable.sample_rows.map((row, rIdx) => (
                            <tr key={rIdx} className="hover:bg-slate-50">
                              {Object.values(row).map((val: any, cIdx) => (
                                <td key={cIdx} className="py-2 px-4 whitespace-nowrap text-slate-700">
                                  {val === null ? (
                                    <span className="italic text-slate-400">NULL</span>
                                  ) : (
                                    String(val)
                                  )}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="p-6 text-center text-xs text-slate-400">No records found.</div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="bg-white p-12 text-center rounded-2xl border border-slate-200 text-slate-400 text-sm">
                Select a table from the sidebar to inspect its columns and data.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
