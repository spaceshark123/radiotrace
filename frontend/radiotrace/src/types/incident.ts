export type Severity = 'Severe' | 'Moderate' | 'Minor' | 'Unknown'

export interface Recording {
  start_time: number
  end_time: number
  audio: string
}

export interface IncidentLocation {
  google_maps: string
  latitude: number
  longitude: number
  confidence: number
}

export interface IncidentType {
  severity: Severity | string
  description: string
  confidence: number
}

export interface Incident {
  id: number
  recordings: Recording[]
  location: IncidentLocation[]
  type: IncidentType[]
}

export interface CityConfig {
  city: string
  state: string
  center: { lat: number; lng: number }
}
