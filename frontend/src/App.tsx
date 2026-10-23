import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import type { NavTab } from './components/Sidebar';
import { QueryWorkspace } from './pages/QueryWorkspace';
import { DatabaseExplorer } from './pages/DatabaseExplorer';
import { QueryHistory } from './pages/QueryHistory';
import { EvaluationDashboard } from './pages/EvaluationDashboard';
import { SettingsPage } from './pages/SettingsPage';
import type { QueryAPIResponse, SystemStatus } from './types/api';
import { fetchSystemStatus, submitQuery, fetchQueryHistory } from './services/api';

const SAVED_QUERIES_STORAGE_KEY = 'querypilot_saved_queries_ids';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('workspace');
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [currentResponse, setCurrentResponse] = useState<QueryAPIResponse | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryAPIResponse[]>([]);
  const [savedQueryIds, setSavedQueryIds] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem(SAVED_QUERIES_STORAGE_KEY);
      return stored ? new Set(JSON.parse(stored)) : new Set<string>();
    } catch {
      return new Set<string>();
    }
  });
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Load system status and history on mount
  useEffect(() => {
    const initData = async () => {
      try {
        const [status, history] = await Promise.all([
          fetchSystemStatus().catch(() => null),
          fetchQueryHistory().catch(() => []),
        ]);
        if (status) setSystemStatus(status);
        if (history && history.length > 0) {
          setQueryHistory(history);
          setCurrentResponse(history[0]);
        }
      } catch (err) {
        console.warn('Initial system fetch encountered non-critical error:', err);
      }
    };
    initData();
  }, []);

  // Persist saved queries
  const handleToggleSave = (resp: QueryAPIResponse) => {
    setSavedQueryIds((prev) => {
      const next = new Set(prev);
      if (next.has(resp.request_id)) {
        next.delete(resp.request_id);
      } else {
        next.add(resp.request_id);
      }
      try {
        localStorage.setItem(SAVED_QUERIES_STORAGE_KEY, JSON.stringify(Array.from(next)));
      } catch {
        // storage quota exceeded or disabled
      }
      return next;
    });
  };

  const handleSubmitQuestion = async (question: string) => {
    setIsLoading(true);
    setApiError(null);
    try {
      const resp = await submitQuery(question);
      setCurrentResponse(resp);
      setQueryHistory((prev) => [resp, ...prev.filter((q) => q.request_id !== resp.request_id)]);
      setActiveTab('workspace');
    } catch (err: any) {
      setApiError(err.message || 'Failed to execute query against agent backend');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewQuery = () => {
    setCurrentResponse(null);
    setApiError(null);
    setActiveTab('workspace');
  };

  const handleRerunQuery = (question: string) => {
    handleSubmitQuestion(question);
  };

  const handleAskAboutTable = (tableName: string) => {
    handleSubmitQuestion(`Show the top records and details from the ${tableName} table.`);
  };

  const handleLoadBenchmarkQuestion = (question: string) => {
    handleSubmitQuestion(question);
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden font-sans">
      {/* Dark Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onNewQuery={handleNewQuery}
        status={systemStatus}
        savedCount={savedQueryIds.size}
      />

      {/* Main Content Workspace */}
      <main className="flex-1 overflow-y-auto bg-slate-50 relative">
        {activeTab === 'workspace' && (
          <QueryWorkspace
            currentResponse={currentResponse}
            isLoading={isLoading}
            onSubmitQuestion={handleSubmitQuestion}
            savedQueryIds={savedQueryIds}
            onToggleSave={handleToggleSave}
            error={apiError}
          />
        )}

        {activeTab === 'database' && (
          <DatabaseExplorer onAskAboutTable={handleAskAboutTable} />
        )}

        {activeTab === 'history' && (
          <QueryHistory
            history={queryHistory}
            savedQueryIds={savedQueryIds}
            onToggleSave={handleToggleSave}
            onRerunQuery={handleRerunQuery}
            isSavedOnlyView={false}
          />
        )}

        {activeTab === 'saved' && (
          <QueryHistory
            history={queryHistory}
            savedQueryIds={savedQueryIds}
            onToggleSave={handleToggleSave}
            onRerunQuery={handleRerunQuery}
            isSavedOnlyView={true}
          />
        )}

        {activeTab === 'evaluation' && (
          <EvaluationDashboard onLoadBenchmarkQuestion={handleLoadBenchmarkQuestion} />
        )}

        {activeTab === 'settings' && (
          <SettingsPage status={systemStatus} />
        )}
      </main>
    </div>
  );
};

export default App;
