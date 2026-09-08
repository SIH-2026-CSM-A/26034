import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../services/apiClient'
import type { components } from '../services/generated/schema'
import { ConsumerHeader } from './ConsumerHeader'

type Body = components['schemas']['Body_submit_consumer_image_scan_consumer_scans_image_post']

/**
 * Photograph or choose a label. The file input with capture="environment" opens the
 * phone's own camera app, which is the most reliable camera on a mobile browser and
 * needs no permission prompt of ours; on a laptop it is a file picker.
 */
export function ConsumerCapture() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const choose = useCallback(
    (chosen: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
      setFile(chosen)
      setPreviewUrl(chosen ? URL.createObjectURL(chosen) : null)
      setError(null)
    },
    [previewUrl],
  )

  const submit = useCallback(async () => {
    if (!file) return
    setSubmitting(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('image', file)
      const { data, error: apiError } = await apiClient.POST('/consumer/scans/image', {
        body: formData as unknown as Body,
      })
      if (apiError || !data) {
        setError('The photograph could not be submitted. Check the connection and try again.')
        return
      }
      navigate(`/consumer/scans/${data.id}`)
    } catch {
      setError('The photograph could not be submitted. Check the connection and try again.')
    } finally {
      setSubmitting(false)
    }
  }, [file, navigate])

  return (
    <div className="min-h-screen bg-paper text-ink">
      <ConsumerHeader />
      <main className="mx-auto max-w-[640px] px-4 py-6 sm:py-10">
        <h1 className="text-section font-semibold sm:text-title">Check a package label</h1>
        <p className="mt-2 text-body text-mute">
          Photograph the back or front panel of any packaged product — food or not. You get
          back what the Legal Metrology (Packaged Commodities) Rules, 2011 ask for on a label,
          and whether each item could be found on yours. No sign-in, and nothing about you is
          stored.
        </p>

        <div className="mt-6 border-2 border-ink bg-paper p-4">
          <label htmlFor="consumer-photo" className="block text-body font-medium">
            Label photograph
          </label>
          <p className="mt-0.5 text-secondary text-mute">
            Fill the frame with the printed panel, in good light, without glare.
          </p>
          <input
            id="consumer-photo"
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => choose(e.target.files?.[0] ?? null)}
            className="mt-3 block w-full text-body file:mr-3 file:min-h-target file:border file:border-ink file:bg-paper file:px-4 file:py-2 file:font-mono file:text-label file:text-ink"
          />
          {previewUrl && (
            <img
              src={previewUrl}
              alt="The label you chose"
              className="mt-4 max-h-[420px] w-full border border-hairline object-contain"
            />
          )}
        </div>

        {error && (
          <div className="mt-4 border border-seal bg-paper p-4">
            <p className="text-body font-semibold text-seal">Not submitted</p>
            <p className="mt-1 text-secondary text-mute">{error}</p>
          </div>
        )}

        <button
          type="button"
          onClick={submit}
          disabled={!file || submitting}
          className="mt-4 flex min-h-target w-full items-center justify-center border-2 border-ink bg-ink px-6 py-4 font-mono text-body font-semibold text-paper hover:bg-ink/90 disabled:cursor-not-allowed disabled:border-mute disabled:bg-mute/20 disabled:text-mute"
        >
          {submitting ? 'Sending…' : 'Check this label'}
        </button>

        <p className="mt-6 text-label text-mute">
          Reading a label takes the server up to a minute. The result page keeps checking
          for you; you can leave it open.
        </p>
      </main>
    </div>
  )
}
