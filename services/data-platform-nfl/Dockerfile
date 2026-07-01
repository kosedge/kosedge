FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app/src

ENTRYPOINT ["python3", "-m", "data_platform_nfl.cli"]
