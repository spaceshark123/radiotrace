import { AdvancedMarker, APIProvider, InfoWindow, Map } from '@vis.gl/react-google-maps'
import {
  Ambulance,
  CarFront,
  CircleHelp,
  Flame,
  House,
  PersonStanding,
  ShieldAlert,
  Siren,
  type LucideIcon,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import type { Incident } from '../types/incident'
import ConfidenceMeter from './ConfidenceMeter'

interface Props {
  incidents: Incident[]
  selectedId: number | null
  onSelect: (incident: Incident) => void
  center: { lat: number; lng: number }
}

function firstLocation(incident: Incident) {
  return incident.location[0]
}

const CATEGORY_MARKERS: Record<string, LucideIcon> = {
  violent_crime: Siren,
  traffic_collision: CarFront,
  fire: Flame,
  medical_emergency: Ambulance,
  missing_person: PersonStanding,
  public_safety_threat: ShieldAlert,
  property_crime: House,
  other_crime: CircleHelp,
  unknown: CircleHelp,
}

export default function IncidentMap({ incidents, selectedId, onSelect, center }: Props) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? ''
  const mapId = import.meta.env.VITE_GOOGLE_MAP_ID || 'radiotrace-atlanta'
  const [infoId, setInfoId] = useState<number | null>(null)

  const selected = useMemo(
    () => incidents.find((item) => item.id === (infoId ?? selectedId)),
    [incidents, infoId, selectedId],
  )
  const selectedLocation = selected ? firstLocation(selected) : undefined
  const sameLocationIncidents = selectedLocation
    ? incidents.filter((incident) => {
        const location = firstLocation(incident)
        return (
          location?.latitude === selectedLocation.latitude &&
          location.longitude === selectedLocation.longitude
        )
      })
    : []

  if (!apiKey) {
    return (
      <div className="map-fallback">
        <p>
          Add <code>VITE_GOOGLE_MAPS_API_KEY</code> to enable the Google Map. Atlanta incident
          pins are listed below.
        </p>
        <ul>
          {incidents.map((incident) => {
            const loc = firstLocation(incident)
            return (
              <li key={incident.id}>
                <button type="button" onClick={() => onSelect(incident)}>
                  #{incident.id} {loc?.google_maps ?? 'unknown'} (
                  {loc?.latitude.toFixed(3)}, {loc?.longitude.toFixed(3)})
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    )
  }

  return (
    <APIProvider apiKey={apiKey}>
      <Map
        className="google-map"
        defaultCenter={center}
        defaultZoom={12}
        mapId={mapId}
        gestureHandling="greedy"
        disableDefaultUI={false}
      >
        {incidents.map((incident) => {
          const loc = firstLocation(incident)
          if (!loc) return null
          const severity = incident.type[0]?.severity ?? 'Unknown'
          const category = String(incident.category ?? incident.type[0]?.category ?? 'unknown')
          const MarkerIcon = CATEGORY_MARKERS[category] ?? CATEGORY_MARKERS.unknown
          const severityPriority = { Severe: 3, Moderate: 2, Minor: 1, Unknown: 0 }[severity] ?? 0
          const zIndex = category === 'unknown' ? 0 : 100 + severityPriority
          return (
            <AdvancedMarker
              key={incident.id}
              position={{ lat: loc.latitude, lng: loc.longitude }}
              zIndex={zIndex}
              title={`Incident ${incident.id}`}
              onClick={() => {
                setInfoId(incident.id)
                onSelect(incident)
              }}
            >
              <span
                className={`map-marker marker-${severity.toLowerCase()}`}
                aria-label={`${category.replaceAll('_', ' ')} incident`}
              >
                <MarkerIcon size={16} strokeWidth={2.5} />
              </span>
            </AdvancedMarker>
          )
        })}
        {selected && selectedLocation ? (
          <InfoWindow
            position={{
              lat: selectedLocation.latitude,
              lng: selectedLocation.longitude,
            }}
            onCloseClick={() => setInfoId(null)}
          >
            <div className="info-window">
              {sameLocationIncidents.map((incident) => {
                const kind = incident.type[0]
                const category = incident.category ?? kind?.category ?? 'unknown'
                return (
                  <button
                    className="info-incident info-incident-hit"
                    key={incident.id}
                    type="button"
                    onClick={() => {
                      setInfoId(incident.id)
                      onSelect(incident)
                    }}
                  >
                    <strong>Incident #{incident.id}</strong>
                    {category && (
                      <>
                        <div style={{ height: '0.25rem' }}></div>
                        <span className="badge badge-category">
                          {category.replaceAll('_', ' ')}
                        </span>
                      </>
                    )}
                    <p>{kind?.description}</p>
                    <ConfidenceMeter incidentType={kind} />
                  </button>
                )
              })}
            </div>
          </InfoWindow>
        ) : null}
      </Map>
    </APIProvider>
  )
}
