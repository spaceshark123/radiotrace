import type { IncidentType } from '../types/incident'

interface Props {
  incidentType?: IncidentType
}

function severityClass(severity: string | undefined): string {
  const value = (severity ?? 'Unknown').toLowerCase()
  if (value === 'severe') return 'badge-severe'
  if (value === 'moderate') return 'badge-moderate'
  if (value === 'minor') return 'badge-minor'
  return 'badge-unknown'
}

export default function ConfidenceMeter({ incidentType }: Props) {
  const confidence = incidentType?.confidence ?? 0
  const percent = Math.round(confidence * 100)
  return (
    <div className="confidence">
      <span className={`badge ${severityClass(incidentType?.severity)}`}>
        {incidentType?.severity ?? 'Unknown'}
      </span>
      <div className="meter" aria-label={`Trust ${percent} percent`}>
        <div className="meter-fill" style={{ width: `${percent}%` }} />
      </div>
      <span className="meter-label">{percent}% confidence</span>
    </div>
  )
}
