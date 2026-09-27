import AudioPlayer from './AudioPlayer'
import ConfidenceMeter from './ConfidenceMeter'
import type { Incident } from '../types/incident'

interface Props {
  incident: Incident
  selected: boolean
  onSelect: (incident: Incident) => void
}

export default function IncidentCard({ incident, selected, onSelect }: Props) {
  const kind = incident.type[0]
  const place = incident.location[0]
  const category = incident.category ?? kind?.category ?? 'unknown'
  const categoryLabel = category.replaceAll('_', ' ')
  return (
    <article
      id={`incident-${incident.id}`}
      className={selected ? 'incident-card selected' : 'incident-card'}
    >
      <button type="button" className="card-hit" onClick={() => onSelect(incident)}>
        <div className="card-top">
          <h3>Incident #{incident.id}</h3>
          <ConfidenceMeter incidentType={kind} />
        </div>
        <p>{kind?.description ?? 'Awaiting analysis'}</p>
        <span className="badge badge-category">{categoryLabel}</span>
        <p className="muted">{place?.google_maps ?? 'Location pending'}</p>
      </button>
      <AudioPlayer recordings={incident.recordings} />
    </article>
  )
}
