# PCCS backend. Paddle model weights are downloaded during the build and baked into the
# image — nothing fetches a model at runtime, because the demo has to survive the venue
# network failing.
FROM python:3.11-slim

# libgomp1: paddlepaddle. libgl1 + libglib2.0-0: cv2 — pyproject asks for
# opencv-python-headless, but paddlex pulls opencv-contrib-python and ultralytics pulls
# opencv-python, and those two are the non-headless builds that need libGL.so.1.
# tesseract-ocr(-eng): the constrained MRP/net-quantity re-read; the app refuses to boot
# without its tessdata.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libgl1 \
        libglib2.0-0 \
        tesseract-ocr \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.10 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    TMPDIR=/var/tmp

# Dependencies before source, so a code change does not re-resolve paddle and torch.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# Debian ships tessdata under a major-version directory. Resolve it rather than guessing,
# and fail the build if the language data is not there.
RUN eng="$(find /usr/share/tesseract-ocr -name eng.traineddata -print -quit)" \
    && test -n "$eng" \
    && ln -s "$(dirname "$eng")" /opt/tessdata \
    && ls /opt/tessdata

# Downloads the PaddleOCR default models and copies det/rec into ~/.cache/pccs/models.
# The script exits non-zero if it finds nothing, so an image can never ship empty weights.
RUN python scripts/bootstrap_weights.py \
    && test -s /root/.cache/pccs/models/ocr_det/inference.yml \
    && test -s /root/.cache/pccs/models/ocr_rec/inference.yml

ENV OCR_DET_MODEL_DIR=/root/.cache/pccs/models/ocr_det \
    OCR_REC_MODEL_DIR=/root/.cache/pccs/models/ocr_rec \
    TESSERACT_TESSDATA_DIR=/opt/tessdata

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
