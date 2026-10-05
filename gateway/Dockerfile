FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home gateway

USER gateway
EXPOSE 8080
CMD ["python", "-c", "from gateway.main import run; run()"]
