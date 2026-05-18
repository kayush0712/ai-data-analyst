FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads generated_charts generated_csv /tmp/matplotlib

ENV MPLCONFIGDIR=/tmp/matplotlib
ENV PYTHONUNBUFFERED=1

EXPOSE 10000

CMD gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --workers 1 --timeout 120
