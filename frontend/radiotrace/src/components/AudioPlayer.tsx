import { audioUrl } from '../api/client'
import type { Recording } from '../types/incident'

interface Props {
  recordings: Recording[]
}

export default function AudioPlayer({ recordings }: Props) {
  const playable = recordings.filter((item) => item.audio)
  if (playable.length === 0) {
    return <p className="muted">No replay audio stored for this incident.</p>
  }

  return (
    <div className="replay">
      {playable.map((item) => (
        <figure key={item.audio}>
          <figcaption>
            Replay {item.start_time}–{item.end_time}
          </figcaption>
          <audio controls preload="none" src={audioUrl(item.audio)}>
            Your browser does not support audio playback.
          </audio>
        </figure>
      ))}
    </div>
  )
}
