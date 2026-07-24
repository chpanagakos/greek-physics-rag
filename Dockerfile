# Container image for greek-physics-rag.
#
# Build:  docker build -t greek-physics-rag .
# Run:    docker run --rm -p 7860:7860 -e GEMINI_API_KEY=... greek-physics-rag
#         then open http://localhost:7860
#
# Note on first run: FlagEmbedding downloads the full BAAI/bge-m3 repo
# (~4.5 GB) into the container at startup. The volume mount below caches it
# on the host so subsequent runs skip the download:
#   docker run --rm -p 7860:7860 -e GEMINI_API_KEY=... \
#     -v hf-cache:/home/app/.cache/huggingface greek-physics-rag
# Pre-baking the weights into the image was considered and declined: it would
# add ~4.5 GB to a demonstrator image for a one-off cost.

FROM python:3.12-slim

# Gradio's default port.
ENV PORT=7860 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

# Dependencies are installed BEFORE the source is copied, so editing code
# does not invalidate the pip layer — rebuilds after a code change are
# near-instant instead of re-downloading the CPU torch wheel.
COPY requirements.txt .

# gradio is not in requirements.txt: Hugging Face Spaces pre-installs it and
# takes the version from sdk_version in the README front matter. In a
# container there is no such provision, so it is pinned here to the same
# version the Space runs.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gradio==6.20.0

# Application code and the shipped Qdrant collection.
COPY . .

# Run as a non-root user; the model cache lives in this user's home.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R app:app /app /home/app
USER app

EXPOSE 7860

# server_name is set here rather than in app.py so the application code is
# identical on the Space and in the container.
ENV GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

CMD ["python", "app.py"]
