import { useRef, useState } from 'react'
import { audioUrl, fetchClip, type RadioClip } from '../api/client'

interface Props {
  recordings: string[]
}

export default function AudioPlayer({ recordings }: Props) {
  const [clips, setClips] = useState<Record<string, RadioClip>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const loadingIds = useRef(new Set<string>())

  if (recordings.length === 0) {
    return <p className="muted">No replay audio stored for this incident.</p>
  }

  async function loadClip(clipId: string) {
    if (clips[clipId] || loadingIds.current.has(clipId)) {
      return
    }
    loadingIds.current.add(clipId)
    try {
      const clip = await fetchClip(clipId)
      setClips((current) => ({ ...current, [clipId]: clip }))
    } catch (err) {
      setErrors((current) => ({
        ...current,
        [clipId]: err instanceof Error ? err.message : 'Unable to load clip details',
      }))
    } finally {
      loadingIds.current.delete(clipId)
    }
  }

  return (
    <div className="replay">
      {recordings.filter(Boolean).map((clipId) => {
        const clip = clips[clipId]
        return (
        <figure key={clipId}>
          <figcaption>{clip?.filename ?? `Clip ${clipId}`}</figcaption>
          <p className="muted small">
            {clip?.metadata.transcript ?? 'Transcript loads when played.'}
          </p>
          {errors[clipId] ? <p className="error small">{errors[clipId]}</p> : null}
          <audio controls preload="none" src={audioUrl(clipId)} onPlay={() => void loadClip(clipId)}>
            Your browser does not support audio playback.
          </audio>
        </figure>
        )
      })}
    </div>
  )
}
