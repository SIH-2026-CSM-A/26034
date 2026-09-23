# Cloud Run deployment

The demo runs on Google Cloud Run in `asia-south1`, project `pccs-26034`, set up 2026-09-23.
The app is at **https://pccs-361618691569.asia-south1.run.app**: a permanent HTTPS URL, and a
secure context for the camera surfaces. The VM (`pccs-vm`) and its quick tunnel still run
alongside it. Nothing here changes `docker-compose.prod.yml`.

## Shape

| Piece | What | Why this way |
|---|---|---|
| `pccs` (Cloud Run) | `fnt` image: nginx serving the bundle and proxying `/api/` | The same image as compose. `BACKEND_ORIGIN` points nginx at the backend service (#207) |
| `pccs-backend` (Cloud Run) | `bck` image, unchanged from the VM's | The build we test is the build we demo |
| `pccs-db` (Cloud SQL) | PostgreSQL 16, Enterprise, `db-f1-micro`, zonal, 10 GB SSD, private IP only, daily backups kept 7 days | Smallest instance. Reached over Direct VPC egress |
| `gs://pccs-26034-evidence` | Versioning on, 365-day retention (not locked), public access prevention | Evidence objects through the S3-compatible API, held captures, and the rules corpus |
| Secret Manager | `pccs-database-url`, `pccs-jwt-secret`, `pccs-officers`, `pccs-evidence-s3-access-key`, `pccs-evidence-s3-secret-key` | No `.env` on a machine |
| Artifact Registry `pccs` | `backend:53f30e0`, `frontend:7b27e02` | Tags are the commits the images were built from |

Redis is not deployed: nothing in `bck/` uses it. MinIO is not deployed: GCS replaces it.

## Settings that must not be dropped

- **Backend: `--no-cpu-throttling`.** Image scans are processed in FastAPI `BackgroundTasks`
  after the 201 is returned. With request-based billing, Cloud Run throttles CPU once the
  response is sent, and the OCR stalls. With `--min-instances 0` idle still costs nothing.
- **Backend: `--max-instances 1`.** The start command runs `alembic upgrade head`. One
  instance means no migration race, the same as one VM.
- **Both services: `--no-invoker-iam-check`.** The app's own login token travels as
  `Authorization: Bearer <JWT>`. On a public service, Cloud Run can still try to verify a
  JWT-shaped bearer as a Google identity token and answer 401 before the request reaches
  the container ("The access token could not be verified"). It did so intermittently,
  mid-scan, before this was set.
- **Backend: `AWS_REQUEST_CHECKSUM_CALCULATION=when_required` and
  `AWS_RESPONSE_CHECKSUM_VALIDATION=when_required`.** boto3 1.43 adds default checksum
  headers that the GCS S3-compatible endpoint rejects as `SignatureDoesNotMatch` on
  `PutObject`.
- **Backend volumes:** the bucket is mounted with `only-dir=rules-corpus`, read-only, at
  `/rules-corpus`, and with `only-dir=captures;implicit-dirs` at `/app/storage/captures`.
  The capture store writes only when a file doesn't exist, so the retention policy never
  blocks it.
- **Frontend: nginx sends `Host: $proxy_host` with SNI** (#207). Cloud Run routes on both,
  and the visitor's host would be a 404.

## Commands

```sh
P=pccs-26034; R=asia-south1-docker.pkg.dev/$P/pccs
BACKEND=https://pccs-backend-361618691569.asia-south1.run.app

gcloud run deploy pccs-backend --project $P --region asia-south1 --image $R/backend:<sha> \
  --service-account pccs-backend@$P.iam.gserviceaccount.com --execution-environment gen2 \
  --no-cpu-throttling --cpu 2 --memory 4Gi --min-instances 0 --max-instances 1 \
  --concurrency 20 --timeout 900 --port 8000 \
  --network default --subnet default --vpc-egress private-ranges-only \
  --allow-unauthenticated --no-invoker-iam-check \
  --command sh --args="-c,alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000" \
  --set-env-vars "RULES_CORPUS_DIR=/rules-corpus,LOG_LEVEL=INFO,EVIDENCE_S3_ENDPOINT_URL=https://storage.googleapis.com,EVIDENCE_S3_BUCKET=pccs-26034-evidence,AWS_REQUEST_CHECKSUM_CALCULATION=when_required,AWS_RESPONSE_CHECKSUM_VALIDATION=when_required" \
  --set-secrets "DATABASE_URL=pccs-database-url:latest,JWT_SECRET=pccs-jwt-secret:latest,OFFICERS=pccs-officers:latest,EVIDENCE_S3_ACCESS_KEY=pccs-evidence-s3-access-key:latest,EVIDENCE_S3_SECRET_KEY=pccs-evidence-s3-secret-key:latest" \
  --add-volume "name=rules,type=cloud-storage,bucket=pccs-26034-evidence,readonly=true,mount-options=only-dir=rules-corpus" \
  --add-volume-mount "volume=rules,mount-path=/rules-corpus" \
  --add-volume "name=captures,type=cloud-storage,bucket=pccs-26034-evidence,mount-options=only-dir=captures;implicit-dirs" \
  --add-volume-mount "volume=captures,mount-path=/app/storage/captures"

gcloud run deploy pccs --project $P --region asia-south1 --image $R/frontend:<sha> \
  --service-account pccs-frontend@$P.iam.gserviceaccount.com --port 80 --cpu 1 --memory 256Mi \
  --min-instances 0 --max-instances 2 --timeout 900 \
  --allow-unauthenticated --no-invoker-iam-check --set-env-vars BACKEND_ORIGIN=$BACKEND
```

**Building images.** The backend image is 7.5 GB, so it's built and pushed from the VM, in
the same region. The VM's own service account has read-only storage scope and can't push.
Instead, give it a one-hour token from an owner's `gcloud auth print-access-token` for
`docker login -u oauth2accesstoken`. Capture the token in a shell variable before writing it
to a file: redirecting the command's output straight to a file gave a token Docker rejected.

**Changing `OFFICERS`.** Add a new secret version (`gcloud secrets versions add
pccs-officers --data-file=…`) and redeploy the backend. `demo-officer` is read-only in code
(`PUBLISHED_OFFICERS`, #203) whatever the secret says.

## Idle cost

Prices are from the Cloud Billing Catalog API for asia-south1 on 2026-09-23, 730 hours a
month, in USD.

| Item | Basis | Per month |
|---|---|---|
| Cloud SQL `db-f1-micro`, zonal | $0.0126 / hour | $9.20 |
| Cloud SQL SSD storage, 10 GB | $0.204 / GB-month | $2.04 |
| Cloud SQL backups, 7 × a 36 MB database | $0.096 / GB-month | < $0.10 |
| Artifact Registry, 1.69 GiB | $0.10 / GiB-month after 0.5 free | $0.12 |
| Cloud Storage, 8.8 MiB | $0.023 / GiB-month | < $0.01 |
| Secret Manager, 5 active versions | first 6 free | $0.00 |
| Cloud Run, both services | scale to zero | $0.00 |
| **Total at idle** | | **≈ $11.50** |

Use is extra. The backend bills 2 vCPU and 4 GiB for as long as an instance is up, which is
while it serves plus up to about 15 minutes idle before scaling to zero.

The VM (e2-standard-4 with an 80 GB balanced disk) is about $127 a month at the same rates:
4 × $0.026199 + 16 × $0.003511 per hour, plus $0.12 per GB-month. That saving arrives only
when the VM is stopped.
