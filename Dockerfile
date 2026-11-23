FROM python:3.12-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt .
ENV CMAKE_BUILD_PARALLEL_LEVEL=2
RUN pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
RUN mkdir -p /models /data && curl -fsSL --retry 3 \
    https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/23749fefcc72300e3a2ad315e1317431b06b590a/Qwen3-0.6B-Q8_0.gguf \
    -o /models/qwen.gguf && chown 1000:1000 /data
ENV AZPU_MODEL_PATH=/models/qwen.gguf AZPU_DATABASE_PATH=/data/assessments.sqlite3
COPY backend backend
COPY ml ml
USER 1000:1000
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
