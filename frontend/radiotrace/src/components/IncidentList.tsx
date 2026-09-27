import IncidentCard from './IncidentCard'
import type { Incident } from '../types/incident'

interface Props {
  incidents: Incident[]
  selectedId: number | null
  onSelect: (incident: Incident) => void
}

export default function IncidentList({ incidents, selectedId, onSelect }: Props) {
  if (incidents.length === 0) {
    return (
      <p className="muted">
        No incidents yet. 
      </p>
    )
  }

  return (
    <div className="incident-list">
      {incidents.map((incident) => (
        <IncidentCard
          key={incident.id}
          incident={incident}
          selected={incident.id === selectedId}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}
