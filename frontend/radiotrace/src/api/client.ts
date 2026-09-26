import type { CityConfig, Incident } from '../types/incident'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { error?: string }
    return body.error ?? response.statusText
  } catch {
    return response.statusText
  }
}

export async function fetchHealth(): Promise<{ status: string; city?: string }> {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json()
}

export async function fetchCityConfig(): Promise<CityConfig> {
  const response = await fetch(`${API_BASE}/config`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json()
}

export async function fetchIncidents(): Promise<Incident[]> {
  const response = await fetch(`${API_BASE}/incidents`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  const body = (await response.json()) as { incidents: Incident[] }
  return body.incidents
}

export async function seedDemoIncidents(): Promise<Incident[]> {
  const response = await fetch(`${API_BASE}/incidents/seed`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  const body = (await response.json()) as { incidents: Incident[] }
  return body.incidents
}

export async function fetchRadioStatus(): Promise<{
  stream_url: string
  live: boolean
  city: string
  feed_id: string
}> {
  const response = await fetch(`${API_BASE}/radio/status`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json()
}

export function audioUrl(fileId: string): string {
  return `${API_BASE}/audio/${fileId}`
}

export function liveStreamUrl(): string {
  return `${API_BASE}/radio/stream`
}

export async function uploadClip(file: File, startTime: number, endTime: number): Promise<unknown> {
  const body = new FormData()
  body.append('file', file)
  body.append('start_time', String(startTime))
  body.append('end_time', String(endTime))
  const response = await fetch(`${API_BASE}/pipeline/process`, {
    method: 'POST',
    body,
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json()
}
