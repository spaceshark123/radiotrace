import { useEffect, useRef, useState } from 'react'
import { fetchIncomingClip, fetchIncomingClipNames, type IncomingClip } from '../api/client'

export default function LiveRadio() {
  const [clips, setClips] = useState<IncomingClip[]>([])
  const [error, setError] = useState<string | null>(null)
  const objectUrls = useRef<string[]>([])

  useEffect(() => {
    let cancelled = false
    const knownFiles = new Set<string>()

    async function poll() {
      try {
        // get the current calls
        const filenames = await fetchIncomingClipNames()
        const newClips = filenames.filter((clip) => !knownFiles.has(clip.filename))
        newClips.forEach((clip) => knownFiles.add(clip.filename))

        const discovered = newClips.map((clip) => ({
          ...clip,
          status: 'discovered' as const,
        }))
        if (!cancelled && discovered.length > 0) {
          setClips((current) => [...discovered, ...current])
        }

        // fetch the audio files for each call
        const fetched = await Promise.all(
          newClips.map(async (clip): Promise<IncomingClip> => {
            try {
              const response = await fetchIncomingClip(clip)
              const blob = await response.blob()
              const objectUrl = URL.createObjectURL(blob)
              objectUrls.current.push(objectUrl)
              return {
                ...clip,
                status: 'fetched',
                size: blob.size,
                contentType: response.headers.get('content-type') ?? blob.type,
                objectUrl,
              }
            } catch (err) {
              return {
                ...clip,
                status: 'error',
                error: err instanceof Error ? err.message : 'Clip fetch failed',
              }
            }
          }),
        )
        if (!cancelled) { // only update state if not cancelled
          setClips((current) =>
            current.map((clip) => fetched.find((item) => item.filename === clip.filename) ?? clip),
          )
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Clip list unavailable')
        }
      }
    }

    // start polling for new clips immediately and then every 10 seconds
    void poll()
    const timer = window.setInterval(() => void poll(), 10000)
    return () => { // cleanup on unmount
      cancelled = true
      window.clearInterval(timer)
      objectUrls.current.forEach((objectUrl) => URL.revokeObjectURL(objectUrl))
    }
  }, [])

  return (
    <section className="panel live-radio">
      <header>
        <h2>Incoming clips</h2>
        <p className="muted">Polling for new MP3 and M4A files every 10 seconds.</p>
      </header>
      {error ? <p className="error">{error}</p> : null}
      {clips.length === 0 ? <p className="muted small">No clips discovered yet.</p> : null}
      <ul className="incoming-clips">
        {clips.map((clip) => (
          <li key={clip.filename}>
            <div className="clip-debug">
              <strong>{clip.filename}</strong>
              <span className="muted small">
                {clip.status}
                {clip.size !== undefined ? ` · ${clip.size.toLocaleString()} bytes` : ''}
                {clip.contentType ? ` · ${clip.contentType}` : ''}
              </span>
            </div>
            {clip.error ? <p className="error small">{clip.error}</p> : null}
            {clip.objectUrl ? <audio controls preload="none" src={clip.objectUrl} /> : null}
          </li>
        ))}
      </ul>
      <p className="muted small">Debug only. Discovered clips are not processed automatically.</p>
    </section>
  )
}
