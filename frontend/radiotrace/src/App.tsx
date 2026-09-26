import { useCallback, useEffect, useState } from 'react'
import ClipUploader from './components/ClipUploader'
import IncidentList from './components/IncidentList'
import IncidentMap from './components/IncidentMap'
import {
  fetchCityConfig,
  fetchHealth,
  fetchIncidents,
  seedDemoIncidents,
} from './api/client'
import type { CityConfig, Incident } from './types/incident'
import './App.css'

const DEFAULT_CENTER = { lat: 33.749, lng: -84.388 }

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [config, setConfig] = useState<CityConfig | null>(null)
  const [status, setStatus] = useState('Connecting…')
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [health, city, items] = await Promise.all([
        fetchHealth(),
        fetchCityConfig(),
        fetchIncidents(),
      ])
      setStatus(`${health.status} · ${health.city ?? city.city}`)
      setConfig(city)
      setIncidents(items)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reach the API')
      setStatus('backend offline')
    }
  }, [])

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => {
      void refresh()
    }, 15000)
    return () => window.clearInterval(timer)
  }, [refresh])

  async function loadDemo() {
    try {
      const items = await seedDemoIncidents()
      setIncidents(items)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Seed failed')
    }
  }

  function onSelect(incident: Incident) {
    setSelectedId(incident.id)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Public safety · {config?.city ?? 'Atlanta'}</p>
          <h1>RadioTrace</h1>
        </div>
        <div className="status">
          <span className={error ? 'dot down' : 'dot up'} />
          {status}
        </div>
      </header>

      <main className="layout">
        <section className="map-pane">
          <IncidentMap
            incidents={incidents}
            selectedId={selectedId}
            onSelect={onSelect}
            center={config?.center ?? DEFAULT_CENTER}
          />
        </section>
        <aside className="sidebar">
          <section className="panel alerts">
            <header className="alerts-header">
              <div>
                <h2>Crime notices</h2>
                <p className="muted">Severity and trust scores from Grok analysis.</p>
              </div>
              <button type="button" onClick={() => void loadDemo()}>
                Seed Atlanta demo
              </button>
            </header>
            {error ? <p className="error">{error}</p> : null}
            <IncidentList incidents={incidents} selectedId={selectedId} onSelect={onSelect} />
          </section>
          <ClipUploader onComplete={() => void refresh()} />
        </aside>
      </main>
    </div>
  )
}
