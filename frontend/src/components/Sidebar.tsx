import React from 'react';
import {
  Compass,
  Database,
  History,
  BookmarkCheck,
  BarChart3,
  Settings as SettingsIcon,
  PlusCircle,
  Cpu,
  HardDrive,
  ShieldCheck,
} from 'lucide-react';
import type { SystemStatus } from '../types/api';

export type NavTab = 'workspace' | 'history' | 'saved' | 'database' | 'evaluation' | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  onNewQuery: () => void;
  status: SystemStatus | null;
  savedCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  onNewQuery,
  status,
  savedCount,
}) => {
  const isOnline = status?.database_connected ?? false;

  const navItems = [
    { id: 'workspace' as NavTab, label: 'Query Workspace', icon: Compass },
    { id: 'database' as NavTab, label: 'Database Explorer', icon: Database },
    { id: 'history' as NavTab, label: 'Query History', icon: History },
    { id: 'saved' as NavTab, label: 'Saved Queries', icon: BookmarkCheck, badge: savedCount > 0 ? savedCount : undefined },
    { id: 'evaluation' as NavTab, label: 'Evaluation Dashboard', icon: BarChart3, badge: '100%' },
    { id: 'settings' as NavTab, label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <aside className="w-72 bg-navy-900 border-r border-navy-800 text-slate-300 flex flex-col justify-between shrink-0 select-none">
      {/* Brand & New Query */}
      <div>
        {/* Logo and Product Title */}
        <div className="px-6 py-6 border-b border-navy-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-brand-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white font-bold text-lg">
              QP
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-white text-base tracking-tight">QueryPilot</span>
                <span className="text-[10px] font-semibold tracking-wider uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  AI
                </span>
              </div>
              <p className="text-xs text-slate-400">Self-Verifying Text-to-SQL</p>
            </div>
          </div>
        </div>

        {/* New Query Primary Action Button */}
        <div className="p-4">
          <button
            onClick={() => {
              onNewQuery();
              onSelectTab('workspace');
            }}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors shadow-md shadow-indigo-600/25 active:scale-[0.99]"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Query</span>
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="px-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-navy-800 text-white shadow-sm border border-navy-700'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-navy-850'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon
                    className={`w-4 h-4 ${
                      isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-slate-300'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                      item.id === 'evaluation'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-navy-700 text-slate-300'
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Live System & Model Status Panel */}
      <div className="p-4 border-t border-navy-800 bg-navy-950/40 text-xs space-y-3">
        <div className="flex items-center justify-between text-slate-400">
          <span className="font-semibold uppercase tracking-wider text-[10px] text-slate-400">
            System Status
          </span>
          <div className="flex items-center space-x-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                isOnline ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)] animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className={isOnline ? 'text-emerald-400 font-medium' : 'text-rose-400 font-medium'}>
              {isOnline ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>

        <div className="space-y-2 pt-1 text-[11px]">
          {/* Database Info */}
          <div className="flex items-center justify-between text-slate-300 bg-navy-900/80 px-2.5 py-1.5 rounded border border-navy-800">
            <div className="flex items-center space-x-2 truncate">
              <HardDrive className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span className="truncate">{status?.database_path || 'business.db'}</span>
            </div>
            <span className="text-[10px] text-slate-400 shrink-0">
              {status?.table_counts ? `${Object.keys(status.table_counts).length} tables` : 'SQLite'}
            </span>
          </div>

          {/* Active LLM Model */}
          <div className="flex items-center justify-between text-slate-300 bg-navy-900/80 px-2.5 py-1.5 rounded border border-navy-800">
            <div className="flex items-center space-x-2 truncate">
              <Cpu className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              <span className="truncate font-mono text-[10px]">{status?.llm_model || 'llama3:8b'}</span>
            </div>
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">
              {status?.llm_provider || 'ollama'}
            </span>
          </div>

          {/* AST Policy Guard */}
          <div className="flex items-center space-x-2 text-emerald-400/90 text-[10px] px-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>AST Read-Only Guard Active</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
