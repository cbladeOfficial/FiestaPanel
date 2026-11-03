# syntax=docker/dockerfile:1
FROM eclipse-temurin:21-jre-noble

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER=1 \
    FIESTA_HOST=0.0.0.0 \
    FIESTA_PORT=8080 \
    FIESTA_SERVER_DIR=/server \
    FIESTA_DATA_DIR=/app/data

# Install Python 3, pip, venv, screen, curl, procps, and required tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    screen \
    curl \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies in dedicated venv
COPY requirements.txt /app/requirements.txt
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

ENV PATH="/opt/venv/bin:$PATH"

# Copy panel application files
COPY . /app

# Ensure entrypoint and panelctl are executable
RUN chmod +x /app/entrypoint.sh /app/panelctl && \
    ln -sf /app/panelctl /usr/local/bin/panelctl

# Create persistent storage directories
RUN mkdir -p /server /app/data /app/static/uploads

# Expose ports:
# 8080: Web UI
# 25565: Minecraft Java Server
# 19132/udp: Geyser Bedrock Edition
EXPOSE 8080 25565 19132/udp

VOLUME ["/server", "/app/data"]

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "app.py"]
