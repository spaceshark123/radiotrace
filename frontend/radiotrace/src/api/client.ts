import type { CityConfig, Incident } from '../types/incident'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'
const RADIO_CLIP_LIST_URL = import.meta.env.VITE_RADIO_CLIP_LIST_URL ?? `${API_BASE}/radio/clips`
const RADIO_CLIP_FILE_URL = import.meta.env.VITE_RADIO_CLIP_FILE_URL ?? `${API_BASE}/radio/clips/file`

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

export interface IncomingClip {
  id: string
  filename: string
  encoding: 'mp3' | 'm4a'
  status: 'discovered' | 'fetched' | 'error'
  size?: number
  contentType?: string
  objectUrl?: string
  error?: string
}

export interface RadioClip {
  id: string
  filename: string
  encoding: 'mp3' | 'm4a'
  metadata: {
    start_time: number
    end_time: number
    transcript: string
  }
  audio_url: string
}

export async function fetchIncomingClipNames(): Promise<IncomingClip[]> {
  const response = await fetch(RADIO_CLIP_LIST_URL)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  const body = (await response.json()) as IncomingClip[] | { files?: IncomingClip[] }
  if (Array.isArray(body)) {
    return body
  }
  return body.files ?? []
}

export async function fetchClip(clipId: string): Promise<RadioClip> {
  const response = await fetch(`${API_BASE}/radio/clips/${encodeURIComponent(clipId)}`)
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<RadioClip>
}

export async function fetchIncomingClip(clip: IncomingClip): Promise<Response> {
  const separator = RADIO_CLIP_FILE_URL.endsWith('/') ? '' : '/'
  const response = await fetch(
    `${RADIO_CLIP_FILE_URL}${separator}${encodeURIComponent(clip.id)}`,
  )
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.startsWith('audio/')) {
    throw new Error(`Expected an audio response, received ${contentType || 'unknown content type'}`)
  }
  return response
}

export function audioUrl(fileId: string): string {
  return `${API_BASE}/radio/clips/file/${fileId}`
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
