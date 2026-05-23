ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.19
FROM ${BUILD_FROM}

ENV LANG=C.UTF-8

RUN apk add --no-cache python3 py3-pip ca-certificates curl jq && \
    pip install --no-cache-dir --break-system-packages \
      paho-mqtt>=2.0 \
      httpx>=0.27 \
      aiohttp>=3.9 \
      pyyaml>=6.0

WORKDIR /app
COPY rootfs/ /
COPY app/ /app/

RUN chmod +x /etc/services.d/vp-edge/run /etc/services.d/vp-edge/finish

HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
  CMD curl -fs http://localhost:8080/health | grep -qE '"status":"(ok|degraded)"' || exit 1

LABEL \
  io.hass.name="VoltPure Edge" \
  io.hass.description="VoltPure Energy Management edge publisher" \
  io.hass.arch="aarch64|amd64|armv7|armhf" \
  io.hass.type="addon" \
  io.hass.version="1.0.0" \
  maintainer="VoltPure <info@voltpure.be>"
