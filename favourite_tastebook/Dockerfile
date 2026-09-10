FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg2-binary ships wheels, so no compiler is needed at build time —
# this drops roughly 600 MB from the image.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .