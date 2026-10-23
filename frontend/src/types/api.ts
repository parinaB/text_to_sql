export interface SystemStatus {
  status: string;
  database_connected: boolean;
  database_path: string;
  llm_provider: string;
  llm_model: string;
  embedding_provider: string;
  embedding_model: string;
  table_counts: Record<string, number>;
  query_timeout_seconds: number;
  max_result_rows: number;
}

export type PipelineStageStatus = 'COMPLETED' | 'FAILED' | 'SKIPPED' | 'RUNNING';

export interface PipelineStage {
  name: string;
  label: string;
  status: PipelineStageStatus;
  details?: string | null;
  duration_ms?: number | null;
}

export interface ExecutionResult {
  success: boolean;
  rows: Array<Record<string, any>>;
  columns: string[];
  row_count: number;
  execution_time_ms: number;
  is_empty: boolean;
  is_truncated: boolean;
  error_message?: string | null;
}

export interface QueryAPIResponse {
  request_id: string;
  question: string;
  timestamp: string;
  sql?: string | null;
  parameters: Record<string, any>;
  assumptions: string[];
  validation_status: 'PASSED' | 'REJECTED' | 'UNSUPPORTED' | 'ERROR';
  execution_result?: ExecutionResult | null;
  answer: string;
  attempts: number;
  total_time_ms: number;
  pipeline_stages: PipelineStage[];
}

export interface SchemaColumn {
  name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
}

export interface ForeignKey {
  column: string;
  target_table: string;
  target_column: string;
}

export interface SchemaTable {
  name: string;
  row_count: number;
  primary_keys: string[];
  columns: SchemaColumn[];
  foreign_keys: ForeignKey[];
  sample_rows: Array<Record<string, any>>;
}

export interface DatabaseSchemaResponse {
  database_name: string;
  tables: SchemaTable[];
}

export interface BenchmarkQueryItem {
  id: string;
  question: string;
  category: string;
  expected_status: string;
  observed_status: string;
  time_ms: number;
  passed: boolean;
  generated_sql?: string | null;
}

export interface BenchmarkEvaluation {
  total_test_cases: number;
  valid_business_queries: number;
  sql_execution_accuracy_pct: number;
  result_correctness_pct: number;
  malicious_test_cases: number;
  safety_rejection_rate_pct: number;
  safety_violations: number;
  unsupported_test_cases: number;
  unsupported_detection_rate_pct: number;
  avg_latency_ms: number;
  results: BenchmarkQueryItem[];
}
