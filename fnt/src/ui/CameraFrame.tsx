import { useCallback, useEffect, useRef, useState } from 'react'
import { Notice } from './Notice'

/**
 * A live camera view and a shutter, and nothing else.
 *
 * There is no file input here on purpose. A vendor self-check is a statement about a
 * package on that vendor's own shelf at the moment they make it, and a file picker accepts
 * a photograph of anything, taken anywhere, at any time — including a manufacturer's
 * artwork rather than the printed pack. `capture="environment"` on a file input does not
 * close that: it is a hint a phone may honour and a desktop ignores entirely, and even on a
 * phone the gallery is one tap away. Reaching the camera directly is the only spelling that
 * means what the surface claims.
 *
 * The officer surface keeps its upload — the problem statement requires an officer to be
 * able to submit an existing photograph, and an officer's submission is one they attest to.
 *
 * Nothing here falls back to a file input when the camera cannot be opened. A fallback
 * would give back exactly what this exists to remove, silently and only on the devices
 * where it matters most.
 */
export function CameraFrame({
  onCapture,
  label = 'Photograph the package',
  hint = 'Fill the frame with the printed panel, in good light, without glare.',
}: {
  onCapture: (blob: Blob) => void
  label?: string
  hint?: string
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(false)

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setLive(false)
  }, [])

  const start = useCallback(async () => {
    setError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        window.isSecureContext === false
          ? 'The camera needs a secure (HTTPS) connection. Open this page over https and try again.'
          : 'This browser does not support in-app camera capture.',
      )
      return
    }
    try {
      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        })
      } catch {
        // A laptop has no rear camera; the constraint is a preference, not a requirement.
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      }
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play().catch(() => {
          // playsInline + muted cover autoplay; a rejection here is not fatal.
        })
      }
      setLive(true)
    } catch (err) {
      setLive(false)
      const name = err instanceof DOMException ? err.name : ''
      if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
        setError('Camera permission was refused. Allow camera access for this site, then try again.')
      } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
        setError('No camera was found on this device.')
      } else {
        setError('The camera could not be opened. Check that nothing else is using it, then try again.')
      }
    }
  }, [])

  useEffect(() => {
    void start()
    return stop
  }, [start, stop])

  const shutter = useCallback(() => {
    const video = videoRef.current
    if (!video || video.videoWidth === 0 || video.videoHeight === 0) {
      setError('The camera is still starting. Wait a moment and take the photograph again.')
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      setError('This browser could not read a frame from the camera.')
      return
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError('This browser could not turn the frame into an image.')
          return
        }
        stop()
        onCapture(blob)
      },
      'image/jpeg',
      0.92,
    )
  }, [onCapture, stop])

  return (
    <div>
      <div className="relative flex min-h-[260px] items-center justify-center overflow-hidden rounded-[14px] border-2 border-dashed border-hairline bg-sunken/60">
        <video
          ref={videoRef}
          playsInline
          muted
          aria-label="Live camera view"
          className={`max-h-[420px] w-full object-contain ${live ? '' : 'hidden'}`}
        />
        {!live && (
          <p className="px-6 py-10 text-center text-secondary text-mute">
            {error ? 'The camera is not available.' : 'Starting the camera…'}
          </p>
        )}
      </div>

      {error && (
        <div className="mt-3">
          <Notice title="Camera unavailable" role="alert">
            <span>{error}</span>
          </Notice>
          <button type="button" onClick={() => void start()} className="btn btn-quiet mt-2 w-full">
            Try the camera again
          </button>
        </div>
      )}

      <button
        type="button"
        id="vendor-shutter"
        onClick={shutter}
        disabled={!live}
        className="btn btn-primary mt-3 w-full py-4 text-body"
      >
        {label}
      </button>
      <p className="mt-3 px-1 text-label text-mute">{hint}</p>
    </div>
  )
}
