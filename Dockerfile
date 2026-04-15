# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_DISABLE_PIP_VERSION_CHECK=1     PIP_NO_CACHE_DIR=1     POSTGRES_HOST=postgres     POSTGRES_PORT=5432     POSTGRES_DB=chatbot     POSTGRES_USER=postgres     POSTGRES_PASSWORD=P@ssw0rd

RUN apt-get update     && apt-get install -y --no-install-recommends         build-essential         git     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "chatbot.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
