# syntax=docker/dockerfile:1

FROM python:3.11-slim-trixie

WORKDIR /python-docker

# Install ffmpeg + clean up apt cache to keep image small
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["flask", "--app", "app", "run", "--host=0.0.0.0"]
