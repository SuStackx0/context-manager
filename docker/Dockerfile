# Context Management Service — runtime image.
# Model weights are baked at BUILD time so the container runs fully offline.
# NOTE: this produces a multi-GB image (torch + transformers + model weights)
# and the running container needs ~2-4 GB RAM to load the model.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/models_cache \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for faiss / sentence-transformers builds.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Pre-download model weights into the image (build needs network; runtime does not).
ARG LLM_MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct
ARG EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RUN python - <<'PY'
import os
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer
llm = os.environ.get("LLM_MODEL_NAME", "Qwen/Qwen2.5-0.5B-Instruct")
emb = os.environ.get("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
snapshot_download(llm)
SentenceTransformer(emb)
print("Models cached.")
PY

COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
