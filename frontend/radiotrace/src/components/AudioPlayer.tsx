import { useEffect, useState } from 'react'
import { audioUrl, fetchClip, type RadioClip } from '../api/client'

interface Props {
  recordings: string[]
}

export default function AudioPlayer({ recordings }: Props) {
  const [clips, setClips] = useState<RadioClip[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const clipIds = recordings.filter(Boolean)

    if (clipIds.length === 0) {
      setClips([])
      return () => {
        cancelled = true
      }
    }

    Promise.all(clipIds.map((clipId) => fetchClip(clipId)))
      .then((loadedClips) => {
        if (!cancelled) {
          setClips(loadedClips)
          setError(null)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load incident clips')
        }
      })

    return () => {
      cancelled = true
    }
  }, [recordings])

  if (recordings.length === 0) {
    return <p className="muted">No replay audio stored for this incident.</p>
  }

  if (error) {
    return <p className="error">{error}</p>
  }

  return (
    <div className="replay">
      {clips.length === 0 ? <p className="muted">Loading incident clips…</p> : null}
      {clips.map((clip) => (
        <figure key={clip.id}>
          <figcaption>{clip.filename}</figcaption>
          <p className="muted small">
            {clip.metadata.transcript || 'No transcript available.'}
          </p>
          <audio controls preload="none" src={audioUrl(clip.id)}>
            Your browser does not support audio playback.
          </audio>
        </figure>
      ))}
    </div>
  )
}
