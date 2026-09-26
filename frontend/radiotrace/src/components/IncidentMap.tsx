import { AdvancedMarker, APIProvider, InfoWindow, Map } from '@vis.gl/react-google-maps'
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

export default function IncidentMap({ incidents, selectedId, onSelect, center }: Props) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? ''
  const mapId = import.meta.env.VITE_GOOGLE_MAP_ID || 'radiotrace-atlanta'
  const [infoId, setInfoId] = useState<number | null>(null)

  const selected = useMemo(
    () => incidents.find((item) => item.id === (infoId ?? selectedId)),
    [incidents, infoId, selectedId],
  )

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
          return (
            <AdvancedMarker
              key={incident.id}
              position={{ lat: loc.latitude, lng: loc.longitude }}
              title={`Incident ${incident.id}`}
              onClick={() => {
                setInfoId(incident.id)
                onSelect(incident)
              }}
            >
              <span className={`pin pin-${severity.toLowerCase()}`}>{severity[0]}</span>
            </AdvancedMarker>
          )
        })}
        {selected && firstLocation(selected) ? (
          <InfoWindow
            position={{
              lat: firstLocation(selected)!.latitude,
              lng: firstLocation(selected)!.longitude,
            }}
            onCloseClick={() => setInfoId(null)}
          >
            <div className="info-window">
              <strong>Incident #{selected.id}</strong>
              <p>{selected.type[0]?.description}</p>
              <ConfidenceMeter incidentType={selected.type[0]} />
            </div>
          </InfoWindow>
        ) : null}
      </Map>
    </APIProvider>
  )
}
