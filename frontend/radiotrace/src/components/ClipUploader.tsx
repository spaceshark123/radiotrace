import { useState, type FormEvent } from 'react'
import { uploadClip } from '../api/client'

interface Props {
  onComplete: () => void
}

export default function ClipUploader({ onComplete }: Props) {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const fileInput = form.elements.namedItem('clip') as HTMLInputElement
    const file = fileInput.files?.[0]
    if (!file) {
      setMessage('Choose an MP3 or M4A clip first.')
      return
    }
    const start = Number((form.elements.namedItem('start_time') as HTMLInputElement).value)
    const end = Number((form.elements.namedItem('end_time') as HTMLInputElement).value)
    setBusy(true)
    setMessage(null)
    try {
      await uploadClip(file, start, end)
      setMessage('Clip processed. Refreshing incidents.')
      form.reset()
      onComplete()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="panel uploader" onSubmit={onSubmit}>
      <h2>Analyze a recorded clip</h2>
      <p className="muted">
        Offline pipeline: ElevenLabs transcript, Grok incident parse, Google geocode. Blank audio
        is stored but does not call the LLM.
      </p>
      <label>
        MP3 or M4A file
        <input name="clip" type="file" accept="audio/mpeg,.mp3,audio/mp4,.m4a" />
      </label>
      <div className="row">
        <label>
          Start
          <input name="start_time" type="number" defaultValue={0} />
        </label>
        <label>
          End
          <input name="end_time" type="number" defaultValue={30} />
        </label>
      </div>
      <button type="submit" disabled={busy}>
        {busy ? 'Processing…' : 'Process clip'}
      </button>
      {message ? <p className="muted">{message}</p> : null}
    </form>
  )
}
