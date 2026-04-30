import type {
  RecommendationRequest,
  RecommendationResponse,
  ReferenceDataResponse,
} from '../types/api'

const BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const msg = (body as { message?: string }).message
    throw new Error(msg ?? `HTTP ${res.status}`)
  }
  return body as T
}

export function postRecommendations(req: RecommendationRequest) {
  return request<RecommendationResponse>('/recommendations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export function getReferenceData() {
  return request<ReferenceDataResponse>('/reference-data')
}
