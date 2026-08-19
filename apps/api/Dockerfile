FROM python:3.12-slim

ARG SCIDOC_EXTRAS=ocr,voice

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SCIDOC_STORAGE_ROOT=/app/data \
    SCIDOC_NARRATION_LOCAL_MODEL=/opt/scidoc/models/narration/kokoro-v1.0.onnx \
    SCIDOC_NARRATION_LOCAL_VOICES=/opt/scidoc/models/narration/voices-v1.0.bin

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        espeak-ng \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        libsndfile1 \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md alembic.ini ./
COPY apps ./apps
COPY cli ./cli
COPY config ./config
COPY migrations ./migrations
COPY packages ./packages
COPY scripts/setup_local_voice.sh ./scripts/setup_local_voice.sh

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e ".[${SCIDOC_EXTRAS}]" \
    && SCIDOC_NARRATION_MODEL_DIR=/opt/scidoc/models/narration ./scripts/setup_local_voice.sh \
    && groupadd --system --gid 10001 scidoc \
    && useradd --system --uid 10001 --gid scidoc --home-dir /app --shell /usr/sbin/nologin scidoc \
    && mkdir -p /app/data \
    && chown -R scidoc:scidoc /app/data

USER scidoc

EXPOSE 8000

CMD ["uvicorn", "scidoc_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
