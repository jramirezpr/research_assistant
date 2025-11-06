# syntax=docker/dockerfile:1

FROM python:3.11-slim-trixie

WORKDIR /python-docker

# Install ffmpeg + clean up apt cache to keep image small
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "-w", "2", "-k", "gthread", "--threads", "4", "--timeout", "300", "--log-level", "debug", "--error-logfile", "-"]
