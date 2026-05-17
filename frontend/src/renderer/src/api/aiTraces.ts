import { aiHttpClient } from './request'

export interface TraceSpanRead {
  id: string
  step_id: string
  source_id: string
  start_offset: number
  end_offset: number
  text?: string | null
  metadata_json?: Record<string, unknown> | null
}

export interface TraceSourceRead {
  id: string
  step_id: string
  source_type: string
  source_ref?: string | null
  label: string
  preview?: string | null
  jump_target?: Record<string, unknown> | null
  metadata_json?: Record<string, unknown> | null
  spans: TraceSpanRead[]
}

export interface TraceStepRead {
  id: string
  run_id: string
  name: string
  kind: string
  status: string
  timestamp: string
  started_at: string
  ended_at?: string | null
  external_id?: string | null
  input_summary?: Record<string, unknown> | null
  output_summary?: Record<string, unknown> | null
  input_schema?: Record<string, unknown> | null
  output_schema?: Record<string, unknown> | null
  error?: string | null
  metadata_json?: Record<string, unknown> | null
  sources: TraceSourceRead[]
}

export interface TraceRunRead {
  id: string
  project_id?: number | null
  card_id?: number | null
  entrypoint: string
  status: string
  started_at: string
  ended_at?: string | null
  metadata_json?: Record<string, unknown> | null
  steps: TraceStepRead[]
}

export interface TraceRunQuery {
  projectId?: number | null
  cardId?: number | null
  entrypoint?: string | null
  limit?: number
}

export function listTraceRuns(query: TraceRunQuery): Promise<TraceRunRead[]> {
  return aiHttpClient.get<TraceRunRead[]>(
    '/ai-traces/runs',
    {
      project_id: query.projectId ?? undefined,
      card_id: query.cardId ?? undefined,
      entrypoint: query.entrypoint ?? undefined,
      limit: query.limit ?? 20
    },
    '/api',
    { showLoading: false }
  )
}

export function getTraceRun(runId: string): Promise<TraceRunRead> {
  return aiHttpClient.get<TraceRunRead>(`/ai-traces/runs/${runId}`, undefined, '/api', {
    showLoading: false
  })
}

export function listTraceSteps(runId: string): Promise<TraceStepRead[]> {
  return aiHttpClient.get<TraceStepRead[]>(`/ai-traces/runs/${runId}/steps`, undefined, '/api', {
    showLoading: false
  })
}
