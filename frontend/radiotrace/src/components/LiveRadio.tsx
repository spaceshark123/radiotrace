import { useEffect, useState } from 'react'
import { fetchRadioStatus, liveStreamUrl } from '../api/client'

export default function LiveRadio() {
  const [label, setLabel] = useState('Atlanta police radio')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchRadioStatus()
      .then((status) => {
        setLabel(`${status.city} Broadcastify feed ${status.feed_id}`)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Radio status unavailable')
      })
  }, [])

  return (
    <section className="panel live-radio">
      <header>
        <h2>Live listening</h2>
        <p className="muted">{label}</p>
      </header>
      {error ? <p className="error">{error}</p> : null}
      <audio controls preload="none" src={liveStreamUrl()}>
        Live stream is not supported in this browser.
      </audio>
      <p className="muted small">
        Stream is proxied from Broadcastify. If it fails, replay stored incident clips instead.
      </p>
    </section>
  )
}
