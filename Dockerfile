FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HIVE_DATA_DIR=/data \
    HIVE_CONFIG_DIR=/app/config

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY config ./config
RUN pip install --no-cache-dir .

EXPOSE 8080 8000
CMD ["uvicorn", "hive_connectome.app:app", "--host", "0.0.0.0", "--port", "8080"]
