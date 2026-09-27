export type Severity = 'Severe' | 'Moderate' | 'Minor' | 'Unknown'
export type IncidentCategory =
    | 'violent_crime'
    | 'traffic_collision'
    | 'fire'
    | 'medical_emergency'
    | 'missing_person'
    | 'public_safety_threat'
    | 'property_crime'
    | 'other_crime'

export interface IncidentLocation {
  google_maps: string
  latitude: number
  longitude: number
  confidence: number
}

export interface IncidentType {
  severity: Severity | string
  category: IncidentCategory
  description: string
  confidence: number
}

export interface Incident {
  id: number
  recordings: string[]
  location: IncidentLocation[]
  type: IncidentType[]
  category: IncidentCategory
}

export interface CityConfig {
  city: string
  state: string
  center: { lat: number; lng: number }
}
