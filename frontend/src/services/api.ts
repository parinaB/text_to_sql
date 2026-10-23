import type {
  BenchmarkEvaluation,
  DatabaseSchemaResponse,
  QueryAPIResponse,
  SystemStatus,
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_URL || '';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail || `API request failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${BASE_URL}/api/status`);
  return handleResponse<SystemStatus>(res);
}

export async function submitQuery(question: string): Promise<QueryAPIResponse> {
  const res = await fetch(`${BASE_URL}/api/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  });
  return handleResponse<QueryAPIResponse>(res);
}

export async function fetchDatabaseSchema(): Promise<DatabaseSchemaResponse> {
  const res = await fetch(`${BASE_URL}/api/schema`);
  return handleResponse<DatabaseSchemaResponse>(res);
}

export async function fetchQueryHistory(): Promise<QueryAPIResponse[]> {
  const res = await fetch(`${BASE_URL}/api/history`);
  return handleResponse<QueryAPIResponse[]>(res);
}

export async function fetchEvaluationResults(): Promise<BenchmarkEvaluation> {
  const res = await fetch(`${BASE_URL}/api/evaluation`);
  return handleResponse<BenchmarkEvaluation>(res);
}
